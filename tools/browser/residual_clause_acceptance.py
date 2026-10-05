"""Current residual-batch fixture; earlier official and recovery freezes stay immutable."""
from pathlib import Path
from recovery_release_acceptance import load_expectations as load_frozen_expectations

FIXTURE = Path(__file__).parent / 'fixtures/residual_clauses_20261005.json'


def load_expectations(path=FIXTURE):
    return load_frozen_expectations(path)
