# Source provenance

This is a new independent Git history, packaged from
`NguyenDong-23/vietreceipt-ocr-pipeline` commit
`f36913d1fa3a9c06d1f693f018d33acbcd33ab26` plus shared-checkpoint integration
changes made on 2026-11-25. The source snapshot traces back to
`vietreceipt-team/vietreceipt`, branch `feat/table-extraction`, commit
`ad442a809e1b276417e8b7b24529f480059763eb`.

The integration under `output/vietreceipt-terminal/` combines the group's
Reader, PP-DocLayoutV3, shared VietOCR checkpoint, Header KIE, Retail Table,
and checkpoint-based Footer components. Reader supplies boxes and reference
text; final text for all three extraction sections uses VietOCR. The original
Paddle Footer source is retained as upstream component code.

Only one synthetic sample and its gold are included in `examples/`.
The original 20-image test set and local machine reports are not republished.
Its development scores are described with their limitations in README.md.

Weights are byte-identical to the source snapshot. MODEL-MANIFEST.json records
their hashes. PP-DocLayoutV3 and Reader model cards are retained beside weights;
VietOCR source provenance is in the bundled VIETOCR-UPSTREAM-METADATA.txt.

The upstream project did not include a root license file at the snapshot commit. Public visibility does not grant additional reuse rights. Check the respective upstream/model terms before redistribution or reuse.
