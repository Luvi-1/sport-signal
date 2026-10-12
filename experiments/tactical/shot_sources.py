"""Pinned source verification for the local shot-context adapters (stdlib only)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
from urllib.parse import quote
from urllib.request import urlopen


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha1(path: Path) -> str:
    digest = hashlib.sha1(f'blob {path.stat().st_size}\0'.encode())
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.partial')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def source_record(path: Path, root: Path, url: str) -> dict:
    return {'path': str(path.relative_to(root)), 'url': url,
            'bytes': path.stat().st_size, 'sha256': sha256_file(path)}


def pinned_blob(relative: str, *, tree: dict, commit: str, repository: str,
                cache: Path, staging: Path, root: Path, fetch: bool) -> tuple[Path, dict]:
    """Validate cached/downloaded Git blob against the complete pinned tree."""
    if tree.get('sha') != commit or tree.get('truncated') is not False:
        raise ValueError('Source tree is not the complete declared pin')
    entries = {item['path']: item for item in tree['tree'] if item['type'] == 'blob'}
    entry = entries.get(relative)
    if entry is None:
        raise ValueError(f'File is not in the pinned source: {relative}')
    url = f'https://raw.githubusercontent.com/{repository}/{commit}/{quote(relative)}'
    path = cache / relative
    if not path.is_file():
        path = staging / relative
    if not path.is_file():
        if not fetch:
            raise FileNotFoundError(f'Pinned source missing: {relative}; use --fetch for official source acquisition')
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + '.partial')
        for attempt in range(3):
            try:
                with urlopen(url, timeout=90) as response, temporary.open('wb') as output:
                    for chunk in iter(lambda: response.read(1024 * 1024), b''):
                        output.write(chunk)
                if temporary.stat().st_size != entry['size'] or git_blob_sha1(temporary) != entry['sha']:
                    raise ValueError(f'Pinned source hash mismatch: {relative}')
                temporary.replace(path)
                break
            except (OSError, TimeoutError):
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
    if path.stat().st_size != entry['size'] or git_blob_sha1(path) != entry['sha']:
        raise ValueError(f'Pinned source hash mismatch: {relative}')
    return path, {**source_record(path, root, url), 'git_blob_sha1': entry['sha']}


def manifest_file(path: Path, root: Path, records: list[dict], commit: str) -> dict:
    """Validate actual bytes against the previously inspected source manifest."""
    matches = [r for r in records if Path(r['path']).name == path.name]
    if len(matches) != 1 or f'/{commit}/' not in matches[0]['url']:
        raise ValueError(f'Missing/ambiguous pinned manifest record: {path.name}')
    expected = matches[0]
    actual = source_record(path, root, expected['url'])
    if (actual['sha256'], actual['bytes']) != (expected['sha256'], expected['bytes']):
        raise ValueError(f'Source hash mismatch: {path.name}')
    return actual
