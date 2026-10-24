#!/usr/bin/env python3
"""Controlled RenPy engine test: copy installation, switches and NEW processes.
Not evidence about a commercial game or a live translation service.
"""
from pathlib import Path
import argparse,json,os,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from linguanova_next.packaging.share_package_installation import install_copy
from linguanova_next.util import atomic_json,file_hash

HARNESS='''# TEST HARNESS ONLY. This file is not included in the player package.
init 1000 python:
    import os as _f_os
    import json as _f_json
    import hashlib as _f_hash
    if _f_os.environ.get("LN_FORCE_START_LANGUAGE"):
        config.language = _f_os.environ["LN_FORCE_START_LANGUAGE"]
    def _f_snapshot():
        values = {}
        for path in ("images/buttons/continue_normal.png", "images/buttons/continue_hover.png", "images/buttons/continue_selected.png", "images/capitulo_01/telefono/mensaje.png"):
            with renpy.file(path) as stream:
                values[path] = _f_hash.sha256(stream.read()).hexdigest()
        return {"language": _preferences.language, "choice": persistent.linguanova_language_choice,
                "known": sorted(renpy.known_languages()), "text": renpy.translate_string("Welcome to our quiet village."),
                "images": values}

screen fixture_asset_preview():
    vbox:
        xalign 0.95
        yalign 0.5
        spacing 8
        text "CONTROLLED IMAGE STATES" size 16 color "#b8f36b"
        add "images/buttons/continue_normal.png" zoom 0.5
        add "images/buttons/continue_hover.png" zoom 0.5
        add "images/buttons/continue_selected.png" zoom 0.5
        add "images/capitulo_01/telefono/mensaje.png" zoom 0.375

label before_main_menu:
    python:
        mode = _f_os.environ.get("LN_FIXTURE_MODE", "")
        code = _f_os.environ.get("LN_FIXTURE_LANGUAGE", "Original")
        code = None if code == "Original" else code
        details = _f_json.loads(_f_os.environ.get("LN_FIXTURE_DETAILS", "{}"))
        if mode == "select":
            _ln_next_choose_language(code, details.get("profile_id", ""), details.get("locale", ""))
        elif mode == "check":
            assert _preferences.language == code, repr((_preferences.language, code))
        records = []
        if mode == "sequence":
            for item in _f_json.loads(_f_os.environ["LN_FIXTURE_SEQUENCE"]):
                _ln_next_choose_language(item.get("renpy_id"), item.get("profile_id", ""), item.get("locale", ""))
                records.append(_f_snapshot())
        else:
            records.append(_f_snapshot())
        renpy.show_screen("preferences")
        renpy.show_screen("fixture_asset_preview")
        renpy.pause(0.1, hard=True)
        if _f_os.environ.get("LN_FIXTURE_SCREENSHOT"):
            renpy.screenshot(_f_os.environ["LN_FIXTURE_SCREENSHOT"])
        with open(_f_os.environ["LN_FIXTURE_REPORT"], "w") as stream:
            _f_json.dump(records, stream, ensure_ascii=False)
        if mode:
            renpy.quit()
    return
'''


