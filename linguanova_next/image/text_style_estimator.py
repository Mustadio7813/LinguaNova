"""Estimates are review candidates and never asserted to identify a typeface."""
from PIL import ImageStat


def estimate_style(image, bounds):
    crop=image.convert('RGBA').crop(bounds)
    mean=ImageStat.Stat(crop).mean
    return {'schema_version':1,'font_path':'','font_hash':'','family':'unknown',
            'size':max(6,int((bounds[3]-bounds[1])*.8)),
            'color':[int(v) for v in mean], 'confidence':.15,'evidence':'unverified',
            'provenance':'region average; background influences color',
            'required':'Identify original font and effects or approve an explicit approximation'}
