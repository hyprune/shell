"""Machine data sources (RFC-0013 draft): sources.json edits and the source helper's local
control socket, for Director > Objects > Placed > Data source.

The source helper listens on `sources.sock` beside core's control socket: newline-delimited
JSON, one request and one response line of at most 64 KiB (ops status, test, secrets, restart,
restart-all, reload). This module never runs a source command itself: Test goes through the
helper's `test` op, which runs it with the helper's rules and publishes nothing.

sources.json is the helper's status.config, else $XDG_CONFIG_HOME/hyprune/sources.json. A save
updates or appends the entry whose id is the instance id (a seed, for a newly placed machine's
demo source, only appends one that is missing) and keeps every other entry, key and
their order; it is written as json.dumps(obj, indent=2) + newline to a temporary file in the
same directory, fsynced and renamed over the file, then the helper is asked to reload.

Every QML request answers exactly one {"type": "sources", "op": ...} event; a missing or
broken helper becomes an error state in that event, never an exception in the bridge.

Director > Objects > Data sources (data sources phase 2) edits whole entries (command and
HTTP sources with their map), tests a definition as written (the helper's test op answers
the raw response and the mapped values) and stores secrets by name: in the secrets file
(the helper's, mode 0600, a JSON object of names to values) or the desktop keyring
(secret-tool). A secret's value goes from the page to the store and nowhere else: never
into sources.json, an event or a log.
"""
import asyncio
import contextlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import struct
import tempfile

SLUG = re.compile(r'[a-z][a-z0-9-]*')
LINE_LIMIT = 64 * 1024
# The helper's limits when it is not running (status.limits replaces them).
DEFAULT_LIMITS = {'command': {'intervalS': [5, 86400], 'devIntervalS': 1, 'timeoutS': [1, 60]}}
MAX_ARGS = 64
MAX_ARG = 4096
BROWSE_LIMIT = 500
# Seconds to wait for each helper op. test and restart run one command (timeoutS ≤ 60).
TIMEOUTS = {'status': 2, 'reload': 3, 'test': 70, 'restart': 70, 'restart-all': 30, 'secrets': 8}
# QML request type -> op in the answering event.
OPS = {'sources.status': 'status', 'sources.get': 'get', 'sources.save': 'save', 'sources.seed': 'seed', 'sources.remove': 'remove',
       'sources.test': 'test', 'sources.restart': 'restart', 'sources.restartAll': 'restartAll',
       'sources.browse': 'browse', 'sources.list': 'list', 'sources.put': 'put', 'sources.testSource': 'testSource',
       'sources.secrets': 'secrets', 'sources.secretSet': 'secretSet'}
KINDS = ('command', 'http')
METHODS = ('GET', 'POST', 'PUT', 'PATCH')
OUTPUTS = ('json', 'number', 'text', 'lines')
SECRET_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}')
SECRET_VALUE_MAX = 4096


class HelperUnavailable(Exception):
    """No helper listens on the control socket (absent or refused)."""


class HelperError(Exception):
    """The helper refused (ok false), timed out, or broke the line protocol."""


class ConfigError(Exception):
    """sources.json can't be read or written, or the request does not fit it."""


def control_path(core_socket, override=None):
    """The helper's control socket: an explicit path, else sources.sock beside core's socket."""
    if override:
        return str(override)
    return str(Path(core_socket).parent / 'sources.sock')


def default_config(env=None):
    """$XDG_CONFIG_HOME/hyprune/sources.json (~/.config when unset or relative)."""
    env = os.environ if env is None else env
    base = env.get('XDG_CONFIG_HOME') or ''
    root = Path(base) if base and Path(base).is_absolute() else Path(env.get('HOME') or Path.home()) / '.config'
    return str(root / 'hyprune' / 'sources.json')


