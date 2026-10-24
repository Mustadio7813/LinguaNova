"""Make an explicit manifest for a tested local Windows OCR/worker folder."""
import argparse,json,hashlib
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('folder');p.add_argument('--type',choices=['tesseract','inference'],required=True)
    p.add_argument('--executable',required=True);p.add_argument('--version',required=True)
    p.add_argument('--license',action='append',required=True)
    args=p.parse_args();root=Path(args.folder).resolve()
    def sha(path):
        h=hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
        return h.hexdigest()
    files=[{'path':f.relative_to(root).as_posix(),'size':f.stat().st_size,'sha256':sha(f)} for f in sorted(root.rglob('*')) if f.is_file() and f.name!='component_manifest.json']
    manifest={'schema_version':1,'type':args.type,'version':args.version,'executable':args.executable,
              'protocol_version':1,'files':files,'license_notices':args.license,
              'validation':'Manifest created from local bytes; execute the acceptance test on the target OS separately'}
    if args.executable not in {x['path'] for x in files}:raise ValueError('Executable not found in component')
    for notice in args.license:
        if notice not in {x['path'] for x in files}:raise ValueError('License notice not found')
    (root/'component_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':main()
