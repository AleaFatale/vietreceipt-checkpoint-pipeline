"""Local review for arbitrary pipeline input images; no gold or prediction edits."""
import html
import json
from pathlib import Path
import shutil
import sys

from run_receipt import HEADER_LABELS, TABLE_LABELS, cell_text


def main():
    root = Path(sys.argv[1]).resolve()
    summary = json.loads((root/'summary.json').read_text(encoding='utf-8'))
    esc = lambda x: html.escape(str(x), quote=True)
    body = []
    for row in summary['runs']:
        folder = root/Path(row['output']).name
        result = json.loads((folder/'result.json').read_text(encoding='utf-8'))
        body.append('<p class="note">Nguồn chữ: '+esc(result.get('text_source','legacy'))+' · '+esc(result.get('footer',{}).get('recognizer',''))+'</p>')
        image = Path(result['image'])
        source = folder/('source'+image.suffix.lower())
        shutil.copy2(image,source)
        body.append('<section><h2>'+esc(image.name)+'</h2><p>Ảnh gốc: '+esc(str(image))+'</p><p><a href="'+source.relative_to(root).as_posix()+'">Mở ảnh nguồn</a> · <a href="'+folder.name+'/result.json">JSON toàn bộ</a></p>')
        body.append('<table><tr><th>Bước</th><th>Trạng thái chạy</th><th>Log / lỗi</th></tr>')
        for stage,state in result['stages'].items():
            log='<a href="'+folder.name+'/'+esc(state['log'])+'">Log</a>' if state.get('log') else ''
            body.append('<tr><td>'+esc(stage)+'</td><td>'+esc(state['status'])+'</td><td>'+log+' '+esc(state.get('error',''))+'</td></tr>')
        body.append('</table><div class="photos"><img src="'+source.relative_to(root).as_posix()+'" alt="Ảnh gốc">')
        if (folder/'pp-preview.jpg').exists():body.append('<img src="'+folder.name+'/pp-preview.jpg" alt="Phân vùng PP mới">')
        body.append('</div><h3>Header</h3><table><tr><th>Trường</th><th>Giá trị</th><th>Nguồn</th></tr>')
        header=result.get('header',{})
        for key,label in HEADER_LABELS.items():
            cell=header.get('fields',{}).get(key)
            if cell:body.append('<tr><td>'+esc(label)+'</td><td>'+esc(cell_text(cell))+'</td><td>'+esc(header.get('field_sources',{}).get(key,{}).get('engine','vietocr-checkpoint'))+'</td></tr>')
        body.append('</table><h3>Table - dòng hàng</h3><table><tr>'+''.join('<th>'+esc(x)+'</th>' for x in TABLE_LABELS.values())+'</tr>')
        for item in result.get('table',{}).get('line_items',[]):
            body.append('<tr>'+''.join('<td>'+esc(cell_text(item[k]))+'</td>' for k in TABLE_LABELS)+'</tr>')
        body.append('</table><h3>Footer - thanh toán</h3>')
        footer=result.get('footer',{});pay=footer.get('payment',{})
        body.append('<p><b>Tổng thanh toán:</b> '+esc(pay.get('amount_vnd','—'))+' VND ['+esc(pay.get('status','UNKNOWN'))+'] · '+esc(pay.get('source',''))+'</p><ul>')
        for line in footer.get('lines',[]):body.append('<li>'+esc(line['text'])+'</li>')
        body.append('</ul><p><a href="'+folder.name+'/reader-document.json">Reader OCR</a> · <a href="'+folder.name+'/header-evidence.json">VietOCR cả trang</a> · <a href="'+folder.name+'/table.json">Table JSON</a> · <a href="'+folder.name+'/footer.json">Footer JSON</a></p></section>')
    css='body{font:16px/1.6 system-ui;margin:30px;background:#f3f7fa;color:#20384a}main{max-width:1280px;margin:auto}section{padding:24px;background:white;margin:24px 0;border:1px solid #cfdee7;border-radius:10px}table{width:100%;border-collapse:collapse}td,th{border:1px solid #ccdae4;padding:10px;text-align:left;vertical-align:top}th{background:#e5f1f6}a{color:#075d91}.photos{display:flex;gap:20px;flex-wrap:wrap;margin:24px 0}.photos img{max-width:46%;max-height:650px}.note{background:#fff0bc;padding:16px}'
    (root/'index.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><title>Hóa đơn đầy đủ - repo GitHub</title><style>'+css+'</style><main><h1>Reader → Phân vùng → Header → Table → Footer</h1><p class="note">Đây là lượt chạy mới từ ảnh. Trạng thái OK nói bước chạy xong, không khẳng định nội dung đúng toàn bộ. PRESENT nghĩa là đã trích được giá trị, không khẳng định đọc đúng. Chưa chấm bằng gold trên trang này. Windows không có nhánh Apple Vision.</p>'+''.join(body)+'</main></html>',encoding='utf-8')
    print(root/'index.html')


if __name__=='__main__':main()
