"""Build the local project with the installed pinned backend; no downloads."""
from pathlib import Path
import importlib.metadata, os, sys
ROOT=Path(__file__).resolve().parents[1]
if importlib.metadata.version("setuptools")!="82.0.1":
    raise SystemExit("This build recipe requires installed setuptools==82.0.1")
def guard(event,args):
    if event in {"socket.connect","socket.getaddrinfo","subprocess.Popen","os.system"}:
        raise RuntimeError("Local wheel build forbids network and child processes")
sys.addaudithook(guard)
os.chdir(ROOT)
from setuptools.build_meta import build_wheel
print(build_wheel("dist"))