async def request(path, message, timeout):
    """One request line to the helper and its answer (a dict with ok true)."""
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        raise HelperUnavailable('The source helper is not running.') from None
    except OSError as error:
        raise HelperError('Control socket: ' + (error.strerror or str(error))) from None
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
        raise HelperError('The control socket is not a socket owned by this user.')
    data = (json.dumps(message, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode()
    if len(data) > LINE_LIMIT:
        raise HelperError('Request is larger than 64 KiB.')
    writer = None
    try:
        async with asyncio.timeout(timeout):
            reader, writer = await asyncio.open_unix_connection(path, limit=LINE_LIMIT + 1)
            sock = writer.get_extra_info('socket')
            _, uid, _ = struct.unpack('3i', sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            if uid != os.getuid():
                raise HelperError('The control socket belongs to another user.')
            writer.write(data)
            await writer.drain()
            line = await reader.readline()
    except (ConnectionRefusedError, FileNotFoundError):
        raise HelperUnavailable('The source helper is not running.') from None
    except TimeoutError:
        raise HelperError('The source helper did not answer in %g s.' % timeout) from None
    except ValueError:  # asyncio's line limit
        raise HelperError('The source helper answered more than 64 KiB.') from None
    except OSError as error:
        raise HelperError('Control socket: ' + (error.strerror or str(error))) from None
    finally:
        if writer is not None:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
    if not line.endswith(b'\n'):
        raise HelperError('The source helper closed the connection without an answer.')
    try:
        reply = json.loads(line)
    except ValueError:
        raise HelperError('The source helper answered something that is not JSON.') from None
    if not isinstance(reply, dict):
        raise HelperError('The source helper answered something that is not an object.')
    if reply.get('ok') is not True:
        error = reply.get('error')
        raise HelperError(error[:512] if isinstance(error, str) and error else 'The source helper refused the request.')
    return reply


# ---- sources.json ----

def read_config(path):
    """The parsed file (an object with a sources list), or None when it does not exist."""
    try:
        text = Path(path).read_text(encoding='utf-8')
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError) as error:
        raise ConfigError('%s: %s' % (path, getattr(error, 'strerror', None) or error)) from None
    try:
        config = json.loads(text)
    except ValueError as error:
        raise ConfigError('%s is not valid JSON (%s); fix it by hand first.' % (path, error)) from None
    if not isinstance(config, dict) or not isinstance(config.get('sources', []), list):
        raise ConfigError('%s is not an object with a sources list; fix it by hand first.' % path)
    return config


def find_entry(config, source_id):
    for entry in (config or {}).get('sources', []):
        if isinstance(entry, dict) and entry.get('id') == source_id:
            return entry
    return None


def interval_bounds(limits=None, dev=False):
    """[min, max] seconds for a command source's interval."""
    command = ((limits or {}).get('command') or {}) if isinstance(limits, dict) else {}
    lo, hi = command.get('intervalS') or DEFAULT_LIMITS['command']['intervalS']
    if dev:
        lo = min(lo, command.get('devIntervalS', DEFAULT_LIMITS['command']['devIntervalS']))
    return [lo, hi]


def check_id(source_id):
    if not isinstance(source_id, str) or not SLUG.fullmatch(source_id) or len(source_id) > 128:
        raise ConfigError('A sources.json id is a lower-case slug ([a-z][a-z0-9-]*); bind this machine in machines.json instead.')


def check_argv(argv):
    if not isinstance(argv, list) or not argv or not all(isinstance(a, str) and a for a in argv):
        raise ConfigError('Choose a command first.')
    if len(argv) > MAX_ARGS or any(len(a) > MAX_ARG or '\0' in a for a in argv):
        raise ConfigError('At most %d arguments of %d characters each.' % (MAX_ARGS - 1, MAX_ARG))


def check_interval(interval, bounds):
    if isinstance(interval, bool) or not isinstance(interval, (int, float)) or interval != interval:
        raise ConfigError('The interval is a number of seconds.')
    if not bounds[0] <= interval <= bounds[1]:
        raise ConfigError('The interval is %g–%g s.' % tuple(bounds))
    return int(interval) if float(interval).is_integer() else interval


def target(path):
    """Write through a symlinked sources.json (kept as a link), else the path itself."""
    path = Path(path)
    return Path(os.path.realpath(path)) if path.is_symlink() else path


def write_atomic(path, config):
    """json.dumps(config, indent=2) + newline into a temporary file beside path, fsync, rename.
    A new file is 0600 (an existing one keeps its mode); the directory is created if needed."""
    path = target(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except FileNotFoundError:
        mode = 0o600
    text = json.dumps(config, indent=2) + '\n'
    fd, temp = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            os.fchmod(handle.fileno(), mode)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temp)
        raise
    with contextlib.suppress(OSError):
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)


def save_entry(path, source_id, argv, interval, limits=None):
    """Update or append the command entry with this id; returns the saved entry."""
    check_id(source_id)
    check_argv(argv)
    config = read_config(path)
    if config is None:
        config = {'sources': []}
    config.setdefault('sources', [])
    interval = check_interval(interval, interval_bounds(limits, config.get('devFastIntervals') is True))
    entry = find_entry(config, source_id)
    if entry is None:
        entry = {'id': source_id, 'kind': 'command', 'argv': list(argv), 'intervalS': interval}
        config['sources'].append(entry)
    else:
        if entry.get('kind', 'command') != 'command':
            raise ConfigError('Source %s is a %s source; edit it in sources.json.' % (source_id, entry.get('kind')))
        entry.update({'kind': 'command', 'argv': list(argv), 'intervalS': interval})
    try:
        write_atomic(path, config)
    except OSError as error:
        raise ConfigError('Could not write %s: %s' % (path, error.strerror or error)) from None
    return entry


def seed_entry(path, source_id, argv, interval, limits=None):
    """Add a command entry with this id only when there is none (a newly placed machine's
    demo source); an existing entry, whatever its kind, is never touched. Returns the added
    entry, or None when one existed (the file is then untouched)."""
    check_id(source_id)
    check_argv(argv)
    if find_entry(read_config(path), source_id) is not None:
        return None
    return save_entry(path, source_id, argv, interval, limits)


def remove_entry(path, source_id):
    """Delete the entry with this id; False when there was none (the file is then untouched)."""
    check_id(source_id)
    config = read_config(path)
    entry = find_entry(config, source_id)
    if entry is None:
        return False
    config['sources'] = [e for e in config['sources'] if e is not entry]
    try:
        write_atomic(path, config)
    except OSError as error:
        raise ConfigError('Could not write %s: %s' % (path, error.strerror or error)) from None
    return True


def check_source(entry):
    """The shape of an entry the Data sources page writes (the helper checks the rest when it
    reloads and in a test). Raises ConfigError with a sentence for the page."""
    if not isinstance(entry, dict):
        raise ConfigError('A source is an object.')
    check_id(entry.get('id'))
    kind = entry.get('kind') or 'command'  # a None (removed) key is its default
    if kind not in KINDS:
        raise ConfigError('The page edits command and HTTP sources.')
    if kind == 'command':
        check_argv(entry.get('argv'))
    else:
        url = entry.get('url')
        if not isinstance(url, str) or not re.match(r'https?://[^/\s]+', url) or len(url) > 2048:
            raise ConfigError('The URL starts with https:// (or http:// for this machine or a local network).')
        if (entry.get('method') or 'GET') not in METHODS:
            raise ConfigError('The method is GET, POST, PUT or PATCH.')
        if (entry.get('method') or 'GET') == 'GET' and entry.get('body') is not None:
            raise ConfigError('A body needs POST, PUT or PATCH.')
        headers = entry.get('headers') or {}
        if not isinstance(headers, dict) or len(headers) > 32:
            raise ConfigError('Headers are names with a text value or a secret.')
        for name, value in headers.items():
            if not re.fullmatch(r'[A-Za-z0-9-]{1,64}', name):
                raise ConfigError('Header %r is not a header name.' % name[:40])
            if isinstance(value, dict):
                if not SECRET_NAME.fullmatch(str(value.get('secret', ''))) or set(value) - {'secret', 'prefix'}:
                    raise ConfigError('Header %s names a secret by letters, digits and ._- (at most 64).' % name)
            elif not isinstance(value, str) or len(value) > 4096:
                raise ConfigError('Header %s is text (at most 4096 characters) or a secret.' % name)
    if (entry.get('output') or 'json') not in OUTPUTS:
        raise ConfigError('The output is json, number, text or lines.')
    for key in ('intervalS', 'timeoutS'):
        value = entry.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not value > 0):
            raise ConfigError('%s is a number of seconds.' % ('The interval' if key == 'intervalS' else 'The timeout'))
    if entry.get('map') is not None and not isinstance(entry['map'], dict):
        raise ConfigError('The map is an object.')
    if len(json.dumps(entry)) > 48 * 1024:
        raise ConfigError('The source is over 48 KiB.')


