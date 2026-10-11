"""Exact quality-repair continuations; historical receipts are never rewritten."""
import json
from pathlib import Path

PATH = 'docs/QUALITY_REPAIR_SUPERSESSIONS_20261011.json'


def load_supersessions(root: Path):
    path = root / PATH
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('schemaVersion') != 'quality-repair-supersessions-v1':
        raise ValueError('invalid quality-repair continuation schema')
    items = {item['id']: item for item in data['items']}
    if len(items) != len(data['items']):
        raise ValueError('duplicate quality-repair continuation identity')
    return items


def continued_hash(items, hazard_id, historical_hash, field, file):
    """Only the exact registered historical target binding may be continued."""
    item = (items or {}).get(hazard_id)
    if item and item['newLifecycle'] == 'active' and any(
        row['file'] == file and row['field'] == field and row['oldValue'] == historical_hash
        for row in item['supersedes']
    ):
        return item['newHazardHash']
    return historical_hash
