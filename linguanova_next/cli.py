import argparse
import asyncio
import json
from pathlib import Path
from .util import load_json, jsonable
from .packaging.frozen_resources import resource_root


def main(argv=None):
    parser=argparse.ArgumentParser(description='LinguaNova Next experimental creator')
    sub=parser.add_subparsers(dest='command')
    sub.add_parser('verify',help='Verify all 283 protected original files without GUI imports')
    gui=sub.add_parser('gui')
    gui.add_argument('--smoke-output',help='Load bundled QML, capture it and exit; useful for frozen distribution checks')
    sub.add_parser('classic',help='Original QML with an added utilities card')
    sub.add_parser('list')
    translate=sub.add_parser('translate')
    translate.add_argument('project');translate.add_argument('--target',default='es',choices=['es','fr','pt','ru','en'])
    translate.add_argument('--profile');translate.add_argument('--provider',default='google')
    translate.add_argument('--source',default='auto');translate.add_argument('--model',default='')
    translate.add_argument('--mode',default='native',choices=['native','mod'])
    translate.add_argument('--options',help='New-flow options JSON; no credentials')
    translate.add_argument('--glossary');translate.add_argument('--recipe')
    resume=sub.add_parser('resume');resume.add_argument('job_id')
    share=sub.add_parser('share');share.add_argument('output');share.add_argument('job_ids',nargs='+')
    backup=sub.add_parser('backup',help='Independent backup of installed game/tl texts and images')
    backup.add_argument('project');backup.add_argument('output')
    args=parser.parse_args(argv)
    if args.command=='verify':
        from .baseline import verify_baseline
        result=verify_baseline(resource_root());print(json.dumps(result,indent=2));return 0 if result['valid'] else 1
    from .bootstrap import Services
    services=Services()
    if args.command in (None,'gui','classic'):
        from .ui.application import run_gui
        return run_gui(services,classic=args.command=='classic',smoke_output=getattr(args,'smoke_output',None))
    if args.command=='list':print(json.dumps(services.jobs(),ensure_ascii=False,indent=2));return 0
    if args.command=='backup':
        from .packaging.translation_backup import TranslationBackup
        result=TranslationBackup().build(args.project,args.output)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    if args.command=='share':
        from .packaging.share_package_builder import SharePackageBuilder
        result=SharePackageBuilder().build([services.data/'jobs'/i for i in args.job_ids],args.output)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    if args.command=='translate':
        options=load_json(args.options,{}) if args.options else {}
        if args.recipe:options['ui_recipe']=load_json(args.recipe)
        job=services.create_job(args.project,args.target,args.profile,args.provider,args.source,args.model,
                                True,args.mode,
                                options,load_json(args.glossary,{}) if args.glossary else {})
    else:job=services.load_job(args.job_id)
    print('JOB_ID='+job.job_id,flush=True)
    from .core.translation_job import TranslationJobRunner
    runner=TranslationJobRunner(services,job,callback=lambda e:print(json.dumps(jsonable(e),ensure_ascii=False),flush=True))
    try:
        result=asyncio.run(runner.run())
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except KeyboardInterrupt:
        runner.queue.cancelled.set()
        print('Interrupted; accepted checkpoints remain for explicit resume')
        return 130
