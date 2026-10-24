"""Classical inpainting, bounded masks and exact unmasked-pixel restoration."""
from PIL import Image, ImageDraw


def mask_for_regions(size,bounds,allow_large=False):
    mask=Image.new('L',size,0)
    draw=ImageDraw.Draw(mask)
    for x,y,r,b in bounds:
        if min(x,y)<0 or r>size[0] or b>size[1] or r<=x or b<=y:
            raise ValueError('Invalid or out-of-canvas authorized bounds')
        draw.rectangle((x,y,r-1,b-1),fill=255)
    fraction=sum(mask.histogram()[1:])/(size[0]*size[1])
    if fraction>.4 and not allow_large:
        raise ValueError('Large mask requires explicit recorded region approval')
    return mask


def preserve_outside(original,candidate,mask):
    original=original.convert('RGBA');candidate=candidate.convert('RGBA')
    if candidate.size!=original.size or mask.size!=original.size:
        raise ValueError('Inpainting changed canvas dimensions')
    return Image.composite(candidate,original,mask.convert('L'))


def reconstruct_classic(original,mask):
    import cv2
    import numpy as np
    rgb=np.asarray(original.convert('RGB'))
    effective=np.asarray(mask.convert('L'))
    restored=cv2.inpaint(rgb,effective,3,cv2.INPAINT_TELEA)
    candidate=Image.fromarray(restored).convert('RGBA')
    # Text-only PNG/WebP buttons use alpha as the glyph silhouette. Keeping
    # the source alpha would leave ghosts of the original letters behind.
    alpha=np.asarray(original.convert('RGBA').getchannel('A'))
    restored_alpha=cv2.inpaint(alpha,effective,3,cv2.INPAINT_TELEA)
    candidate.putalpha(Image.fromarray(restored_alpha))
    return preserve_outside(original,candidate,mask)
