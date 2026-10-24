"""Decode Ren'Py resources to PNG pixels; export genuine original formats.

SVG output uses paths: Ren'Py ignores embedded bitmaps and text elements.
SVGs are flattened at native resolution and this limitation is recorded.
"""
from collections import defaultdict
from dataclasses import dataclass
import io
from pathlib import Path
from PIL import Image

NATIVE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.avif', '.svg', '.bmp', '.tga', '.ico'}
IMAGE_SUFFIXES = NATIVE_SUFFIXES | {'.gif', '.tif', '.tiff', '.apng', '.svgz', '.dds', '.ktx', '.psd', '.jxl'}
MAX_PIXELS = 40_000_000


def register_codecs():
    try:
        import pillow_avif  # noqa: F401
    except ImportError:
        pass


def render_svg(data):
    from defusedxml.ElementTree import fromstring
    from resvg_py import svg_to_bytes
    root = fromstring(data)
    for element in root.iter():
        for key, value in element.attrib.items():
            if key.rsplit('}', 1)[-1] == 'href' and not value.startswith(('#', 'data:')):
                raise ValueError('SVG con recurso externo: debe estar autocontenido')
            if 'url(' in value and not all(part.split(')', 1)[0].strip(' \"\'').startswith('#') for part in value.split('url(')[1:]):
                raise ValueError('SVG con URL externa no admitida')
    result = svg_to_bytes(svg_string=data.decode('utf-8-sig'), dpi=96, skip_system_fonts=True)
    with Image.open(io.BytesIO(result)) as image:
        if image.width * image.height > MAX_PIXELS:
            raise ValueError('SVG demasiado grande para procesar')
        return image.convert('RGBA')


@dataclass
class DecodedImage:
    frames: list
    format: str
    durations: list
    loop: int = 0
    svg: bool = False


def decode(data, suffix=''):
    register_codecs()
    suffix = suffix.lower()
    if suffix == '.svgz':
        import gzip
        data = gzip.decompress(data)
    if suffix in ('.svg', '.svgz') or data.lstrip().startswith((b'<svg', b'<?xml')):
        return DecodedImage([render_svg(data)], 'SVG', [0], svg=True)
    with Image.open(io.BytesIO(data)) as image:
        count = getattr(image, 'n_frames', 1)
        if image.width * image.height * count > MAX_PIXELS:
            raise ValueError('Imagen/secuencia demasiado grande para procesar')
        frames, durations = [], []
        loop, fmt = image.info.get('loop', 0), image.format
        for index in range(count):
            image.seek(index)
            frames.append(image.convert('RGBA').copy())
            durations.append(int(image.info.get('duration', 100 if count > 1 else 0)))
        return DecodedImage(frames, fmt, durations, loop)


def _path_svg(image):
    import numpy as np
    pixels = np.asarray(image.convert('RGBA'))
    width, height = image.size
    colors, active = defaultdict(list), {}
    for y, row in enumerate(pixels):
        changes = np.flatnonzero(np.any(row[1:] != row[:-1], axis=1)) + 1
        boundaries, current = [0, *changes.tolist(), width], {}
        for x, right in zip(boundaries, boundaries[1:]):
            color = tuple(int(v) for v in row[x])
            if color[3]:
                key = (x, right, color)
                current[key] = active.pop(key, y)
        for (x, right, color), top in active.items():
            colors[color].append(f'M{x} {top}h{right-x}v{y-top}h{x-right}z')
        active = current
    for (x, right, color), top in active.items():
        colors[color].append(f'M{x} {top}h{right-x}v{height-top}h{x-right}z')
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    for (r, g, b, a), paths in sorted(colors.items()):
        opacity = '' if a == 255 else f' fill-opacity="{a/255:.8f}"'
        lines.append(f'<path fill="#{r:02x}{g:02x}{b:02x}"{opacity} d="{"".join(paths)}"/>')
    lines.append('</svg>')
    return '\n'.join(lines).encode()


