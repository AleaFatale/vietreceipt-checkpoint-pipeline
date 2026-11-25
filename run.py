"""One-image entry point for the shared VietOCR checkpoint pipeline."""
import argparse,ctypes,datetime,os
from pathlib import Path
import subprocess,sys
from verify_models import ROOT,verify

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image",type=Path,default=ROOT/"examples/00001.png")
    parser.add_argument("--out",type=Path)
    parser.add_argument("--open",action="store_true",help="Open local HTML result")
    args=parser.parse_args()
    image=args.image.resolve()
    if not image.is_file():parser.error("Input image does not exist")
    out=(args.out or ROOT/"runs"/datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")).resolve()
    if out.exists():parser.error("Use a new output directory")
    verify()
    terminal=ROOT/"output/vietreceipt-terminal"
    cache=ROOT/"models/paddle-reader"
    if os.name=="nt":
        buffer=ctypes.create_unicode_buffer(32768)
        if not ctypes.windll.kernel32.GetShortPathNameW(str(cache),buffer,len(buffer)):
            raise SystemExit("Cannot resolve local Reader model cache")
        cache=Path(buffer.value)
    env=dict(os.environ,PYTHONUTF8="1",PYTHONIOENCODING="utf-8",
        VIETRECEIPT_READER_PADDLE_CACHE=str(cache),
        PYTHONPATH=str(ROOT)+os.pathsep+os.environ.get("PYTHONPATH",""))
    if os.name=="nt":
        env["PADDLE_PDX_LOCAL_FONT_FILE_PATH"]=str(Path(os.environ["WINDIR"])/"Fonts/arial.ttf")
    code=subprocess.call([sys.executable,"-X","utf8","-B",str(terminal/"run_receipt.py"),
        "--image",str(image),"--out",str(out),"--core-python",sys.executable,
        "--text-source","checkpoint"],env=env)
    if (out/"summary.json").is_file():
        subprocess.run([sys.executable,"-X","utf8",str(terminal/"windows_review.py"),str(out)],env=env,check=True)
        if args.open:
            import webbrowser
            webbrowser.open((out/"index.html").as_uri())
    return code

if __name__=="__main__":raise SystemExit(main())
