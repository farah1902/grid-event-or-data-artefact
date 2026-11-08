"""Copy the repository to its Google Drive copy (for Colab runs): new and changed files only, by MD5.

    python tools/sync_drive.py "G:/My Drive/grid-event-or-data-artefact"            # local -> Drive
    python tools/sync_drive.py "G:/My Drive/grid-event-or-data-artefact" --dry-run  # list what would change
    python tools/sync_drive.py "G:/My Drive/grid-event-or-data-artefact" --pull results/benchmark_v1 notebooks/NB4_benchmark.ipynb
        # Drive -> local, for the given paths only (outputs of a Colab run)

Skips .git, _local_archive, figures/ (scratch), caches and checkpoints. Never deletes anything.
"""
import argparse, hashlib, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "_local_archive", "__pycache__", ".ipynb_checkpoints", ".venv", "venv"}
SKIP_TOP = {"figures"}


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def files(base, sub=None):
    start = base / sub if sub else base
    if start.is_file():
        yield start
        return
    for p in start.rglob("*"):
        rel = p.relative_to(base)
        if p.is_file() and not (set(rel.parts) & SKIP_DIRS) and rel.parts[0] not in SKIP_TOP:
            yield p


def copy(src_base, dst_base, paths=None, dry=False):
    n_new = n_chg = n_same = 0
    for p in (f for sub in (paths or [None]) for f in files(src_base, sub)):
        rel = p.relative_to(src_base)
        q = dst_base / rel
        if q.exists() and md5(p) == md5(q):
            n_same += 1
            continue
        tag = "changed" if q.exists() else "new"
        n_chg += tag == "changed"; n_new += tag == "new"
        print(f"{tag:8s} {rel.as_posix()}")
        if not dry:
            q.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, q)
    print(f"{'would copy' if dry else 'copied'}: {n_new} new, {n_chg} changed; {n_same} identical")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("drive")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pull", nargs="+", default=None, help="copy these paths Drive -> local instead")
    a = ap.parse_args()
    drive = Path(a.drive)
    if a.pull:
        copy(drive, ROOT, a.pull, a.dry_run)
    else:
        copy(ROOT, drive, None, a.dry_run)
