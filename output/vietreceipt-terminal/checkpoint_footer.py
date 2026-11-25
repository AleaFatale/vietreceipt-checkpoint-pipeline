"""Build Footer from shared VietOCR evidence, never from Paddle text.

Reader still detects boxes. PP links select the Footer blocks. All text and
probabilities come from the same checkpoint run used for Header and Table.
"""
from math import ceil, floor
from pathlib import Path
import sys

from PIL import Image, ImageOps
from footer_amount import read_payable


def rotate_point(point, angle):
    x, y = point['x'], point['y']
    return {0:(x,y),90:(1-y,x),180:(1-x,1-y),270:(y,1-x)}[angle]


def build_footer(image, out, document, metadata, links=None):
    footer_lib = Path(__file__).resolve().parent/'bundles/footer'
    if str(footer_lib) not in sys.path:
        sys.path.append(str(footer_lib))
    from footer_layout import group_rows, locate_footer, text_from_lines

    if len(document['pages']) != 1:
        raise ValueError('Single-image Footer expects one evidence page')
    angle = metadata['pages'][0]['orientation_clockwise']
    if angle not in (0,90,180,270):
        raise ValueError('Invalid Reader orientation')
    with Image.open(image) as original:
        upright = ImageOps.exif_transpose(original).convert('RGB')
    page = document['pages'][0]['evidence']
    expected = (page['image']['width_px'],page['image']['height_px'])
    if upright.size != expected:
        raise ValueError('Image and shared checkpoint coordinates have different frames')
    if angle:
        upright = upright.rotate(-angle,expand=True)
    upright.save(Path(out)/'footer-upright.png')
    width,height = upright.size
    lines = []
    for block in page['blocks']:
        points = [rotate_point(p,angle) for p in block['polygon']]
        lines.append({'text':block['text'],'score':block['confidence'],
            'poly':[[x*width,y*height] for x,y in points],
            'source_block_id':block['block_id'],'source_ocr_run_id':document['ocr_run_id'],
            'text_source':'vietocr-checkpoint','source_pass':'shared-checkpoint'})
    footer_ids = {b['block_id'] for b in (links or {}).get('blocks',[])
                  if b['status']=='ASSIGNED' and any(m['label']=='footer' for m in b['matches'])}
    if footer_ids:
        selected = [line for line in lines if line['source_block_id'] in footer_ids]
        method = 'PP Footer blocks + shared VietOCR checkpoint text'
    else:
        region = locate_footer(lines,(height,width))
        selected = [line for line in lines if region.contains(line)] if region else []
        method = 'Footer cues in shared checkpoint text' if region else 'no checkpoint Footer cue'
    if selected:
        xs = [p[0] for line in selected for p in line['poly']]
        ys = [p[1] for line in selected for p in line['poly']]
        box = [max(0,floor(min(xs))),max(0,floor(min(ys))),min(width,ceil(max(xs))),height]
        _,typical,slope = group_rows(selected)
        geometry = [typical,slope]
        text = text_from_lines(selected,geometry=geometry)
    else:
        box,geometry,text = None,None,''
    payment = read_payable(text)
    payment['source'] = 'VIETOCR_CHECKPOINT_FOOTER'
    return {'box':box,'method':method,'text':text,'lines':selected,'row_geometry':geometry,
            'layout_input_shape':[height,width],'layout_seconds':0,'footer_seconds':0,
            'payment':payment,'recognizer':'vietocr-pos-disambiguation / vgg19_bn+seq2seq',
            'coordinate_system':'pixels_on_footer_upright_png','orientation_clockwise':angle,
            'source_ocr_run_id':document['ocr_run_id'],'text_source':'vietocr-checkpoint',
            'paddle_text_fallback':False,'confidence_semantics':'uncalibrated VietOCR token probability',
            'empty_text_policy':'do not replace missing checkpoint text with Paddle text'}
