"""Exact reviewed coal-body successor IDs, excluding legacy ordinary evidence."""
VERSION = 'LV_MEM_COAL_MAJOR_2026'
CLAUSES = frozenset(f'C_MEM_COAL_2026_{n}' for n in range(1, 22))
EVIDENCE = frozenset({'E_MEM_COAL_FULL_20261001'} | {f'E_MEM_COAL_CLARIFICATION_{n}_20261001' for n in range(1, 8)})
