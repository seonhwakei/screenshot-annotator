"""Usage: upload_batch.py <currentPageId e.g. 2929:3> <png1> <png2> ... -- <uuid1> <uuid2> ...
POSTs each PNG to its single-use upload URL (uuids come from the upload_assets MCP result: .../upload/<uuid>/submit).
Prints success/hash per file. Layer name = filename."""
import sys, subprocess, urllib.parse
a=sys.argv[1:]; page=urllib.parse.quote(a[0]); i=a.index('--'); files=a[1:i]; ids=a[i+1:]
assert len(files)==len(ids),"files/uuids count mismatch"
for f,u in zip(files,ids):
    r=subprocess.run(['curl','-s','-X','POST','-F',f'file=@{f};type=image/png',f'https://mcp.figma.com/mcp/upload/{u}/submit?scaleMode=FILL&currentPageId={page}'],capture_output=True,text=True)
    print(f,r.stdout[:90])
