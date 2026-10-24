"""Measured, bounded text layer with effects. No model is asked to draw text."""
from PIL import Image, ImageDraw, ImageFont
from .typography_validation import validate_typography
from .image_reconstruction import preserve_outside


def _length(font,text,tracking):
    return font.getlength(text)+max(0,len(text)-1)*tracking


def _wrap(text,font,width,tracking):
    lines=[]
    for paragraph in text.split('\n'):
        line=''
        for word in paragraph.split(' '):
            trial=(line+' '+word).strip()
            if _length(font,trial,tracking)>width and line:
                lines.append(line);line=word
            else:
                line=trial
        lines.append(line)
    return lines


def compose(background,original,mask,game,text,bounds,profile):
    evidence=validate_typography(game,profile,text)
    x,y,r,b=bounds
    width,height=r-x,b-y
    effects=2*profile.stroke_width+max(abs(v) for v in profile.shadow_offset)+4
    chosen=None
    for size in range(profile.size,max(5,int(profile.size*profile.min_size_ratio))-1,-1):
        font=ImageFont.truetype(evidence['font_path'],size)
        lines=_wrap(text,font,width-effects,profile.tracking)
        line_heights=[max(1,font.getbbox(line or ' ',stroke_width=profile.stroke_width)[3]-font.getbbox(line or ' ',stroke_width=profile.stroke_width)[1]) for line in lines]
        h=sum(line_heights)+profile.line_spacing*max(0,len(lines)-1)
        if len(lines)<=profile.max_lines and h<=height-effects and all(_length(font,t,profile.tracking)<=width-effects for t in lines):
            chosen=(size,font,lines,line_heights,h)
            break
    if not chosen:
        raise ValueError('Typography overflow within approved design limits')
    size,font,lines,line_heights,total_height=chosen
    region=Image.new('RGBA',(width,height),(0,0,0,0))
    draw=ImageDraw.Draw(region)
    top=(height-total_height)//2
    def draw_line(text,position,fill,stroke):
        if not profile.tracking:
            draw.text(position,text,font=font,fill=fill,stroke_width=profile.stroke_width,stroke_fill=stroke,anchor='lt')
        else:
            tx,ty=position
            for char in text:
                draw.text((tx,ty),char,font=font,fill=fill,stroke_width=profile.stroke_width,stroke_fill=stroke,anchor='lt')
                tx+=font.getlength(char)+profile.tracking
    for line,line_height in zip(lines,line_heights):
        length=_length(font,line,profile.tracking)
        left=effects//2 if profile.alignment=='left' else width-effects//2-length if profile.alignment=='right' else (width-length)/2
        if profile.shadow_color[3]:
            draw_line(line,(left+profile.shadow_offset[0],top+profile.shadow_offset[1]),tuple(profile.shadow_color),tuple(profile.shadow_color))
        draw_line(line,(left,top),tuple(profile.color),tuple(profile.stroke_color))
        top+=line_height+profile.line_spacing
    if profile.rotation:
        rotated=region.rotate(profile.rotation,resample=Image.Resampling.BICUBIC,expand=True)
        visible=rotated.getbbox()
        if visible:
            rotated=rotated.crop(visible)
            if rotated.width>width or rotated.height>height:
                raise ValueError('Rotated text exceeds authorized region')
            region=Image.new('RGBA',(width,height),(0,0,0,0))
            region.alpha_composite(rotated,((width-rotated.width)//2,(height-rotated.height)//2))
    bbox=region.getbbox()
    if bbox and (bbox[0]<=0 or bbox[1]<=0 or bbox[2]>=width or bbox[3]>=height):
        raise ValueError('Text effect touches crop boundary; review geometry')
    layer=Image.new('RGBA',background.size,(0,0,0,0))
    layer.alpha_composite(region,(x,y))
    candidate=Image.alpha_composite(background.convert('RGBA'),layer)
    result=preserve_outside(original,candidate,mask)
    evidence.update(size_effective=size,lines=lines,bounds=list(bounds),rotation=profile.rotation)
    return result,layer,evidence
