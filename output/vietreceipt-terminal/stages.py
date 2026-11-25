"""Local adapters for the three stages with independent model runtimes."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from uuid import uuid4

from footer_amount import apply_footer_display, resolve_payable
from header_recovery import recover_header

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
BASE = ROOT.parent / "pp-doclayout-v3-1511"
HEADER = ROOT / "bundles/HEADER-CHECKPOINT-TICH-HOP"
HEADER_SAMPLES = ROOT / "samples/header"
FOOTER = ROOT / "bundles/footer"
RETAIL = ROOT / "bundles/retail/ai/kie/retail_table.py"
PP = BASE / "bundle" if (BASE / "bundle").is_dir() else BASE
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def checkpoint_text_mode():
    return os.environ.get('VIETRECEIPT_TEXT_SOURCE','legacy') == 'checkpoint'


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def table_and_footer_text(image, out, document, metadata):
    spec = importlib.util.spec_from_file_location("retail_bundle", RETAIL)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    table = module.extract_retail_table(document, currency="VND")
    links = out / "pp-region-links.json"
    if links.is_file():
        if str(HEADER) not in sys.path:
            sys.path.append(str(HEADER))
        from receipt_refinement import refine_receipt

        footer_text = refine_receipt(image, document, metadata, load(links),
                                     load(out / "pp-prediction.json"), table, module)
        save(out / "footer-refinement.json", footer_text)
    save(out / "table.json", table)


def core(image, out):
    sys.path[:0] = [str(PP / "code"), str(REPO)]
    os.environ["PADDLE_PDX_CACHE_HOME"] = os.environ.get("VIETRECEIPT_READER_PADDLE_CACHE", str(BASE / "paddle-models"))
    import torch  # Load Torch DLLs before Paddle on the Windows runtime.
    from ai.document_reader import DocumentReader
    from image_input import prepare_image, transform_polygon
    from pipeline import LayoutPipeline
    from preview_render import render_preview
    from reader_auto_layout import integrate

    receipt_id, run_id = uuid4(), uuid4()
    document, metadata = DocumentReader().process_with_metadata(
        image, content_type=MIME[image.suffix.lower()], receipt_id=receipt_id, ocr_run_id=run_id,
    )
    save(out / "reader-document.json", document)
    save(out / "reader-metadata.json", metadata)
    outcomes = {}
    try:
        engine = LayoutPipeline(external_ocr=True, model_path=PP / "models/PP-DocLayoutV3_safetensors")
        result = integrate(
            image, engine, receipt_id=receipt_id, ocr_run_id=run_id,
            reader=lambda *_args, **_kwargs: document,
        )
        for name, value in result.items():
            save(out / f"pp-{name.replace('_', '-')}.json", value)
        prepared = prepare_image(image)
        matrix = prepared.source["original_to_upright_matrix"]
        regions = [
            {"label": r["label"], "polygon": transform_polygon(r["polygon_original_pixels"], matrix)}
            for r in result["layout"]["pages"][0]["regions"]
        ]
        render_preview(prepared.image, regions).save(out / "pp-preview.jpg", quality=95)
        outcomes["segmentation"] = {"status": "OK", "warnings": result["prediction"]["warnings"]}
    except Exception as exc:
        outcomes["segmentation"] = {"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"}
    if checkpoint_text_mode():
        outcomes['table'] = {'status':'PENDING_CHECKPOINT','note':'Runs after shared checkpoint evidence is ready'}
    else:
        try:
            table_and_footer_text(image, out, document, metadata)
            outcomes["table"] = {"status": "OK"}
        except Exception as exc:
            outcomes["table"] = {"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"}
    save(out / "core-stages.json", outcomes)


def header(image, out, *, engine=None):
    if str(HEADER) not in sys.path:
        sys.path.insert(0, str(HEADER))
    from checkpoint_pipeline import CheckpointHeaderPipeline
    from checkpoint_ocr import CheckpointRecognizer
    from header_second_pass import refine_header

    document = load(out / "reader-document.json")
    metadata = load(out / "reader-metadata.json")
    if engine is None:
        recognizer = CheckpointRecognizer(crop_padding_ratio=0.2 if checkpoint_text_mode() else 0.0)
        engine = CheckpointHeaderPipeline(recognizer=recognizer)
    result = engine.process(
        image, evidence=document, reader_metadata=metadata,
    )
    result["selection"]["adapter_bundle"] = HEADER.name
    links = out / "pp-region-links.json"
    if links.is_file():
        region_links = load(links)
        suggest_retail_header(result["header"], result["evidence"], region_links)
        recover_header(result["header"], result["evidence"], document, region_links,
                       allow_reader=not checkpoint_text_mode())
        if not checkpoint_text_mode():
            refine_header(image, result["header"], document, metadata, region_links)
    for key in ("header", "evidence", "selection", "checkpoint_provenance", "recognizer_comparison"):
        filename = "header.json" if key == "header" else f"header-{key.replace('_', '-')}.json"
        save(out / filename, result[key])
    if checkpoint_text_mode():
        save(out/'checkpoint-document.json',result['evidence'])
        save(out/'text-selection.json',{
            'text_source':'vietocr-checkpoint','scope':['header','table','footer'],
            'ocr_run_id':result['evidence']['ocr_run_id'],'parent_ocr_run_id':document['ocr_run_id'],
            'checkpoint_sha256':result['checkpoint_provenance']['checkpoint_sha256'],
            'preprocessing':result['checkpoint_provenance'].get('preprocessing',{}),
            'paddle_role':'boxes and reference text only','paddle_text_fallback':False,
            'apple_vision_text_replacement':False,'gold_used_for_selection':False,
            'empty_prediction_policy':'omit and record; never insert Paddle text'})


def table(image, out):
    document=load(out/'checkpoint-document.json')
    spec=importlib.util.spec_from_file_location('retail_checkpoint_bundle',RETAIL)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    result=module.extract_retail_table(document,currency='VND')
    result.update(text_source='vietocr-checkpoint',source_ocr_run_id=document['ocr_run_id'],
                  paddle_text_fallback=False)
    save(out/'table-evidence.json',document)
    save(out/'table.json',result)


def suggest_retail_header(header_data, evidence, region_links):
    """Suggest missing merchant fields from a retail shop imprint."""
    from ai.kie.v2.cells import Candidate, select
    from ai.kie.v2.evidence import flatten
    from ai.kie.v2.normalization import folded

    fields = header_data["fields"]
    if all(fields[key]["value_status"] != "UNKNOWN" for key in ("seller_name", "seller_address")):
        return
    header_ids = {
        link["block_id"] for link in region_links["blocks"] if link["status"] == "ASSIGNED"
        and any(match["label"] == "header" for match in link["matches"])
    }
    blocks = [block for block in flatten(evidence) if block.block_id in header_ids]
    # The print sequence ties the unlabelled lines to the merchant. Keep the
    # original values and block IDs and ask for role confirmation.
    for shop, address, phone, title in zip(blocks, blocks[1:], blocks[2:], blocks[3:]):
        if len({block.page for block in (shop, address, phone, title)}) != 1:
            continue
        if not re.match(r"^(?:minimart|supermarket|sieu thi|cua hang|tap hoa)\s+\S", folded(shop.text)):
            continue
        if not re.match(r"^(?:cho|duong|pho|thon|xa|phuong|quan|huyen|\d+[a-z]?\b)\s+", folded(address.text)):
            continue
        if not re.match(r"^(?:tel|dt|dien thoai|phone)\s*:", folded(phone.text)):
            continue
        if not re.match(r"^(?:hoa don ban hang|bien lai ban hang|phieu tinh tien)\b", folded(title.text)):
            continue
        for key, block in (("seller_name", shop), ("seller_address", address)):
            if fields[key]["value_status"] == "UNKNOWN":
                fields[key] = select(key, [Candidate(block.text, (block,), explicit_role=False)])
        return


def footer(image, out):
    if checkpoint_text_mode():
        from checkpoint_footer import build_footer
        document=load(out/'checkpoint-document.json')
        links=load(out/'pp-region-links.json') if (out/'pp-region-links.json').exists() else None
        save(out/'footer.json',build_footer(image,out,document,load(out/'reader-metadata.json'),links))
        save(out/'footer-evidence.json',document)
        return
    sys.path.insert(0, str(FOOTER))
    os.environ["PADDLE_PDX_CACHE_HOME"] = os.environ.get("VIETRECEIPT_FOOTER_PADDLE_CACHE", str(ROOT / "footer-paddle-cache"))
    from paddle_footer import read_footer
    from paddle_runtime import build_engine

    # Align the footer image with the Reader's view, and record its coordinate frame.
    from PIL import Image, ImageOps

    metadata = load(out / "reader-metadata.json")
    angle = metadata["pages"][0]["orientation_clockwise"]
    with Image.open(image) as source:
        upright = ImageOps.exif_transpose(source).convert("RGB")
    if angle:
        upright = upright.rotate(-angle, expand=True)
    display_path = out / "footer-upright.png"
    upright.save(display_path)
    result = read_footer(build_engine(threads=4), display_path)
    prediction = out / "pp-prediction.json"
    rows = load(prediction)["rows"] if prediction.is_file() else ()
    result["payment"] = resolve_payable(result["text"], rows)
    supplement = out / "footer-refinement.json"
    if supplement.is_file():
        apply_footer_display(result, load(supplement))
    result["recognizer"] = "PP-OCRv5_server_det + latin_PP-OCRv5_mobile_rec"
    result["coordinate_system"] = "pixels_on_footer_upright_png"
    result["orientation_clockwise"] = angle
    save(out / "footer.json", result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("core", "header", "table", "footer"))
    parser.add_argument("image", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    {"core": core, "header": header, "table":table, "footer": footer}[args.stage](args.image, args.out)


if __name__ == "__main__":
    main()