def ico_bytes(image):
    """ICO/DIB with a complete AND mask, required by SDL2_image.

    Pillow omits this mask for 32-bit DIBs. Windows accepts that shortcut;
    older SDL2 decoders used by Ren'Py try to read it and reject the file.
    """
    import numpy as np
    import struct
    frame=image.convert('RGBA')
    stream=io.BytesIO()
    frame.save(stream,format='ICO',sizes=[frame.size],bitmap_format='bmp')
    data=bytearray(stream.getvalue())
    offset=struct.unpack_from('<I',data,18)[0]
    dib_header=struct.unpack_from('<I',data,offset)[0]
    row_bytes=((frame.width+31)//32)*4
    mask=np.zeros((frame.height,row_bytes),dtype='uint8')
    packed=np.packbits(np.asarray(frame.getchannel('A'))[::-1]==0,axis=1,bitorder='big')
    mask[:,:packed.shape[1]]=packed
    expected=dib_header+frame.width*frame.height*4
    if len(data)-offset==expected:
        data.extend(mask.tobytes())
        struct.pack_into('<I',data,14,len(data)-offset)
    return bytes(data)


def encode(path, frames, source, *, jpeg_quality=100):
    import numpy as np
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fmt, options, images = source.format.upper(), {}, frames
    if fmt == 'SVG':
        data = _path_svg(frames[0])
        if path.suffix.lower() == '.svgz':
            import gzip
            data = gzip.compress(data, mtime=0)
        path.write_bytes(data)
    elif fmt == 'ICO':
        path.write_bytes(ico_bytes(frames[0]))
    else:
        if fmt in ('JPEG', 'JPG'):
            images = [frame.convert('RGB') for frame in frames]
            options.update(quality=jpeg_quality, subsampling=0, optimize=True)
        elif fmt == 'WEBP':
            options.update(lossless=True, exact=True)
        elif fmt == 'AVIF':
            options.update(quality=100, subsampling='4:4:4', speed=6)
        elif fmt == 'GIF':
            options.update(disposal=2, optimize=False)
        elif fmt == 'ICO':
            options['sizes'] = [frames[0].size]
            # SDL2_image (Ren'Py 7/8) does not accept PNG payloads in ICO.
            options['bitmap_format'] = 'bmp'
        if len(images) > 1:
            if fmt not in ('PNG', 'WEBP', 'AVIF', 'GIF', 'TIFF'):
                raise ValueError('El formato no admite todos sus cuadros: ' + fmt)
            options.update(save_all=True, append_images=images[1:])
            if fmt != 'TIFF':
                options.update(duration=source.durations, loop=source.loop)
            if fmt == 'PNG':
                options.update(disposal=0, blend=0)
        images[0].save(path, format=fmt, **options)
    decoded = decode(path.read_bytes(), path.suffix)
    if len(decoded.frames) != len(frames):
        raise ValueError('La exportación cambió el número de cuadros')
    losses, exact = [], True
    for before, after in zip(frames, decoded.frames):
        if before.size != after.size:
            raise ValueError('La exportación cambió el lienzo')
        delta = np.abs(np.asarray(before.convert('RGBA')).astype('int16') - np.asarray(after.convert('RGBA')).astype('int16'))
        same = bool(np.all(delta == 0)); exact = exact and same
        losses.append({'exact': same, 'maximum_channel_error': int(delta.max()), 'mean_channel_error': float(delta.mean())})
    if fmt in ('PNG', 'WEBP', 'BMP', 'TIFF', 'TGA', 'ICO') and not exact:
        raise ValueError('La codificación sin pérdida cambió píxeles')
    return {'format': fmt, 'frames': len(frames), 'durations': decoded.durations,
            'decoded_pixels_exact': exact, 'encoding_errors': losses,
            'svg_flattened_at_native_resolution': source.svg,
            'lossy_encoding': fmt in ('JPEG', 'JPG', 'AVIF', 'GIF')}
