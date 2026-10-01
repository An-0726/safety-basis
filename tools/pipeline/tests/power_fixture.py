"""Exact independently reviewed power-body successor IDs; no canonical identities added."""
VERSION = 'LV_NDRC_POWER_MAJOR_2026'
CLAUSES = frozenset(f'C_NDRC_POWER_2026_{n}' for n in range(1, 39))
EVIDENCE = frozenset(f'E_NDRC_POWER_{kind}_20261001' for kind in ('FULL','WEB','COUNT','REPEAL'))
