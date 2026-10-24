from pathlib import Path
import pytest
from linguanova_next.models.model_registry import selected_manifest
from linguanova_next.models.model_manifest import verify_model
from linguanova_next.models.model_compatibility import capability_report


def test_real_model_manifest_is_pinned_and_complete(tmp_path):
    manifest=selected_manifest()
    assert len(manifest['revision'])==40 and manifest['total_bytes']>6_000_000_000
    weights=[f for f in manifest['files'] if f['path'].endswith('.safetensors')]
    assert len(weights)==4 and all(len(f['sha256'])==64 and f['size']>0 for f in manifest['files'])
    with pytest.raises(ValueError,match='missing'):verify_model(tmp_path,manifest)


def test_optional_real_inference_when_installed(tmp_path):
    import os
    directory=os.environ.get('LINGUANOVA_NEXT_TEST_MODEL_DIR')
    if not directory:
        pytest.skip('Real inference not executed: no explicitly installed model directory provided')
    info=capability_report()
    if not info['available']:
        pytest.skip('Real inference not executed: optional Torch/Diffusers runtime absent')
    from PIL import Image
    from linguanova_next.adapters.generative_inpainting_adapter import DiffusersInpaintingAdapter
    from linguanova_next.image.image_reconstruction import mask_for_regions
    from linguanova_next.image.image_validation import validate_pixels
    manifest=selected_manifest();verify_model(directory,manifest)
    original=Image.new('RGBA',(256,128),(30,70,80,255))
    mask=mask_for_regions(original.size,[(80,40,176,88)])
    result=DiffusersInpaintingAdapter().restore(original,mask,directory,{'device':os.environ.get('LINGUANOVA_NEXT_TEST_DEVICE','cuda'),'allow_unverified_hardware':True,'steps':20})
    assert validate_pixels(original,result,mask)['outside_mask_equal']
