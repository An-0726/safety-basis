"""Exact independently reviewed city-gas body, no prefix-based exclusions."""
VERSION = 'LV_MOHURD_CITY_GAS_MAJOR_2023'
CLAUSES = frozenset(f'C_MOHURD_CITY_GAS_2023_{n}' for n in range(1, 12))
EVIDENCE = frozenset({'E_MOHURD_CITY_GAS_FULL_20261001', 'E_COPYRIGHT_LAW_ARTICLE5_20261001'})
