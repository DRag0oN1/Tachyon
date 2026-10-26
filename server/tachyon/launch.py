"""Filesystem-only owner launch handoff. Never exposed by an HTTP endpoint."""
import ipaddress
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit

from .errors import TachyonError


def descriptor_path(settings, port=None):
    port = port or urlsplit(settings.ui_origin).port or 80
    # One private, project-local rendezvous per port, independent of the
    # selected CAD data profile. A fresh terminal can recover the running app.
    return settings.root / '.local' / 'runtime' / f'owner-launch-{port}.json'


def write_owner_launch(settings, token):
    path = descriptor_path(settings)
    if path.parent.parent.is_symlink() or path.parent.is_symlink() or path.is_symlink():
        raise TachyonError('UNSAFE_LAUNCH_PATH', 'The private runtime path must not be a symlink')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            os.chmod(handle.name, 0o600)
            json.dump({'schemaVersion': 1, 'origin': settings.ui_origin.rstrip('/'), 'session': token}, handle)
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists(): temporary.unlink()
    return path


def read_owner_launch(settings, port=None):
    path = descriptor_path(settings, port)
    try:
        if path.is_symlink() or path.parent.is_symlink() or path.parent.parent.is_symlink() or path.stat().st_mode & 0o077 or path.stat().st_uid != os.getuid():
            raise ValueError()
        value = json.loads(path.read_text())
        origin, token = value['origin'], value['session']
        if not isinstance(origin,str): raise ValueError()
        parsed = urlsplit(origin)
        local = parsed.hostname == 'localhost' or ipaddress.ip_address(parsed.hostname).is_loopback
        if (value['schemaVersion'] != 1 or not local or parsed.scheme not in ('http', 'https')
                or parsed.path not in ('', '/') or parsed.query or parsed.fragment or parsed.username
                or (parsed.port or 80) != (port or urlsplit(settings.ui_origin).port or 80)
                or not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,256}', token)):
            raise ValueError()
        return origin.rstrip('/'), token
    except (OSError, ValueError, KeyError, TypeError):
        raise TachyonError('LAUNCH_UNAVAILABLE', 'Start Tachyon in this project, then run launch with its port. The owner handoff must be private and local.') from None


def remove_owner_launch(settings, token):
    path = descriptor_path(settings)
    try:
        if not path.is_symlink() and json.loads(path.read_text()).get('session') == token:
            path.unlink()
    except (OSError, ValueError):
        pass


def open_owner_launch(settings, *, port=None, show_url=False):
    import httpx
    import webbrowser
    origin, token = read_owner_launch(settings, port)
    try:
        response = httpx.get(origin + '/api/workspace', headers={'X-Tachyon-Session': token, 'Origin': origin},
                             timeout=5, follow_redirects=False, trust_env=False)
        if response.status_code != 200: raise ValueError()
    except (httpx.HTTPError, ValueError):
        raise TachyonError('LAUNCH_EXPIRED', 'The saved launch is no longer authorized. Start the current Tachyon server and retry launch.') from None
    url = origin + '/#session=' + token
    if show_url:
        return url
    if not webbrowser.open(url):
        raise TachyonError('BROWSER_UNAVAILABLE', 'The browser could not open. Use launch --show-url privately and paste that URL into the connection screen.')
    return None
