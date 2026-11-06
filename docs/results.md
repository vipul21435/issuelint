# issuelint on public SWE-bench data

## Tasks flagged per check, issue text only

| check | SWE-bench Lite | SWE-bench Verified | SWE-bench test | SWE-Bench+ |
| --- | ---: | ---: | ---: | ---: |
| `solution_leakage` | 18 (6.0 %) | 21 (4.2 %) | 66 (2.9 %) | 21 (3.8 %) |
| `test_leakage` | 2 (0.7 %) | 5 (1.0 %) | 19 (0.8 %) | 3 (0.5 %) |
| `location_hints` | 42.0 % (score > 0) | 51.0 % (score > 0) | 52.4 % (score > 0) | 46.2 % (score > 0) |
| `underspecification` | 154 (51.3 %) | 253 (50.6 %) | 1288 (56.1 %) | 218 (39.8 %) |
| `external_links` | 0 (0.0 %) | 51 (10.2 %) | 313 (13.6 %) | 75 (13.7 %) |
| `scope_gap` | 222 (74.0 %) | 361 (72.2 %) | 1811 (78.9 %) | 362 (66.1 %) |
| tasks | 300 | 500 | 2294 | 548 |

Examples (highest-scoring flagged tasks):

- SWE-bench Lite, `solution_leakage`: `django__django-14534`, `django__django-16255`, `pytest-dev__pytest-5227`
- SWE-bench Lite, `test_leakage`: `django__django-15695`, `pytest-dev__pytest-7373`
- SWE-bench Lite, `location_hints`: `django__django-11583`, `django__django-12453`, `django__django-13321`
- SWE-bench Lite, `underspecification`: `django__django-10914`, `django__django-11039`, `django__django-11099`
- SWE-bench Lite, `scope_gap`: `astropy__astropy-12907`, `astropy__astropy-14365`, `astropy__astropy-14995`
- SWE-bench Verified, `solution_leakage`: `django__django-11451`, `django__django-14534`, `django__django-16255`
- SWE-bench Verified, `test_leakage`: `django__django-15695`, `matplotlib__matplotlib-20488`, `sympy__sympy-23824`
- SWE-bench Verified, `location_hints`: `astropy__astropy-13977`, `astropy__astropy-14096`, `astropy__astropy-14309`
- SWE-bench Verified, `underspecification`: `astropy__astropy-7166`, `django__django-14434`, `django__django-15499`
- SWE-bench Verified, `external_links`: `astropy__astropy-8707`, `django__django-10097`, `django__django-11066`
- SWE-bench Verified, `scope_gap`: `astropy__astropy-12907`, `astropy__astropy-13033`, `astropy__astropy-13236`
- SWE-bench test, `solution_leakage`: `django__django-11451`, `django__django-14534`, `django__django-15297`
- SWE-bench test, `test_leakage`: `astropy__astropy-13390`, `django__django-15695`, `django__django-16597`
- SWE-bench test, `location_hints`: `astropy__astropy-12880`, `astropy__astropy-13638`, `astropy__astropy-13745`
- SWE-bench test, `underspecification`: `astropy__astropy-7166`, `django__django-11260`, `django__django-11539`
- SWE-bench test, `external_links`: `astropy__astropy-12544`, `astropy__astropy-12891`, `astropy__astropy-13075`
- SWE-bench test, `scope_gap`: `astropy__astropy-11693`, `astropy__astropy-12057`, `astropy__astropy-12544`
- SWE-Bench+, `solution_leakage`: `matplotlib__matplotlib-27773`, `matplotlib__matplotlib-28030`, `sympy__sympy-26442`
- SWE-Bench+, `test_leakage`: `pylint-dev__pylint-9867`, `pylint-dev__pylint-9866`, `pytest-dev__pytest-12414`
- SWE-Bench+, `location_hints`: `sympy__sympy-26980`, `sympy__sympy-26954`, `matplotlib__matplotlib-28541`
- SWE-Bench+, `underspecification`: `astropy__astropy-15751`, `sympy__sympy-26098`, `sympy__sympy-26940`
- SWE-Bench+, `external_links`: `sympy__sympy-26940`, `sympy__sympy-26935`, `sympy__sympy-26597`
- SWE-Bench+, `scope_gap`: `sympy__sympy-26920`, `sympy__sympy-26919`, `sympy__sympy-26882`

## Tasks flagged per check, issue text plus hints_text

| check | SWE-bench Lite | SWE-bench Verified | SWE-bench test | SWE-Bench+ |
| --- | ---: | ---: | ---: | ---: |
| `solution_leakage` | 33 (11.0 %) | 44 (8.8 %) | 142 (6.2 %) | 35 (6.4 %) |
| `test_leakage` | 6 (2.0 %) | 14 (2.8 %) | 35 (1.5 %) | 4 (0.7 %) |
| `location_hints` | 57.7 % (score > 0) | 62.6 % (score > 0) | 65.0 % (score > 0) | 58.0 % (score > 0) |
| `underspecification` | 117 (39.0 %) | 220 (44.0 %) | 984 (42.9 %) | 140 (25.5 %) |
| `external_links` | 15 (5.0 %) | 62 (12.4 %) | 350 (15.3 %) | 63 (11.5 %) |
| `scope_gap` | 196 (65.3 %) | 322 (64.4 %) | 1662 (72.4 %) | 331 (60.4 %) |
| tasks | 300 | 500 | 2294 | 548 |

Examples (highest-scoring flagged tasks):

