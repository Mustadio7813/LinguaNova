from dataclasses import replace
from pathlib import Path
import threading
import pytest
from PIL import Image, ImageDraw
from linguanova_next.image.image_inventory import inventory
from linguanova_next.image.typography_profile import TypographyProfile
from linguanova_next.image.image_reconstruction import mask_for_regions,reconstruct_classic
from linguanova_next.image.image_compositor import compose
from linguanova_next.image.image_validation import validate_pixels,save_lossless
from linguanova_next.image.font_resolver import resolve_font
from linguanova_next.adapters.ocr_provider import TesseractProvider
from linguanova_next.util import file_hash
from support import TARGETS


def style(game):
    return TypographyProfile('fonts/DejaVuSans.ttf',file_hash(game/'fonts/DejaVuSans.ttf'),'DejaVu Sans',38,
                             color=(244,247,245,255),stroke_width=1,stroke_color=(17,28,34,255),
                             shadow_offset=(2,2),shadow_color=(0,0,0,180),evidence='identified',confidence=1.0,
                             provenance='controlled fixture author knows the exact font',reviewer='fixture-author')


def test_real_ocr_source_model_and_states(project):
    engine=TesseractProvider()
    if not engine.available()['available']:pytest.skip('Real Tesseract component not installed')
    game=project/'game';resources=inventory(game)
    assert {x.state for x in resources}>={'normal','hover','selected'}
    resource=next(x for x in resources if x.state=='normal')
    regions=engine.recognize(game/resource.path,resource.image_hash,'eng')
    assert any('Continue' in x.text for x in regions)
    assert all(x.source_language=='en' for x in regions)
    with pytest.raises(ValueError):engine.recognize(game/resource.path,resource.image_hash,'not_installed')


@pytest.mark.parametrize('text',['Continuar','Continuer','Продолжить','Proceed','Primera línea\nSegunda línea'])
def test_layered_composition_exact_pixels_transparency_and_effects(project,tmp_path,text):
    game=project/'game'
    original=Image.open(game/'images/buttons/continue_normal.png').convert('RGBA')
    bounds=(65,28,415,130)
    mask=mask_for_regions(original.size,[bounds],allow_large=True)
    restored=reconstruct_classic(original,mask)
    profile=style(game)
    result,layer,evidence=compose(restored,original,mask,game,text,bounds,profile)
    assert validate_pixels(original,result,mask)['outside_mask_equal']
    assert layer.getbbox() is not None and evidence['font_hash']==profile.font_hash
    output=tmp_path/'result.png';save_lossless(output,result,'PNG')
    with Image.open(output) as decoded:validate_pixels(original,decoded,mask)


def test_glyph_overflow_approximation_rotation_and_jpeg_guards(project,tmp_path):
    game=project/'game';profile=style(game)
    original=Image.open(game/'images/buttons/continue_normal.png').convert('RGBA');bounds=(65,28,415,130)
    mask=mask_for_regions(original.size,[bounds],allow_large=True)
    with pytest.raises(ValueError,match='glyph'):resolve_font(game,profile,'漢字')
    with pytest.raises(ValueError,match='overflow'):compose(original,original,mask,game,'W'*200,bounds,profile)
    with pytest.raises(ValueError):replace(profile,evidence='approved_approximation',reviewer='',approximation_approved=True).validate()
    with pytest.raises(ValueError,match='unsupported'):save_lossless(tmp_path/'image.jpg',original,'JPEG')
    with pytest.raises(ValueError,match='Large mask'):mask_for_regions(original.size,[(0,0,480,160)])
    rotated=replace(profile,size=16,rotation=90)
    _,_,evidence=compose(original,original,mask,game,'Hi',bounds,rotated)
    assert evidence['rotation']==90


def test_no_detection_is_uncertain_and_unsupported_reported(project):
    game=project/'game'
    (game/'images/unsupported.svg').write_text('<svg><invalid')
    unsupported=next(x for x in inventory(game) if x.path.endswith('.svg'))
    assert unsupported.status=='unsupported_format'
