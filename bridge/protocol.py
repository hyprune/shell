"""Offline IPC 0.1 validation and byte framing. No QML text/binary ambiguity."""
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
    schema = json.loads(path.read_text())
    registry = registry.with_resource(schema['$id'], Resource.from_contents(schema))
SCHEMA = json.loads((ROOT / 'ipc.schema.json').read_text())
VALIDATOR = Draft202012Validator(SCHEMA, registry=registry)
MOCK_SCHEMA = json.loads((ROOT / 'mock-preview.schema.json').read_text())
MOCK_VALIDATOR = Draft202012Validator(MOCK_SCHEMA, registry=registry)
V2_VALIDATOR = Draft202012Validator(json.loads((ROOT / 'v0.2/ipc.schema.json').read_text()), registry=registry)
TRANSITION_VALIDATOR = Draft202012Validator(json.loads((ROOT / 'presentation-transition.schema.json').read_text()))
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


async def read_frame(reader, validator=VALIDATOR):
    first = await reader.readexactly(1)
    async with asyncio.timeout(10):
        header = first + await reader.readexactly(3)
        length = struct.unpack('!I', header)[0]
        if not 1 <= length <= LIMIT:
            raise ValueError('invalid frame length')
        data = await reader.readexactly(length)
    obj = decode(data)
    validator.validate(obj)
    return obj


def frame(obj, validator=VALIDATOR):
    validator.validate(obj)
    data = json.dumps(obj, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
    if not 1 <= len(data) <= LIMIT:
        raise ValueError('invalid outgoing frame length')
    return struct.pack('!I', len(data)) + data
