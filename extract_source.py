from pathlib import Path
import hashlib, zipfile

archive = Path(__file__).with_name('release_path_v0.3.zip')
expected = 'c8d9119dce5cf84a974946e96d30829b69d50dc62161eddccde4a7e24b8a8409'
actual = hashlib.sha256(archive.read_bytes()).hexdigest()
if actual != expected:
    raise SystemExit(f'archive integrity mismatch: {actual}')
with zipfile.ZipFile(archive) as zf:
    zf.extractall(Path(__file__).resolve().parent)
print('Release Path v0.3 source materialized; SHA-256 verified.')
