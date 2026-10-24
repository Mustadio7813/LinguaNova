"""Measured source-font candidates. Estimates are never human approvals."""
from pathlib import Path
from PIL import Image, ImageFont, ImageDraw
import numpy as np
from .typography_profile import TypographyProfile
from .font_resolver import resolve_font
from ..packaging.frozen_resources import resource_root
from ..util import file_hash


def estimate(original, region, translated, fonts):
    import cv2
    x, y, right, bottom = region.bounds
    source = original.crop((x, y, right, bottom)).convert('RGBA')
    pixels = np.asarray(source)
    pad = max(3, (bottom-y)//6)
    outer = np.asarray(original.crop((max(0,x-pad),max(0,y-pad),min(original.width,right+pad),min(original.height,bottom+pad))).convert('RGBA'))
    edges = np.concatenate((outer[0],outer[-1],outer[:,0],outer[:,-1]))
    background = np.median(edges,axis=0)
    difference = np.linalg.norm(pixels.astype(float)-background,axis=2)
    foreground = difference > max(25,float(difference.max())*.45)
    choices = pixels[foreground & (pixels[:,:,3]>40)]
    color = (255,255,255,255)
    if len(choices):
        values, counts = np.unique(choices,axis=0,return_counts=True)
        selected = values[np.argmax(counts)]
        color = tuple(int(v) for v in selected[:3])+(255,)
    target = cv2.resize(foreground.astype('float32'),(160,48))
    candidates = [f for f in fonts if f.get('local_path') and f.get('sha256')]
    bundled = resource_root()/'linguanova_next/data/fonts/DejaVuSans.ttf'
    if bundled.is_file():
        candidates.append({'local_path':str(bundled),'sha256':file_hash(bundled),'family':'DejaVu Sans','variant':'Book'})
    best = None
    for info in candidates[:48]:
        try:
            path = Path(info['local_path'])
            profile = TypographyProfile(str(path),info['sha256'],info['family'],24,evidence='automatic_estimate',provenance='source glyph measurement')
            resolve_font(Path('/'),profile,translated)
            unit = ImageFont.truetype(str(path),100)
            box = unit.getbbox(region.text or 'Ag')
            size = max(6,round((bottom-y)*100/max(1,box[3]-box[1])))
            font = ImageFont.truetype(str(path),size)
            box = font.getbbox(region.text)
            sample = Image.new('L',(max(1,box[2]-box[0]),max(1,box[3]-box[1])),0)
            ImageDraw.Draw(sample).text((-box[0],-box[1]),region.text,font=font,fill=255)
            rendered = cv2.resize(np.asarray(sample).astype('float32')/255,(160,48))
            score = float(np.mean(np.abs(rendered-target)))
            # Penalize source proportions unlike the actual recognized text.
            score += abs(sample.width/max(1,sample.height) - source.width/max(1,source.height))*.025
            if best is None or score<best[0]:best=(score,info,size)
        except (OSError,ValueError,KeyError):
            continue
    if best is None:
        raise ValueError('No hay una fuente con los glifos del idioma destino')
    score, info, size = best
    height = bottom-y
    # Give the translated phrase room; never change the canvas or references.
    extra_x, extra_y = max(8,round((right-x)*.30)), max(5,round(height*.65))
    bounds = (max(0,x-extra_x),max(0,y-extra_y),min(original.width,right+extra_x),min(original.height,bottom+extra_y))
    profile = TypographyProfile(info['local_path'],info['sha256'],info['family'],size,
        color=color,variant=info.get('variant','Regular'),min_size_ratio=.65,max_lines=3,
        line_spacing=max(1,size//10),evidence='automatic_estimate',confidence=max(0,min(1,1-score)),
        provenance='Automatic source glyph/color measurement; original typeface and visual fidelity not certified')
    return profile, bounds
