"""Verify the exact shared weights, including successful Git LFS checkout."""
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def verify():
    manifest=json.loads((ROOT/"MODEL-MANIFEST.json").read_text(encoding="utf-8"))
    for relative,expected in manifest.items():
        path=ROOT/relative
        if not path.is_file() or path.stat().st_size!=expected["bytes"]:
            raise SystemExit(f"Missing/incomplete model: {relative}. Run git lfs pull.")
        digest=hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b""):digest.update(chunk)
        if digest.hexdigest()!=expected["sha256"]:
            raise SystemExit(f"Model checksum mismatch: {relative}")
        print("OK",relative,flush=True)
    return len(manifest)

if __name__=="__main__":
    print("Verified model files:",verify())
