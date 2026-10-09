"""Offline versioned IPC validation and byte framing. No QML text/binary ambiguity."""
import asyncio
import json
import math
import struct
from pathlib import Path
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

LIMIT = 1_048_576
ROOT = Path(__file__).resolve().parents[1] / 'protocol'
registry = Registry()
for path in ROOT.rglob('*.schema.json'):
    if 'worlds' in path.relative_to(ROOT).parts: continue
    schema = json.loads(path.read_text())
    registry = registry.with_resource(schema['$id'], Resource.from_contents(schema))
SCHEMA = json.loads((ROOT / 'ipc.schema.json').read_text())
VALIDATOR = Draft202012Validator(SCHEMA, registry=registry)
V2_VALIDATOR = Draft202012Validator(json.loads((ROOT / 'v0.2/ipc.schema.json').read_text()), registry=registry)
V3_VALIDATOR = Draft202012Validator(json.loads((ROOT / "v0.3/ipc.schema.json").read_text()), registry=registry)
V4_VALIDATOR = Draft202012Validator(json.loads((ROOT / "v0.4/ipc.schema.json").read_text()), registry=registry)
V5_VALIDATOR = Draft202012Validator(json.loads((ROOT / "v0.5/ipc.schema.json").read_text()), registry=registry)
V6_VALIDATOR = Draft202012Validator(json.loads((ROOT / "v0.6/ipc.schema.json").read_text()), registry=registry)
V7_VALIDATOR = Draft202012Validator(json.loads((ROOT / "v0.7/ipc.schema.json").read_text()), registry=registry)
V8_VALIDATOR = Draft202012Validator(json.loads((ROOT / "v0.8/ipc.schema.json").read_text()), registry=registry)
V9_VALIDATOR = Draft202012Validator(json.loads((ROOT / "v0.9/ipc.schema.json").read_text()), registry=registry)
V10_VALIDATOR = Draft202012Validator(json.loads((ROOT / "v0.10/ipc.schema.json").read_text()), registry=registry)
V11_VALIDATOR = Draft202012Validator(json.loads((ROOT / "v0.11/ipc.schema.json").read_text()), registry=registry)
V12_VALIDATOR = Draft202012Validator(json.loads((ROOT / "v0.12/ipc.schema.json").read_text()), registry=registry)
# Canonical 0.13 adds camera revision responses beside the generic response
# branch, making top-level oneOf ambiguous for every {revision:...} reply.
# Preserve the pin, accept the union at the envelope, and still validate each
# response against the originating method in validate_response().
v13_schema = json.loads((ROOT / "v0.13/ipc.schema.json").read_text())
v13_schema['anyOf'] = v13_schema.pop('oneOf')
V13_VALIDATOR = Draft202012Validator(v13_schema, registry=registry)
V14_VALIDATOR = Draft202012Validator(json.loads((ROOT / "v0.14/ipc.schema.json").read_text()), registry=registry)
V15_VALIDATOR = Draft202012Validator(json.loads((ROOT / "v0.15/ipc.schema.json").read_text()), registry=registry)
V16_VALIDATOR = Draft202012Validator(json.loads((ROOT / "v0.16/ipc.schema.json").read_text()), registry=registry)
WORLD_VALIDATOR = Draft202012Validator(json.loads((ROOT / 'world.schema.json').read_text()), registry=registry)
WORLD_V2_VALIDATOR = Draft202012Validator(json.loads((ROOT / 'v0.2/world.schema.json').read_text()), registry=registry)


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def decode(data):
    # Scan before parsing to bound nesting, respecting strings/escapes.
    depth = 0
    string = escape = False
    for char in data.decode('utf-8', errors='strict'):
        if string:
            if escape:
                escape = False
            elif char == '\\':
                escape = True
            elif char == '"':
                string = False
        elif char == '"':
            string = True
        elif char in '[{':
            depth += 1
            if depth > 64:
                raise ValueError('JSON nesting exceeds 64')
        elif char in ']}':
            depth -= 1
    obj = json.loads(data, object_pairs_hook=unique,
                     parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    def finite(value):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('nonfinite number')
        if isinstance(value, dict):
            for v in value.values(): finite(v)
        elif isinstance(value, list):
            for v in value: finite(v)
    finite(obj)
    return obj


def validate_response(obj, method, validator=VALIDATOR):
    if 'error' not in obj:
        validator.evolve(schema={'$ref': validator.schema['$id'] + '#/$defs/' + method + '.response'}).validate(obj)


async def read_packet(reader):
    first = await reader.readexactly(1)
    async with asyncio.timeout(10):
        header = first + await reader.readexactly(3)
        length = struct.unpack('!I', header)[0]
        if not 1 <= length <= LIMIT:
            raise ValueError('invalid frame length')
        data = await reader.readexactly(length)
    return data


async def read_frame(reader, validator=VALIDATOR):
    obj = decode(await read_packet(reader))
    validator.validate(obj)
    return obj


def frame(obj, validator=VALIDATOR):
    validator.validate(obj)
    data = json.dumps(obj, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
    if not 1 <= len(data) <= LIMIT:
        raise ValueError('invalid outgoing frame length')
    return struct.pack('!I', len(data)) + data

SUPPORTED_PROTOCOLS = tuple("0." + str(n) for n in range(1,17))
def at_least(protocol, minor):
    return protocol in SUPPORTED_PROTOCOLS and tuple(map(int,protocol.split("."))) >= (0,minor)

# New world common schemas contain authoring definitions absent from frozen IPC
# pins. Keep a separate registry so older IPC validation cannot be widened.
world_registry = registry
for path in (ROOT / 'worlds').rglob('*.schema.json'):
    schema = json.loads(path.read_text())
    world_registry = world_registry.with_resource(schema['$id'], Resource.from_contents(schema))
WORLD_VALIDATORS = {"0.1":WORLD_VALIDATOR,"0.2":WORLD_V2_VALIDATOR,**{
    v:Draft202012Validator(json.loads((ROOT / 'worlds' / ('v'+v) / 'world.schema.json').read_text()),registry=world_registry)
    for v in ['0.3','0.4','0.5']}}


# One validator per negotiated protocol (0.1 uses the unversioned pin).
VALIDATORS = {'0.1': VALIDATOR, **{'0.' + str(n): globals()['V%d_VALIDATOR' % n] for n in range(2, 17)}}
