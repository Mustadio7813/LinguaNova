from PIL import Image


def validate_pixels(original,result,mask):
    import numpy as np
    a=np.asarray(original.convert('RGBA'));b=np.asarray(result.convert('RGBA'))
    if a.shape!=b.shape or mask.size!=original.size:
        raise ValueError('Image geometry changed')
    outside=np.asarray(mask.convert('L'))==0
    if not np.array_equal(a[outside],b[outside]):
        raise ValueError('Pixels/alpha outside authorized mask changed')
    return {'outside_mask_equal':True,'dimensions_equal':True,'alpha_outside_equal':True,
            'residual_text_review':'required','legibility_review':'required'}


def save_lossless(path,image,source_format):
    # Preserve resource names and references. JPEG is never silently recoded
    # or renamed; its lossy round-trip cannot satisfy exact pixel equality.
    if source_format not in ('PNG','WEBP','BMP','TIFF'):
        raise ValueError('Exact-pixel localized export unsupported for '+source_format+'; explicit path recipe needed')
    kwargs={'lossless':True,'exact':True} if source_format=='WEBP' else {}
    image.save(path,format=source_format,**kwargs)
    with Image.open(path) as reopened:
        import numpy as np
        if not np.array_equal(np.asarray(image.convert('RGBA')),np.asarray(reopened.convert('RGBA'))):
            raise ValueError('Lossless encoded output changed decoded pixels')
