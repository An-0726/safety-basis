"""Select the separately frozen current batch; keep the old recovery fixture intact.

All source, date, membership, exact detail and browser checks remain in the shared
acceptance implementation. A new source edit still requires an explicit freeze.
"""
from pathlib import Path
from recovery_release_acceptance import load_expectations as load_frozen_expectations

FIXTURE = Path(__file__).parent / 'fixtures/official_clauses_20261005.json'


def load_expectations(path=FIXTURE):
    return load_frozen_expectations(path)