- SWE-bench Lite, `solution_leakage`: `astropy__astropy-14995`, `django__django-14534`, `django__django-16255`
- SWE-bench Lite, `test_leakage`: `django__django-15695`, `django__django-15814`, `sympy__sympy-21612`
- SWE-bench Lite, `location_hints`: `django__django-11179`, `django__django-11583`, `django__django-11620`
- SWE-bench Lite, `underspecification`: `django__django-11039`, `django__django-11099`, `django__django-11742`
- SWE-bench Lite, `external_links`: `django__django-10914`, `django__django-11179`, `django__django-11848`
- SWE-bench Lite, `scope_gap`: `astropy__astropy-12907`, `astropy__astropy-14365`, `astropy__astropy-14995`
- SWE-bench Verified, `solution_leakage`: `astropy__astropy-14539`, `astropy__astropy-14995`, `django__django-11451`
- SWE-bench Verified, `test_leakage`: `django__django-15695`, `django__django-15814`, `matplotlib__matplotlib-20488`
- SWE-bench Verified, `location_hints`: `astropy__astropy-13453`, `astropy__astropy-13579`, `astropy__astropy-13977`
- SWE-bench Verified, `underspecification`: `django__django-14434`, `django__django-15499`, `django__django-15987`
- SWE-bench Verified, `external_links`: `astropy__astropy-7166`, `astropy__astropy-8707`, `django__django-10097`
- SWE-bench Verified, `scope_gap`: `astropy__astropy-12907`, `astropy__astropy-13033`, `astropy__astropy-13236`
- SWE-bench test, `solution_leakage`: `astropy__astropy-13668`, `astropy__astropy-14539`, `astropy__astropy-14995`
- SWE-bench test, `test_leakage`: `astropy__astropy-13390`, `django__django-14077`, `django__django-15695`
- SWE-bench test, `location_hints`: `astropy__astropy-12880`, `astropy__astropy-13453`, `astropy__astropy-13469`
- SWE-bench test, `underspecification`: `django__django-11260`, `django__django-11539`, `django__django-12748`
- SWE-bench test, `external_links`: `astropy__astropy-12544`, `astropy__astropy-12891`, `astropy__astropy-14371`
- SWE-bench test, `scope_gap`: `astropy__astropy-11693`, `astropy__astropy-12544`, `astropy__astropy-12907`
- SWE-Bench+, `solution_leakage`: `matplotlib__matplotlib-28582`, `matplotlib__matplotlib-28487`, `sympy__sympy-26122`
- SWE-Bench+, `test_leakage`: `pylint-dev__pylint-9867`, `pylint-dev__pylint-9866`, `pytest-dev__pytest-12414`
- SWE-Bench+, `location_hints`: `sympy__sympy-26980`, `sympy__sympy-26954`, `sympy__sympy-26919`
- SWE-Bench+, `underspecification`: `astropy__astropy-15751`, `sympy__sympy-26920`, `sympy__sympy-26683`
- SWE-Bench+, `external_links`: `sympy__sympy-26597`, `matplotlib__matplotlib-28503`, `matplotlib__matplotlib-28388`
- SWE-Bench+, `scope_gap`: `sympy__sympy-26920`, `sympy__sympy-26782`, `sympy__sympy-26779`

## Agreement with the SWE-bench Verified annotations

Label `underspecified >= 2`: 1699 annotated tasks, 650 positive; held-out half: 866 tasks.

| score or metric | AUC, all (95 % interval) | AUC, held-out half | flagged among positives | flagged among negatives |
| --- | ---: | ---: | ---: | ---: |
| `underspecification` | 0.568 (0.541 to 0.596) | 0.577 (0.538 to 0.616) | 61.7 % | 52.5 % |
| `underspecification.has_reproduction` | 0.436 (0.412 to 0.460) | 0.424 (0.391 to 0.456) |  |  |
| `underspecification.has_expected_actual` | 0.451 (0.428 to 0.474) | 0.446 (0.411 to 0.480) |  |  |
| `underspecification.has_error_text` | 0.496 (0.473 to 0.519) | 0.494 (0.461 to 0.527) |  |  |
| `underspecification.tokens` | 0.445 (0.415 to 0.473) | 0.445 (0.404 to 0.485) |  |  |
| `external_links` | 0.517 (0.493 to 0.544) | 0.504 (0.469 to 0.536) | 17.8 % | 10.5 % |

Label `false_negative >= 2`: 1699 annotated tasks, 1039 positive; held-out half: 866 tasks.

| score or metric | AUC, all (95 % interval) | AUC, held-out half | flagged among positives | flagged among negatives |
| --- | ---: | ---: | ---: | ---: |
| `scope_gap` | 0.520 (0.494 to 0.546) | 0.507 (0.470 to 0.543) | 81.9 % | 72.3 % |
| `scope_gap.unmentioned` | 0.642 (0.614 to 0.667) | 0.645 (0.607 to 0.681) |  |  |
| `scope_gap.tests_use_new_names` | 0.679 (0.657 to 0.702) | 0.681 (0.648 to 0.712) |  |  |
| `location_hints` | 0.473 (0.447 to 0.501) | 0.482 (0.447 to 0.518) | 0.0 % | 0.0 % |
| `test_leakage` | 0.495 (0.488 to 0.501) | 0.494 (0.483 to 0.505) | 0.4 % | 1.1 % |
| `solution_leakage.added_ngrams` | 0.703 (0.679 to 0.728) | 0.713 (0.677 to 0.748) |  |  |
