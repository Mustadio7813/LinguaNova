"""Real codecs/OCR; controlled translations explicitly isolate provider behavior."""
import asyncio
import io
import pickle
import struct
import zlib
from pathlib import Path
from dataclasses import replace
import pytest
from PIL import Image, ImageDraw, ImageFont
from linguanova_next.adapters.resource_catalog import ResourceCatalog
from linguanova_next.adapters.extraction_adapter import game_directory
from linguanova_next.image.image_inventory import inventory
from linguanova_next.image.image_formats import decode, encode, DecodedImage, _path_svg, ico_bytes
from linguanova_next.image.typography_inventory import inventory_fonts
from linguanova_next.packaging.native_export import existing_strings, native_export
from linguanova_next.core.translation_job import TranslationJobRunner
from linguanova_next.contracts.entry import Occurrence
from linguanova_next.contracts.result import EntryResult
from linguanova_next.util import load_json, file_hash
from support import FixtureProvider


FORMATS=[('.png','PNG'),('.jpg','JPEG'),('.jpeg','JPEG'),('.webp','WEBP'),('.avif','AVIF'),
         ('.svg','SVG'),('.bmp','BMP'),('.tga','TGA'),('.ico','ICO')]


def rpa(path, members, *, version=3, prefix=0, split=False):
    key=0x23984367 if version==3 else 0
    header=(f'RPA-3.0 {0:016x} {key:08x}\n' if version==3 else f'RPA-2.0 {0:016x}\n').encode()
    body=b'';index={}
    for name,data in members.items():
        chunks=[data[:len(data)//2],data[len(data)//2:]] if split else [data]
        index[name]=[]
        for chunk in chunks:
            start=chunk[:prefix];disk=chunk[prefix:]
            index[name].append((len(header+body)^key,len(disk)^key,start))
            body+=disk
    offset=len(header+body)
    header=(f'RPA-3.0 {offset:016x} {key:08x}\n' if version==3 else f'RPA-2.0 {offset:016x}\n').encode()
    path.write_bytes(header+body+zlib.compress(pickle.dumps(index,protocol=2)))


def bitmap(project):
    image=Image.new('RGBA',(240,100),(20,31,41,255))
    font=ImageFont.truetype(str(project/'game/fonts/DejaVuSans.ttf'),30)
    ImageDraw.Draw(image).text((120,50),'Continue',font=font,anchor='mm',fill=(245,247,249,255))
    return image


def image_bytes(project, suffix, fmt):
    image=bitmap(project)
    if fmt=='SVG':return _path_svg(image)
    if fmt=='ICO':return ico_bytes(image)
    stream=io.BytesIO();options={}
    if fmt=='JPEG':image=image.convert('RGB');options.update(quality=98,subsampling=0)
    if fmt=='WEBP':options.update(lossless=True,exact=True)
    if fmt=='AVIF':options.update(quality=100,subsampling='4:4:4')
    if fmt=='ICO':options.update(sizes=[image.size],bitmap_format='bmp')
    image.save(stream,format=fmt,**options)
    return stream.getvalue()


@pytest.mark.parametrize('version,prefix,split',[(2,0,False),(3,0,False),(3,12,True)])
def test_real_archive_prefix_chunks_and_loose_precedence(project,version,prefix,split):
    game=project/'game';data=image_bytes(project,'.png','PNG')
    rpa(game/'a.rpa',{'images/packed.png':data,'fonts/packed.ttf':(game/'fonts/DejaVuSans.ttf').read_bytes()},version=version,prefix=prefix,split=split)
    rpa(game/'z.rpa',{'images/priority.png':b'winning archive'},prefix=prefix)
    rpa(game/'b.rpa',{'images/priority.png':b'lower archive'},prefix=prefix)
    catalog=ResourceCatalog(game)
    assert catalog.read('images/packed.png')==data
    assert catalog.read('images/priority.png')==b'winning archive'
    (game/'images/priority.png').write_bytes(data)
    assert ResourceCatalog(game).read('images/priority.png')==data
    fonts=inventory_fonts(game,catalog,game.parent/'private_fonts')
    assert any(f['path']=='fonts/packed.ttf' and Path(f['local_path']).is_file() for f in fonts)


def test_archive_paths_do_not_escape_and_bad_archives_are_reported(project,tmp_path):
    game=project/'game'
    rpa(game/'malformed.rpa',{'../../outside.png':b'bad','images/okay.png':image_bytes(project,'.png','PNG')})
    (game/'opaque.rpa').write_bytes(b'not a supported archive')
    catalog=ResourceCatalog(game)
    assert '../../outside.png' not in catalog.resources
    assert catalog.read('images/okay.png')
    assert {d['status'] for d in catalog.diagnostics}>={'archive_member_rejected','archive_unverified'}
    assert not (tmp_path/'outside.png').exists()


@pytest.mark.parametrize('suffix,fmt',FORMATS)
def test_native_format_real_decoding_ocr_composition_and_export(services,project,suffix,fmt):
    game=project/'game'
    for path in (game/'images').rglob('*.png'):path.unlink()
    data=image_bytes(project,suffix,fmt)
    rpa(game/'assets.rpa',{'images/deep/button'+suffix:data,'images.rpy':('image sign = "images/deep/button'+suffix+'"\n').encode()},prefix=8,split=True)
    before=file_hash(game/'assets.rpa')
    job=services.create_job(project,'fr',text_enabled=False,image_enabled=True,options={'attempts':1})
    report=asyncio.run(TranslationJobRunner(services,job,provider_factory=FixtureProvider).run())
    images=load_json(services.data/'jobs'/job.job_id/'image_results.json')
    assert len(images)==1
    item=next(iter(images.values()))
    assert item['status']=='exported_automatic',item
    assert item['origin']=='rpa' and item['regions'][0]['region']['text']=='Continue'
    assert item['regions'][0]['response']['text']=='Continuer'
    assert item['visual_review']=='not_executed'
    path=services.data/'jobs'/job.job_id/'published'/item['output_path']
    assert path.suffix==suffix and decode(path.read_bytes(),suffix).format==fmt
    assert decode(path.read_bytes(),suffix).frames[0].size==(240,100)
    assert report['visual_coverage']['numerator']==1
    assert report['visual']['human_reviewed_coverage']['numerator']==0
    assert file_hash(game/'assets.rpa')==before
    if fmt=='SVG':assert b'<image' not in path.read_bytes() and b'<text' not in path.read_bytes()


@pytest.mark.parametrize('fmt,suffix',[('PNG','.png'),('WEBP','.webp'),('GIF','.gif'),('TIFF','.tiff')])
def test_sequence_frame_count_pixels_and_timing_are_preserved(project,tmp_path,fmt,suffix):
    first=bitmap(project);second=first.copy()
    ImageDraw.Draw(second).rectangle((0,0,8,8),fill=(255,200,0,255))
    source=DecodedImage([first,second],fmt,[120,260],loop=2)
    out=tmp_path/('sequence'+suffix)
    metadata=encode(out,[first,second],source)
    restored=decode(out.read_bytes(),suffix)
    assert len(restored.frames)==2 and restored.frames[0].size==first.size
    if fmt in ('PNG','WEBP','GIF'):
        assert restored.durations==[120,260]
        assert restored.loop==2


def test_rpy_reference_scope_dynamic_paths_and_all_assets(project):
    game=project/'game'
    (game/'images.rpy').write_text('image a = "images/buttons/continue_%s.png"\nimage b = "images/packed.avif"\n')
    rpa(game/'assets.rpa',{'images/packed.avif':image_bytes(project,'.avif','AVIF')})
    rows=inventory(game,scope='rpy')
    assert {r.path for r in rows}>={'images/buttons/continue_hover.png','images/buttons/continue_normal.png',
                                  'images/buttons/continue_selected.png','images/packed.avif'}
    assert next(r for r in rows if r.path.endswith('.avif')).origin=='rpa'
    (game/'images/unreferenced.png').write_bytes(image_bytes(project,'.png','PNG'))
    assert 'images/unreferenced.png' not in {r.path for r in rows}
    assert 'images/unreferenced.png' in {r.path for r in inventory(game,scope='all')}
    assert game_directory(game/'assets.rpa')==game.resolve()
    assert game_directory(game/'images.rpy')==game.resolve()


@pytest.mark.parametrize('kind',['rpa','rpy','rpyc'])
def test_selected_input_limits_images_and_freezes_inferred_scope(services,project,kind):
    import json
    game=project/'game'
    png=image_bytes(project,'.png','PNG')
    (game/'images/unrelated.png').write_bytes(png)
    if kind=='rpa':
        selected=game/'selected.rpa'
        rpa(selected,{'images/selected.png':png})
        rpa(game/'other.rpa',{'images/other.png':png})
        expected={'images/selected.png'}
    elif kind=='rpy':
        selected=game/'selected.rpy'
        selected.write_text('image selected = "images/selected.png"\n')
        (game/'images/selected.png').write_bytes(png)
        (game/'other.rpy').write_text('image unrelated = "images/unrelated.png"\n')
        expected={'images/selected.png'}
    else:
        selected=game/'selected.rpyc'
        selected.write_bytes((Path(__file__).parent/'fixtures/ocr_scripts/images.rpyc').read_bytes())
        for suffix,fmt in [('.png','PNG'),('.avif','AVIF')]:
            path=game/('images/deep/button'+suffix)
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(image_bytes(project,suffix,fmt))
        expected={'images/deep/button.png','images/deep/button.avif'}
    job=services.create_job(selected,'fr',text_enabled=False,image_enabled=True)
    options=json.loads(job.options_json)
    assert options['image_sources']==kind
    assert options['image_input']==selected.name
    assert {r.path for r in inventory(game,scope=kind,input_path=options['image_input'])}==expected


def test_packed_translation_owner_blocks_duplicate_export(services,project,tmp_path):
    game=project/'game'
    rpa(game/'translations.rpa',{'tl/french/previous.rpy':b'translate french strings: # valid comment\n    old "Continue"\n    new "Continuer"\n'},prefix=5)
    assert existing_strings(game,'french')[0]['Continue']=='Continuer'
    job=services.create_job(project,'fr')
    entry=Occurrence.create('script.rpy',1,'Continue','say','dialogue','source')
    result=EntryResult(entry.occurrence_id,job.identity,'accepted',candidate='Continuer')
    updated,mapping,warnings=native_export(game,tmp_path/'stage',job,[entry],{entry.occurrence_id:result})
    assert updated[entry.occurrence_id].status=='duplicate' and 'Continue' not in mapping


@pytest.mark.parametrize('packed',[False,True])
def test_real_engine_compiled_references_and_translation_owners(project,packed):
    game=project/'game'
    fixture=Path(__file__).parent/'fixtures/ocr_scripts'
    compiled=(fixture/'images.rpyc').read_bytes()
    previous=(fixture/'existing_tl.rpyc').read_bytes()
    members={'only_compiled.rpyc':compiled,'tl/french/previous.rpyc':previous,
             'images/deep/button.png':image_bytes(project,'.png','PNG'),
             'images/deep/button.avif':image_bytes(project,'.avif','AVIF')}
    if packed:
        rpa(game/'compiled.rpa',members,prefix=16,split=True)
    else:
        for name,data in members.items():
            path=game/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    rows=inventory(game,scope='rpyc')
    assert {r.path for r in rows}=={'images/deep/button.png','images/deep/button.avif'}
    assert all('only_compiled.rpyc' in r.references for r in rows)
    assert existing_strings(game,'french')[0]['Continue']=='Continuer'
    from linguanova_next.adapters.extraction_adapter import ExtractionAdapter
    entries,issues=ExtractionAdapter().extract(game)
    assert any(e.path=='only_compiled.rpyc' and e.original=='Continue' for e in entries)


def test_transparent_white_letters_ocr_and_alpha_cleanup(services,project):
    from linguanova_next.image.image_reconstruction import reconstruct_classic,mask_for_regions
    import numpy as np
    game=project/'game'
    for p in (game/'images').rglob('*.png'):p.unlink()
    image=Image.new('RGBA',(240,100),(0,0,0,0))
    font=ImageFont.truetype(str(game/'fonts/DejaVuSans.ttf'),30)
    ImageDraw.Draw(image).text((120,50),'Continue',font=font,anchor='mm',fill='white')
    image.save(game/'images/white_text.png')
    mask=mask_for_regions(image.size,[(20,20,220,80)],allow_large=True)
    background=reconstruct_classic(image,mask)
    assert np.asarray(background.getchannel('A')).max()==0
    job=services.create_job(project,'fr',text_enabled=False,image_enabled=True,options={'attempts':1})
    asyncio.run(TranslationJobRunner(services,job,provider_factory=FixtureProvider).run())
    item=next(iter(load_json(services.data/'jobs'/job.job_id/'image_results.json').values()))
    assert item['status']=='exported_automatic',item
    assert item['regions'][0]['region']['text']=='Continue'
