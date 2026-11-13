"""Real-host mount allowlist, adapted from U2's working bubblewrap launch.
No Landlock preexec restrictions: the CLI must start its own tool sandbox.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

WORK = '/home/dev/proj'
HOME = '/home/dev'
RUNTIME = '/opt/egmcal-runtime'
MARKER = '.egmcal-sandbox-started'


def runtime_root(cli):
    """Require a lead-supplied, dedicated runtime. Never infer a CLI parent."""
    executable = Path(cli).resolve()
    home = Path.home().resolve()
    matches = [Path(v).resolve() for v in os.environ.get('EGMCAL_RUNTIME_ROOTS', '').split(os.pathsep) if v]
    matches = [p for p in matches if p.is_dir() and executable.is_relative_to(p)
               and p != home and p not in home.parents
               and not any(p.is_relative_to(Path(s)) for s in ('/usr', '/bin', '/lib', '/lib64', '/etc'))]
    if len(matches) != 1:
        raise ValueError('runtime_allowlist: EGMCAL_RUNTIME_ROOTS must name exactly one dedicated folder containing this CLI, never HOME/system roots')
    # Mounting a runtime with links escaping it would expose or break dependencies.
    if any(p.is_symlink() and not p.resolve().is_relative_to(matches[0]) for p in matches[0].rglob('*')):
        raise ValueError('runtime_allowlist: runtime symlink escapes the explicitly supplied folder')
    return matches[0]


def read_roots(cli, work, home):
    return [Path(p).resolve() for p in ('/usr', '/bin', '/lib', '/lib64', '/etc/ssl',
            '/etc/resolv.conf', '/etc/hosts', '/etc/nsswitch.conf') if Path(p).exists()] + [runtime_root(cli), work.resolve(), home.resolve()]


def available():
    if not shutil.which('bwrap'):
        raise ValueError('sandbox_started: bubblewrap is required; no fallback')


def bubblewrap(command, cli, work, home):
    available()
    runtime = runtime_root(cli)
    argv = ['bwrap', '--tmpfs', '/', '--ro-bind', '/usr', '/usr', '--ro-bind', '/bin', '/bin',
            '--ro-bind', '/lib', '/lib', '--ro-bind', '/lib64', '/lib64', '--dir', '/etc']
    for p in ('/etc/ssl', '/etc/resolv.conf', '/etc/hosts', '/etc/nsswitch.conf'):
        if Path(p).exists():
            # Bind only the resolved file, never the parent of a resolver symlink.
            argv += ['--ro-bind', str(Path(p).resolve()), p]
    argv += ['--dev', '/dev', '--proc', '/proc', '--tmpfs', '/tmp', '--dir', '/home',
             '--bind', str(home), HOME, '--bind', str(work), WORK,
             '--bind', str(work / 'review_out'), WORK + '/review_out',
             '--dir', '/opt', '--ro-bind', str(runtime), RUNTIME,
             '--chdir', WORK, '--die-with-parent', '--unshare-ipc', '--unshare-pid']
    inner = [RUNTIME + '/' + Path(cli).resolve().relative_to(runtime).as_posix()] + command[1:]
    wrapper = ('from pathlib import Path; import os,sys; '
               'Path("/home/dev/' + MARKER + '").write_text("bwrap-v1"); '
               'os.execv(sys.argv[1],sys.argv[1:])')
    return argv + ['/usr/bin/python3', '-c', wrapper] + inner


def version_output(cli):
    """Even --version gets a fresh namespace, no credential or operator configuration."""
    with tempfile.TemporaryDirectory(prefix='egmcal-version-') as td:
        root = Path(td)
        work, home = root / 'workspace', root / 'home'
        (work / 'review_out').mkdir(parents=True)
        home.mkdir()
        argv = bubblewrap([str(cli), '--version'], cli, work, home)
        return subprocess.run(argv, capture_output=True, text=True, timeout=15,
                              env={'HOME': HOME, 'PATH': RUNTIME + ':/usr/bin:/bin',
                                   'DISABLE_AUTOUPDATER': '1'}, cwd=work)