def put_entry(path, entry, previous=None):
    """Write an edited entry: its keys replace the entry's (a None value removes the key), any
    key it doesn't name stays (fields, ttlMs, env, cwd ...); previous renames an entry (its id
    was edited). Returns it."""
    check_source(entry)
    config = read_config(path)
    if config is None:
        config = {'sources': []}
    config.setdefault('sources', [])
    old = find_entry(config, previous or entry['id'])
    if previous and previous != entry['id'] and find_entry(config, entry['id']) is not None:
        raise ConfigError('Another source is called %s.' % entry['id'])
    if old is None:
        old = {'id': entry['id']}
        config['sources'].append(old)
    old['id'] = entry['id']
    for key, value in entry.items():
        if value is None:
            old.pop(key, None)
        else:
            old[key] = value
    try:
        write_atomic(path, config)
    except OSError as error:
        raise ConfigError('Could not write %s: %s' % (path, error.strerror or error)) from None
    return old


def default_secrets_path(env=None):
    env = os.environ if env is None else env
    base = env.get('XDG_CONFIG_HOME') or os.path.join(os.path.expanduser('~'), '.config')
    return str(Path(base) / 'hyprune' / 'secrets.json')


def set_secret_file(path, name, value):
    """Store a secret in the secrets file: mode 0600, created if needed; a file with any other
    mode or owner is refused, never loosened or rewritten. A None value removes the name."""
    if not SECRET_NAME.fullmatch(str(name)):
        raise ConfigError('A secret name is letters, digits and ._- (at most 64).')
    if value is not None and (not isinstance(value, str) or not value or len(value) > SECRET_VALUE_MAX or '\0' in value):
        raise ConfigError('A secret is text (at most %d characters).' % SECRET_VALUE_MAX)
    path = Path(path)
    data = {}
    try:
        st = os.stat(path, follow_symlinks=False)
    except FileNotFoundError:
        st = None
    if st is not None:
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
            raise ConfigError('%s must be your own file with mode 0600 (chmod 600 it first).' % path)
        try:
            data = json.loads(path.read_text(encoding='utf-8') or '{}')
        except (OSError, ValueError) as error:
            raise ConfigError('%s is not a JSON object of secrets (%s).' % (path, error)) from None
        if not isinstance(data, dict):
            raise ConfigError('%s is not a JSON object of secrets.' % path)
    if value is None:
        data.pop(name, None)
    else:
        data[name] = value
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix='.secrets.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(json.dumps(data, indent=2) + '\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temp)
        raise


