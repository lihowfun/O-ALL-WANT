"""Small, strict standard-library utilities shared by the calibration tools."""
import hashlib
import json
import os
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def invalid(_):
        raise ValueError('non-finite JSON number')
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=pairs,
                      parse_constant=invalid)


def save(path, value):
    path = Path(path)
    data = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('x', encoding='utf-8') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def append(path, row):
    with Path(path).open('a', encoding='utf-8') as handle:
        handle.write(canonical(row).decode() + '\n')
        handle.flush()
        os.fsync(handle.fileno())


def rows(path):
    path = Path(path)
    if not path.exists():
        return []
    result = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            raise ValueError('blank ledger line')
        # Reuse the strict decoder without creating a temporary file.
        def pairs(items):
            d = {}
            for k, v in items:
                if k in d:
                    raise ValueError('duplicate JSON key')
                d[k] = v
            return d
        result.append(json.loads(line, object_pairs_hook=pairs,
                                 parse_constant=lambda _: (_ for _ in ()).throw(ValueError('non-finite'))))
    return result


def require(ok, message):
    if not ok:
        raise ValueError(message)


def hexsha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)
