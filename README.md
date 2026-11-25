# VietReceipt — shared VietOCR checkpoint pipeline

Repo bàn giao độc lập cho nhóm: ảnh hóa đơn → khung chữ → phân vùng →
VietOCR checkpoint → Header / bảng hàng / Footer → HTML và JSON.

## Chạy nhanh trên Windows

Cài Python **3.12**, Git và Git LFS. Nên clone vào đường dẫn ngắn, ví dụ
`C:\AI\vietreceipt-checkpoint-pipeline`.

```powershell
git lfs install
git clone https://github.com/AleaFatale/vietreceipt-checkpoint-pipeline.git
Set-Location .\vietreceipt-checkpoint-pipeline
git lfs pull
& .\setup.ps1
& .\run.ps1 -OpenReport
```

Lần cài đầu cần Internet để tải thư viện Python. Repo kèm trọng số qua Git LFS,
bao gồm VietOCR, PP-DocLayoutV3 và 3 model Reader. Cài xong có thể chạy ảnh
bằng các model local. Tổng trọng số khoảng **241 MB**, chưa tính thư viện.

Nếu PowerShell chặn script, có thể dùng các lệnh Python tương đương:

```powershell
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
& .\.venv\Scripts\python.exe .\run.py --open
```

Ảnh mặc định: **`examples/00001.png`**, hóa đơn giả lập, không có giá trị
thanh toán. Đáp án phát triển: `examples/00001.gold.json`. Các lệnh chạy
pipeline không đọc file gold.

Test hóa đơn của bạn:

```powershell
& .\run.ps1 -Image 'C:\anh\hoa-don.jpg' -OpenReport
```

Hoặc:

```powershell
& .\.venv\Scripts\python.exe .\run.py --image 'C:\anh\hoa-don.png' --open
```

Kết quả mỗi lần ở **`runs/<thời-gian>/index.html`**, kèm ảnh nguồn, ảnh chia
vùng, JSON và log từng bước. Cần thư mục đầu ra mới cho mỗi lần chạy.
CLI này nhận JPG/JPEG/PNG; chưa cung cấp luồng PDF ở lệnh `run.py`.

## Từng phần đang dùng gì?

| Bước | Model / code | Vai trò |
|---|---|---|
| Chỉnh chiều | PP-LCNet_x1_0_doc_ori | Nhận diện chiều ảnh |
| Tìm khung chữ | PP-OCRv3_mobile_det | Vị trí crop chữ |
| Chữ tham chiếu | latin_PP-OCRv3_mobile_rec | Lưu chữ Reader; hỗ trợ quy tắc phân vùng |
| Phân vùng | PP-DocLayoutV3 + adapter | Header / Table / Footer |
| Đọc chữ cả ba phần | VietOCR VGG19-BN + Seq2Seq đã fine-tune | **Cùng một checkpoint** |
| Trích Header | KIE quy tắc | 9 trường Header |
| Trích Table | Retail Table KIE | Tên, đơn vị, số lượng, đơn giá, thành tiền |
| Trích Footer | Quy tắc vùng + tổng tiền | Dòng cuối và tổng thanh toán |

VietOCR đọc lại mọi crop từ cùng ảnh. Header, Table và Footer dùng chung
`checkpoint-document.json`; không tự thay chữ checkpoint bằng Paddle.
Ảnh crop được thêm viền trắng bằng 20% chiều cao trước resize. Trọng số
không được train lại trong lần tích hợp này.

`PRESENT` = đã trích được giá trị, **không phải đã đọc đúng**.
`UNKNOWN` = chưa có đủ căn cứ để lấy giá trị.
`AMBIGUOUS` = cần xác nhận. Confidence của model không phải accuracy.

## Code nằm ở đâu?

| Folder / file | Nội dung |
|---|---|
| `run.py`, `run.ps1` | Điểm bắt đầu chạy một ảnh |
| `verify_models.py` | Kiểm tra kích thước và SHA-256 model |
| `ai/document_reader`, `ai/ocr` | Đọc ảnh, chiều ảnh và khung chữ |
| `output/pp-doclayout-v3-1511/code` | Phân vùng PP và quy tắc |
| `output/pp-doclayout-v3-1511/models` | Trọng số PP |
| `output/vietreceipt-terminal/run_receipt.py` | Điều phối các bước |
| `output/vietreceipt-terminal/stages.py` | Gọi Reader, PP, checkpoint và KIE |
| `output/vietreceipt-terminal/bundles/HEADER-CHECKPOINT-TICH-HOP/checkpoint_ocr.py` | Nạp trọng số, cắt ảnh và gọi VietOCR |
| `output/vietreceipt-terminal/bundles/HEADER-CHECKPOINT-TICH-HOP/models/vietocr-pos` | Checkpoint VietOCR + cấu hình |
| `output/vietreceipt-terminal/bundles/retail/ai/kie/retail_table.py` | KIE Table |
| `output/vietreceipt-terminal/checkpoint_footer.py` | Footer dùng chữ checkpoint |
| `models/paddle-reader` | Trọng số Reader local |
| `schemas` | Contract dữ liệu |
| `examples` | 1 ảnh giả lập và gold; không kèm dataset hóa đơn riêng |

## Kiểm tra

```powershell
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\python.exe .\verify_models.py
& .\.venv\Scripts\python.exe .\output\vietreceipt-terminal\test_checkpoint_routing.py
```

`MODEL-MANIFEST.json` liệt kê đủ model và hash. Nếu file model chỉ có vài
trăm byte hoặc báo thiếu, chạy `git lfs pull`.

Với `result.json`, kiểm tra `text_source = checkpoint`.
`table.source_ocr_run_id` và `footer.source_ocr_run_id` phải trùng
`checkpoint_document.ocr_run_id`. `text-selection.json` ghi model,
preprocessing và nguồn Reader cha.

## Kết quả và giới hạn đã quan sát

- 00001: 5 dòng hàng, tổng 884.000 VND; đã sửa được tên người bán
  `CỬA HÀNG MẪU SAO VIỆT`.
- Vẫn có lỗi: `THỬ → THỨ`, `Sổ → Số`, `Quyển → Quyền`,
  ký hiệu `0% → 0#`.
- Kiểm tra riêng Header với Reader/PP lưu sẵn trên bộ dev 20 mẫu:
  130/163 → 142/163 trường khớp gold khi thêm viền crop; 12 trường tốt lên,
  không có trường PASS chuyển thành FAIL. 163 trường này thuộc **19 ảnh
  giả lập**; 1 ảnh demo còn lại chưa có gold Header đầy đủ.
- Những số này là kiểm tra phát triển, không phải đánh giá trên hóa đơn
  thật độc lập. Repo vẫn cần review dữ liệu đầu ra trước khi dùng.

Xem `docs/VALIDATION.json` cho bằng chứng của lượt kiểm tra bản bàn giao.

## Nguồn

Tách từ `NguyenDong-23/vietreceipt-ocr-pipeline`, commit
`f36913d1fa3a9c06d1f693f018d33acbcd33ab26`, kèm thay đổi dùng chung
checkpoint và hỗ trợ chạy độc lập. Đây là repo mới, không chứa lịch sử
Git hay remote của dự án gốc. Xem `SOURCE_PROVENANCE.md` và model card
kèm trọng số để biết nguồn từng thành phần.
