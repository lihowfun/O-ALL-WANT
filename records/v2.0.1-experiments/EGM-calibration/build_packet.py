#!/usr/bin/env python3
"""Create/verify a closed packet manifest. No symlinks, VCS metadata or review outputs."""
import argparse
import os
from pathlib import Path
from cal_common import canonical, load, require, save, sha

FORBIDDEN = {'.git', 'review_out'}


def inventory(root):
    root = Path(root)
    require(root.is_dir() and not root.is_symlink(), 'packet must be a real directory')
    result = []
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs.sort()
        for name in sorted(dirs + names):
            path = Path(base) / name
            require(name not in FORBIDDEN, 'forbidden packet entry: ' + name)
            require(not path.is_symlink(), 'packet symlink forbidden')
            require(path.is_dir() or path.is_file(), 'special packet entry forbidden')
        for name in sorted(names):
            path = Path(base) / name
            rel = path.relative_to(root).as_posix()
            data = path.read_bytes()
            result.append({'path': rel, 'size': len(data), 'sha256': sha(data)})
    result.sort(key=lambda x: x['path'])
    require(result, 'empty packet')
    return {'schema_version': 1, 'tree_algorithm': 'sha256(canonical JSON files array)',
            'files': result, 'tree_sha256': sha(canonical(result))}


def verify(root, manifest):
    actual = inventory(root)
    require(actual == manifest, 'packet differs from manifest (extra, missing or changed file)')
    return actual['tree_sha256']


def copy_packet(root, target, manifest):
    import shutil
    verify(root, manifest)
    target = Path(target)
    require(not target.exists(), 'workspace already exists')
    shutil.copytree(root, target, symlinks=False)
    verify(target, manifest)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('packet', type=Path)
    p.add_argument('--manifest', type=Path, default=Path(__file__).with_name('packet_manifest.json'))
    p.add_argument('--create', action='store_true', help='one-time creation; never overwrites a manifest')
    a = p.parse_args(argv)
    if a.create:
        require(not a.manifest.exists(), 'manifest already frozen; use verification')
        save(a.manifest, inventory(a.packet))
    digest = verify(a.packet, load(a.manifest))
    print(digest)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError):
        raise SystemExit('packet verification failed')