def set_secret_keyring(name, value):
    """Store a secret in the desktop keyring (secret-tool store, the value on stdin)."""
    import shutil
    import subprocess
    if not SECRET_NAME.fullmatch(str(name)):
        raise ConfigError('A secret name is letters, digits and ._- (at most 64).')
    if not isinstance(value, str) or not value or len(value) > SECRET_VALUE_MAX:
        raise ConfigError('A secret is text (at most %d characters).' % SECRET_VALUE_MAX)
    tool = shutil.which('secret-tool')
    if not tool:
        raise ConfigError('The keyring needs secret-tool (libsecret); store it in the secrets file instead.')
    try:
        done = subprocess.run([tool, 'store', '--label', 'Hyprune: ' + name, 'application', 'hyprune', 'secret', name],
                              input=value.encode(), capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ConfigError('The keyring did not answer (%s).' % type(error).__name__) from None
    if done.returncode != 0:
        raise ConfigError('The keyring refused: %s' % done.stderr.decode('utf-8', 'replace').strip()[:200])


def browse(path=None, hidden=False, limit=BROWSE_LIMIT):
    """A directory listing for the in-shell command chooser: folders first, then files by name;
    files the user may execute are marked. A file path lists its folder."""
    base = Path(os.path.expanduser(path)) if path else Path.home()
    if not base.is_absolute():
        raise ConfigError('Choose an absolute path.')
    base = Path(os.path.normpath(base))
    selected = None
    if base.exists() and not base.is_dir():
        selected, base = base.name, base.parent
    entries = []
    try:
        with os.scandir(base) as scan:
            for item in scan:
                if not hidden and item.name.startswith('.'):
                    continue
                try:
                    folder = item.is_dir()
                except OSError:
                    folder = False
                entries.append({'name': item.name, 'dir': folder,
                                'executable': not folder and os.access(item.path, os.X_OK)})
    except OSError as error:
        raise ConfigError('%s: %s' % (base, error.strerror or error)) from None
    entries.sort(key=lambda e: (not e['dir'], e['name'].casefold(), e['name']))
    return {'path': str(base), 'parent': str(base.parent) if base.parent != base else None,
            'entries': entries[:limit], 'truncated': len(entries) > limit, 'selected': selected}


class Sources:
    """The bridge side of the Data source panel: one answer event per QML request."""

    def __init__(self, control, config_default, timeouts=None):
        self.control = control
        self.config_default = config_default
        self.timeouts = {**TIMEOUTS, **(timeouts or {})}
        self.config = None          # the helper's status.config when it last answered
        self.limits = None          # the helper's status.limits
        self.lock = asyncio.Lock()  # one sources.json write at a time

    async def helper(self, op, **fields):
        reply = await request(self.control, {'op': op, **fields}, self.timeouts[op])
        if op == 'status':
            config = reply.get('config')
            self.config = config if isinstance(config, str) and Path(config).is_absolute() else None
            self.limits = reply.get('limits') if isinstance(reply.get('limits'), dict) else None
        return reply

    async def config_path(self):
        """The helper's config file, else the default path."""
        with contextlib.suppress(HelperUnavailable, HelperError):
            await self.helper('status')
        return self.config or self.config_default

    async def reload(self):
        try:
            await self.helper('reload')
            return {'ok': True}
        except HelperUnavailable as error:
            return {'ok': False, 'helper': 'missing', 'error': str(error)}
        except HelperError as error:
            return {'ok': False, 'helper': 'error', 'error': str(error)}

    async def handle(self, cmd):
        kind = cmd.get('type') if isinstance(cmd, dict) else None
        event = {'type': 'sources', 'op': OPS.get(kind, 'unknown')}
        if isinstance(cmd, dict) and isinstance(cmd.get('seq'), int) and not isinstance(cmd.get('seq'), bool):
            event['seq'] = cmd['seq']
        if isinstance(cmd, dict) and isinstance(cmd.get('id'), str):
            event['id'] = cmd['id']
        try:
            event.update(await self.answer(kind, cmd))
            event.setdefault('ok', True)
        except HelperUnavailable as error:
            event.update({'ok': False, 'helper': 'missing', 'error': str(error)})
        except HelperError as error:
            event.update({'ok': False, 'helper': 'error', 'error': str(error)})
        except ConfigError as error:
            event.update({'ok': False, 'error': str(error)})
        except Exception as error:  # never let a request take the bridge down
            event.update({'ok': False, 'error': ('Unexpected error: %s' % error)[:512]})
        return event

    async def answer(self, kind, cmd):
        if kind == 'sources.status':
            return {'helper': 'ok', 'status': await self.helper('status')}
        if kind == 'sources.get':
            path = await self.config_path()
            config = await asyncio.to_thread(read_config, path)
            entry = find_entry(config, cmd.get('id'))
            return {'path': path, 'exists': config is not None, 'dev': bool(config and config.get('devFastIntervals') is True),
                    'limits': self.limits or DEFAULT_LIMITS, 'entry': entry}
        if kind == 'sources.save':
            async with self.lock:
                path = await self.config_path()
                entry = await asyncio.to_thread(save_entry, path, cmd.get('id'), cmd.get('argv'), cmd.get('intervalS'), self.limits)
                return {'path': path, 'entry': entry, 'reload': await self.reload()}
        if kind == 'sources.seed':
            async with self.lock:
                path = await self.config_path()
                entry = await asyncio.to_thread(seed_entry, path, cmd.get('id'), cmd.get('argv'), cmd.get('intervalS'), self.limits)
                return {'path': path, 'entry': entry, 'seeded': entry is not None,
                        'reload': await self.reload() if entry is not None else {'ok': True}}
        if kind == 'sources.remove':
            async with self.lock:
                path = await self.config_path()
                removed = await asyncio.to_thread(remove_entry, path, cmd.get('id'))
                return {'path': path, 'removed': removed, 'reload': await self.reload() if removed else {'ok': True}}
        if kind == 'sources.test':
            argv = cmd.get('argv')
            check_argv(argv)
            source = {'kind': 'command', 'argv': argv, 'output': 'json'}
            timeout = cmd.get('timeoutS')
            if isinstance(timeout, (int, float)) and not isinstance(timeout, bool):
                source['timeoutS'] = timeout
            reply = await self.helper('test', source=source)
            return {'result': {k: reply.get(k) for k in ('values', 'stdout', 'stderr', 'error', 'exitCode', 'durationMs')}}
        if kind == 'sources.list':
            path = await self.config_path()
            config = await asyncio.to_thread(read_config, path)
            try:
                status = await self.helper('status')
            except (HelperUnavailable, HelperError) as error:
                status = {'ok': False, 'error': str(error)}
            return {'path': path, 'exists': config is not None, 'dev': bool(config and config.get('devFastIntervals') is True),
                    'limits': self.limits or DEFAULT_LIMITS, 'entries': [e for e in (config or {}).get('sources', []) if isinstance(e, dict)],
                    'status': status}
        if kind == 'sources.put':
            async with self.lock:
                path = await self.config_path()
                entry = await asyncio.to_thread(put_entry, path, cmd.get('entry'), cmd.get('previous'))
                return {'path': path, 'entry': entry, 'reload': await self.reload()}
        if kind == 'sources.testSource':
            source = cmd.get('source')
            check_source({**(source if isinstance(source, dict) else {}), 'id': 'test'})
            reply = await self.helper('test', source={k: v for k, v in source.items() if k not in ('id', 'enabled')})
            return {'result': {k: reply.get(k) for k in ('values', 'stdout', 'stderr', 'error', 'exitCode', 'durationMs', 'raw',
                                                          'rawBytes', 'httpStatus', 'contentType', 'secrets')}}
        if kind == 'sources.secrets':
            return {'secrets': await self.helper('secrets')}
        if kind == 'sources.secretSet':
            name, value, store = cmd.get('name'), cmd.get('value'), cmd.get('store', 'file')
            if store == 'keyring':
                await asyncio.to_thread(set_secret_keyring, name, value)
            elif store == 'file':
                path = None
                with contextlib.suppress(HelperUnavailable, HelperError):
                    path = (await self.helper('secrets')).get('file')
                await asyncio.to_thread(set_secret_file, path or default_secrets_path(), name, value)
            else:
                raise ConfigError('Store a secret in the file or the keyring.')
            return {'name': name, 'store': store, 'removed': value is None}
        if kind == 'sources.restart':
            check_id(cmd.get('id'))
            await self.helper('restart', id=cmd['id'], resetAverage=cmd.get('resetAverage') is True)
            return {'resetAverage': cmd.get('resetAverage') is True}
        if kind == 'sources.restartAll':
            await self.helper('restart-all')
            return {}
        if kind == 'sources.browse':
            path = cmd.get('path')
            if path is not None and not isinstance(path, str):
                raise ConfigError('Choose an absolute path.')
            return await asyncio.to_thread(browse, path or None, cmd.get('hidden') is True)
        raise ConfigError('Unknown sources request.')
