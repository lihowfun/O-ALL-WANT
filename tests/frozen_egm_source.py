"""Restore the source registered by historical EGM contracts, not today's V2.

Only offline historical tests use this archive. Current installer behavior is
tested independently by test_install and test_egm_integration. No contract hash,
tree digest, scorer, or provenance guard is mocked to accept a newer source.
"""
from contextlib import contextmanager
import hashlib
from pathlib import Path, PurePosixPath
import tempfile
import zipfile

ARCHIVE = Path(__file__).parent / "fixtures/egm-registered-oaw-source.zip"
ARCHIVE_SHA256 = "744f2137a14cb9cf1e654c0d583e89ac55cae193c1de4be2eb5e76a4b53cd67c"
TREE_SHA256 = "a4ee3c46ac5fd15b45cd7218959bd4ea6d420da7c48b7493e3446a936705f0c7"


def enter_context(case, manager):
    """TestCase.enterContext equivalent that also works on Python 3.10."""
    result = manager.__enter__()
    case.addCleanup(manager.__exit__, None, None, None)
    return result


@contextmanager
def registered_source():
    if hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("Frozen EGM test source archive changed")
    with tempfile.TemporaryDirectory(prefix="egm-frozen-source-") as temporary:
        root = Path(temporary)
        with zipfile.ZipFile(ARCHIVE) as archive:
            for info in archive.infolist():
                name = PurePosixPath(info.filename)
                if name.is_absolute() or ".." in name.parts or "\\" in info.filename or ":" in info.filename:
                    raise ValueError("Unsafe frozen source path")
                path = root.joinpath(*name.parts)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(info))
        yield root