def acceptance(renpy,demo_path,workspace,display=None):
    workspace=Path(workspace).resolve();workspace.mkdir(parents=True,exist_ok=True)
    summary=json.loads(Path(demo_path).read_text())
    target=workspace/'Segunda copia con espacios y acentos áñ'
    if target.exists():raise ValueError('Acceptance target already exists; choose a new workspace')
    shutil.copytree(summary['source'],target)
    manifest=install_copy(summary['package']['path'],target,workspace/'private_backup')
    # Explicitly added test script, separate from everything shipped to players.
    (target/'game/zz_fixture_acceptance.rpy').write_text(HARNESS,encoding='utf-8')
    destinations=manifest['destinations']
    by_id={d['renpy_id']:d for d in destinations}
    image_paths=['images/buttons/continue_normal.png','images/buttons/continue_hover.png','images/buttons/continue_selected.png','images/capitulo_01/telefono/mensaje.png']
    expected={None:{p:file_hash(target/'game'/p) for p in image_paths}}
    for code in by_id:
        expected[code]={p:file_hash(target/'game/tl'/code/p) for p in image_paths}
    savedir=workspace/'player_data_separate'
    runs=[]
    environment=os.environ.copy();environment.update(SDL_AUDIODRIVER='dummy',RENPY_RENDERER='sw')
    if display:environment.update(DISPLAY=display,SDL_VIDEODRIVER='x11')
    environment.pop('SDL_VIDEODRIVER',None) if not display else None
    def run(mode,code,details=None,sequence=None,screenshot=False):
        index=len(runs);report=workspace/f'run_{index:02d}.json';log=workspace/f'run_{index:02d}.log'
        env=environment|{'LN_FIXTURE_MODE':mode,'LN_FIXTURE_LANGUAGE':code or 'Original',
                         'LN_FIXTURE_DETAILS':json.dumps(details or {}),'LN_FIXTURE_REPORT':str(report),
                         'LN_FORCE_START_LANGUAGE':'english'}
        if sequence is not None:env['LN_FIXTURE_SEQUENCE']=json.dumps(sequence)
        if screenshot:env['LN_FIXTURE_SCREENSHOT']=str(workspace/f'preferences_{code or "Original"}.png')
        result=subprocess.run([str(renpy),str(target),'--savedir',str(savedir)],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
        log.write_bytes(result.stdout)
        if result.returncode or not report.is_file():raise RuntimeError('RenPy engine acceptance failed: '+str(log))
        records=json.loads(report.read_text())
        for record in records:
            actual=record['language']
            assert record['images']==expected[actual],('Localized assets mismatch',actual)
            assert not any(x.startswith('linguanova_font') or x=='linguanova_mod_fonts' for x in record['known'])
        runs.append({'mode':mode,'requested':code,'records':records,'returncode':result.returncode,'log':log.name})
        return records
    for destination in destinations+[{'renpy_id':None,'profile_id':'','locale':''}]:
        code=destination['renpy_id']
        selected=run('select',code,destination,screenshot=True)[0]
        reopened=run('check',code)[0]
        assert reopened['language']==code and reopened['choice']['selected']
        assert reopened['choice']['profile_id']==destination.get('profile_id','')
        assert selected['text']==reopened['text']
    # 20 base-language directions, plus the extra Spanish-profile directions.
    sequence=[]
    for first in destinations:
        for second in destinations:
            if first['renpy_id']!=second['renpy_id']:sequence.extend([first,second])
        sequence.extend([first,{'renpy_id':None,'profile_id':'','locale':''}])
    switches=run('sequence',None,sequence=sequence)
    for desired,observed in zip(sequence,switches):assert desired['renpy_id']==observed['language']
    # Same bytes can update a compatible copy while preserving player data.
    persistent=savedir/'persistent';before=file_hash(persistent)
    install_copy(summary['package']['path'],target,workspace/'update_backup',previous_manifest=manifest)
    assert file_hash(persistent)==before
    result={'schema_version':1,'scope':'Controlled fixture, real RenPy processes; not a commercial game',
            'provider':'Controlled dictionary; no live-provider evidence',
            'engine':'RenPy 8.3.7.25031702 (SDK version used by caller must match)',
            'archive_format':Path(summary['package']['path']).suffix.lower().lstrip('.'),
            'archive_sha256':file_hash(summary['package']['path']),
            'destinations':destinations,'fresh_processes':len(runs),'base_directions':20,
            'profile_additional_directions':len(destinations)*(len(destinations)-1)-20,'original_returns':len(destinations),'switch_steps':len(switches),
            'installation':'Distributed game/ copied to a second compatible root with spaces/accents',
            'creator_dependency_in_game':False,'player_persistent_retained_on_update':True,
            'runs':runs,'screenshots':sorted(p.name for p in workspace.glob('preferences_*.png'))}
    atomic_json(workspace/'acceptance.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--renpy',required=True);parser.add_argument('--demo',required=True)
    parser.add_argument('--workspace',required=True);parser.add_argument('--display')
    args=parser.parse_args()
    result=acceptance(args.renpy,args.demo,args.workspace,args.display)
    print(json.dumps({k:v for k,v in result.items() if k!='runs'},ensure_ascii=False,indent=2))
