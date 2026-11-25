"""Offline checks for shared text routing; no model download or gold selection."""
import copy
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from checkpoint_footer import build_footer, rotate_point
from footer_amount import read_payable
from run_receipt import reconcile


def document(texts):
    blocks = []
    for i, text in enumerate(texts):
        y = .6 + i*.08
        blocks.append(dict(block_id=f"b{i}",text=text,confidence=.9,
            polygon=[dict(x=x,y=v) for x,v in [(.1,y),(.9,y),(.9,y+.04),(.1,y+.04)]],
            reading_order=i))
    return dict(ocr_run_id="checkpoint-run",receipt_id="receipt",
        pages=[dict(page_index=0,evidence=dict(image=dict(width_px=100,height_px=200),
                                             blocks=blocks,engine=dict(name="checkpoint")))])


class RoutingTests(unittest.TestCase):
    def build(self, texts, angle=0):
        evidence = document(texts)
        links = dict(blocks=[dict(block_id=b["block_id"],status="ASSIGNED",
                      matches=[dict(label="footer")]) for b in evidence["pages"][0]["evidence"]["blocks"]])
        with tempfile.TemporaryDirectory() as folder:
            image=Path(folder)/"source.png"
            Image.new("RGB",(100,200),"white").save(image)
            before=copy.deepcopy(evidence)
            result=build_footer(image,Path(folder),evidence,
                     dict(pages=[dict(orientation_clockwise=angle)]),links)
            self.assertEqual(before,evidence)
            with Image.open(Path(folder)/"footer-upright.png") as preview:
                self.assertEqual(preview.size,(200,100) if angle in (90,270) else (100,200))
            return result

    def test_raw_text_and_source_preserved(self):
        result=self.build(["Tiền thuể GTGT:0","Tổng thanh toán:884.000"])
        self.assertEqual(result["lines"][0]["text"],"Tiền thuể GTGT:0")
        self.assertEqual(result["payment"]["amount_vnd"],884000)
        self.assertEqual(result["source_ocr_run_id"],"checkpoint-run")
        self.assertFalse(result["paddle_text_fallback"])

    def test_rotated_boxes_stay_in_frame(self):
        self.assertEqual(rotate_point(dict(x=.2,y=.3),90),(.7,.2))
        for angle in (90,180,270):
            result=self.build(["Tổng thanh toán:113.000"],angle)
            height,width=result["layout_input_shape"]
            self.assertTrue(all(0<=x<=width and 0<=y<=height
                for line in result["lines"] for x,y in line["poly"]))

    def test_conflicting_totals_remain_ambiguous(self):
        result=self.build(["Tổng thanh toán:113.000","Tổng thanh toán:118.000"])
        self.assertEqual(result["payment"]["status"],"AMBIGUOUS")
        self.assertIsNone(result["payment"]["amount_vnd"])

    def test_malformed_digits_not_guessed(self):
        self.assertEqual(read_payable("Tổng thanh toán:113,0)00")["status"],"UNKNOWN")

    def test_duplicate_label_separator_does_not_change_digits(self):
        result=read_payable("Tổng cộng 113,000\nTổng tiền:: 113,000")
        self.assertEqual(result["status"],"PRESENT")
        self.assertEqual(result["amount_vnd"],113000)

    def test_empty_page_does_not_fallback(self):
        result=self.build([])
        self.assertEqual(result["lines"],[])
        self.assertEqual(result["payment"]["status"],"UNKNOWN")
        self.assertFalse(result["paddle_text_fallback"])

    def test_integration_rejects_text_replacement(self):
        evidence=document(["Tổng thanh toán:113.000"])
        result=dict(reader=evidence,text_source="checkpoint",checkpoint_document=evidence,
                    footer=dict(source_ocr_run_id="checkpoint-run",paddle_text_fallback=False,
                        lines=[dict(source_block_id="b0",text="changed",source_ocr_run_id="checkpoint-run")]))
        with self.assertRaisesRegex(ValueError,"Footer"):
            reconcile(result)


if __name__=="__main__":
    unittest.main()
