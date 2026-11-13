"""Linux Landlock filesystem confinement, inherited by all descendant processes.

Host runtime/auth/state necessarily live outside review_out. No other study,
packet, key, parent HOME or transcript directory is allowed. Network for model
transport remains host-owned; agent tools are constrained by each CLI as well.
"""
import ctypes
import errno
import os
import platform
from pathlib import Path

# Linux UAPI syscall numbers on x86_64/aarch64; unsupported systems fail closed.
CREATE, ADD, RESTRICT = 444, 445, 446
EXECUTE, WRITE_FILE, READ_FILE, READ_DIR = 1, 2, 4, 8
FS_V1 = (1 << 13) - 1
REFER, TRUNCATE = 1 << 13, 1 << 14


class Ruleset(ctypes.Structure):
    _fields_ = [('handled_access_fs', ctypes.c_uint64)]


class PathBeneath(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('allowed_access', ctypes.c_uint64), ('parent_fd', ctypes.c_int32)]


def abi():
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'aarch64'):
        raise ValueError('Landlock requires supported Linux architecture')
    libc = ctypes.CDLL(None, use_errno=True)
    value = libc.syscall(CREATE, 0, 0, 1)
    if value < 3:
        raise ValueError('Landlock ABI >= 3 required; no isolation fallback')
    return value


def restrict(read_paths, write_paths):
    version = abi()
    libc = ctypes.CDLL(None, use_errno=True)
    # ABI 3 handles truncation; later ABIs keep this compatible subset.
    handled = FS_V1 | REFER | TRUNCATE
    attr = Ruleset(handled)
    fd = libc.syscall(CREATE, ctypes.byref(attr), ctypes.sizeof(attr), 0)
    if fd < 0:
        raise OSError(ctypes.get_errno(), 'Landlock ruleset')
    try:
        for paths, rights in ((read_paths, EXECUTE | READ_FILE | READ_DIR),
                               (write_paths, handled)):
            for value in paths:
                path = Path(value).resolve()
                access = rights if path.is_dir() else rights & (EXECUTE | READ_FILE | WRITE_FILE | TRUNCATE)
                pfd = os.open(str(path), os.O_PATH | os.O_CLOEXEC)
                try:
                    rule = PathBeneath(access, pfd)
                    if libc.syscall(ADD, fd, 1, ctypes.byref(rule), 0) < 0:
                        raise OSError(ctypes.get_errno(), 'Landlock path rule')
                finally:
                    os.close(pfd)
        if libc.prctl(38, 1, 0, 0, 0) != 0:  # PR_SET_NO_NEW_PRIVS
            raise OSError(ctypes.get_errno(), 'no_new_privs')
        if libc.syscall(RESTRICT, fd, 0) < 0:
            raise OSError(ctypes.get_errno(), 'Landlock enforce')
    finally:
        os.close(fd)
    return version


def runtime_paths(cli):
    # Never grant an arbitrary CLI parent directory (it may contain other studies).
    paths = ['/usr', '/bin', '/lib', '/lib64', '/etc', '/dev/null', '/dev/urandom',
             '/dev/random', '/proc/self', '/proc/cpuinfo', '/proc/meminfo']
    paths.append(str(Path(cli).resolve()))
    return [p for p in paths if Path(p).exists()]
