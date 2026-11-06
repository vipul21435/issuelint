# issuelint on public SWE-bench data

## Tasks flagged per check, issue text only

| check | SWE-bench Lite | SWE-bench Verified | SWE-bench test | SWE-Bench+ |
| --- | ---: | ---: | ---: | ---: |
| `solution_leakage` | 17 (5.7 %) | 19 (3.8 %) | 52 (2.3 %) | 12 (2.2 %) |
| `test_leakage` | 3 (1.0 %) | 8 (1.6 %) | 22 (1.0 %) | 2 (0.4 %) |
| `location_hints` | 41.7 % (score > 0) | 50.6 % (score > 0) | 52.1 % (score > 0) | 45.6 % (score > 0) |
| `underspecification` | 153 (51.0 %) | 250 (50.0 %) | 1283 (55.9 %) | 218 (39.8 %) |
| `external_links` | 0 (0.0 %) | 52 (10.4 %) | 314 (13.7 %) | 75 (13.7 %) |
| `scope_gap` | 222 (74.0 %) | 361 (72.2 %) | 1811 (78.9 %) | 362 (66.1 %) |
| tasks | 300 | 500 | 2294 | 548 |

Examples (highest-scoring flagged tasks):

- SWE-bench Lite, `solution_leakage`: `django__django-14534`, `django__django-16255`, `pytest-dev__pytest-5227`
- SWE-bench Lite, `test_leakage`: `django__django-13757`, `sympy__sympy-22005`, `django__django-15695`
- SWE-bench Lite, `location_hints`: `django__django-11583`, `django__django-12453`, `django__django-13321`
- SWE-bench Lite, `underspecification`: `django__django-10914`, `django__django-11039`, `django__django-11099`
- SWE-bench Lite, `scope_gap`: `astropy__astropy-12907`, `astropy__astropy-14365`, `astropy__astropy-14995`
- SWE-bench Verified, `solution_leakage`: `django__django-11451`, `django__django-14534`, `django__django-16255`
- SWE-bench Verified, `test_leakage`: `django__django-14349`, `matplotlib__matplotlib-20488`, `sympy__sympy-23824`
- SWE-bench Verified, `location_hints`: `astropy__astropy-13977`, `astropy__astropy-14096`, `astropy__astropy-14309`
- SWE-bench Verified, `underspecification`: `astropy__astropy-7166`, `django__django-14434`, `django__django-15499`
- SWE-bench Verified, `external_links`: `astropy__astropy-8707`, `django__django-10097`, `django__django-11066`
- SWE-bench Verified, `scope_gap`: `astropy__astropy-12907`, `astropy__astropy-13033`, `astropy__astropy-13236`
- SWE-bench test, `solution_leakage`: `django__django-11451`, `django__django-14534`, `django__django-15297`
- SWE-bench test, `test_leakage`: `django__django-13757`, `django__django-14349`, `django__django-15297`
- SWE-bench test, `location_hints`: `astropy__astropy-12880`, `astropy__astropy-13638`, `astropy__astropy-13745`
- SWE-bench test, `underspecification`: `astropy__astropy-7166`, `django__django-11260`, `django__django-11539`
- SWE-bench test, `external_links`: `astropy__astropy-12544`, `astropy__astropy-12891`, `astropy__astropy-13075`
- SWE-bench test, `scope_gap`: `astropy__astropy-11693`, `astropy__astropy-12057`, `astropy__astropy-12544`
- SWE-Bench+, `solution_leakage`: `sympy__sympy-26442`, `sympy__sympy-26303`, `pytest-dev__pytest-12492`
- SWE-Bench+, `test_leakage`: `pylint-dev__pylint-9867`, `pylint-dev__pylint-9866`
- SWE-Bench+, `location_hints`: `sympy__sympy-26980`, `sympy__sympy-26954`, `matplotlib__matplotlib-28541`
- SWE-Bench+, `underspecification`: `astropy__astropy-15751`, `sympy__sympy-26098`, `sympy__sympy-26940`
- SWE-Bench+, `external_links`: `sympy__sympy-26940`, `sympy__sympy-26935`, `sympy__sympy-26597`
- SWE-Bench+, `scope_gap`: `sympy__sympy-26920`, `sympy__sympy-26919`, `sympy__sympy-26882`

## Tasks flagged per check, issue text plus hints_text

| check | SWE-bench Lite | SWE-bench Verified | SWE-bench test | SWE-Bench+ |
| --- | ---: | ---: | ---: | ---: |
| `solution_leakage` | 33 (11.0 %) | 42 (8.4 %) | 131 (5.7 %) | 28 (5.1 %) |
| `test_leakage` | 7 (2.3 %) | 17 (3.4 %) | 40 (1.7 %) | 3 (0.5 %) |
| `location_hints` | 57.7 % (score > 0) | 62.2 % (score > 0) | 64.7 % (score > 0) | 56.8 % (score > 0) |
| `underspecification` | 117 (39.0 %) | 218 (43.6 %) | 981 (42.8 %) | 139 (25.4 %) |
| `external_links` | 15 (5.0 %) | 63 (12.6 %) | 351 (15.3 %) | 63 (11.5 %) |
| `scope_gap` | 196 (65.3 %) | 322 (64.4 %) | 1662 (72.4 %) | 331 (60.4 %) |
| tasks | 300 | 500 | 2294 | 548 |

Examples (highest-scoring flagged tasks):

- SWE-bench Lite, `solution_leakage`: `astropy__astropy-14995`, `django__django-14534`, `django__django-16255`
- SWE-bench Lite, `test_leakage`: `django__django-13757`, `django__django-15814`, `sympy__sympy-21612`
- SWE-bench Lite, `location_hints`: `django__django-11179`, `django__django-11583`, `django__django-11620`
- SWE-bench Lite, `underspecification`: `django__django-11039`, `django__django-11099`, `django__django-11742`
- SWE-bench Lite, `external_links`: `django__django-10914`, `django__django-11179`, `django__django-11848`
- SWE-bench Lite, `scope_gap`: `astropy__astropy-12907`, `astropy__astropy-14365`, `astropy__astropy-14995`
- SWE-bench Verified, `solution_leakage`: `astropy__astropy-14539`, `astropy__astropy-14995`, `django__django-11451`
- SWE-bench Verified, `test_leakage`: `django__django-14349`, `django__django-15554`, `django__django-15814`
- SWE-bench Verified, `location_hints`: `astropy__astropy-13453`, `astropy__astropy-13579`, `astropy__astropy-13977`
- SWE-bench Verified, `underspecification`: `django__django-14434`, `django__django-15499`, `django__django-15987`
- SWE-bench Verified, `external_links`: `astropy__astropy-7166`, `astropy__astropy-8707`, `django__django-10097`
- SWE-bench Verified, `scope_gap`: `astropy__astropy-12907`, `astropy__astropy-13033`, `astropy__astropy-13236`
- SWE-bench test, `solution_leakage`: `astropy__astropy-13668`, `astropy__astropy-14539`, `astropy__astropy-14995`
- SWE-bench test, `test_leakage`: `django__django-13757`, `django__django-14266`, `django__django-14349`
- SWE-bench test, `location_hints`: `astropy__astropy-12880`, `astropy__astropy-13453`, `astropy__astropy-13469`
- SWE-bench test, `underspecification`: `django__django-11260`, `django__django-11539`, `django__django-12748`
- SWE-bench test, `external_links`: `astropy__astropy-12544`, `astropy__astropy-12891`, `astropy__astropy-14371`
- SWE-bench test, `scope_gap`: `astropy__astropy-11693`, `astropy__astropy-12544`, `astropy__astropy-12907`
- SWE-Bench+, `solution_leakage`: `matplotlib__matplotlib-28582`, `matplotlib__matplotlib-28487`, `sympy__sympy-26429`
- SWE-Bench+, `test_leakage`: `pylint-dev__pylint-9867`, `pylint-dev__pylint-9866`, `sympy__sympy-26429`
- SWE-Bench+, `location_hints`: `sympy__sympy-26980`, `sympy__sympy-26954`, `sympy__sympy-26919`
- SWE-Bench+, `underspecification`: `astropy__astropy-15751`, `sympy__sympy-26920`, `sympy__sympy-26683`
- SWE-Bench+, `external_links`: `sympy__sympy-26597`, `matplotlib__matplotlib-28503`, `matplotlib__matplotlib-28388`
- SWE-Bench+, `scope_gap`: `sympy__sympy-26920`, `sympy__sympy-26782`, `sympy__sympy-26779`

## Agreement with the SWE-bench Verified annotations

Label `underspecified >= 2`: 1699 annotated tasks, 650 positive; held-out half: 866 tasks.

| score or metric | AUC, all (95 % interval) | AUC, held-out half | flagged among positives | flagged among negatives |
| --- | ---: | ---: | ---: | ---: |
| `underspecification` | 0.569 (0.541 to 0.596) | 0.576 (0.538 to 0.615) | 61.5 % | 52.2 % |
| `underspecification.has_reproduction` | 0.435 (0.411 to 0.459) | 0.425 (0.394 to 0.458) |  |  |
| `underspecification.has_expected_actual` | 0.451 (0.428 to 0.474) | 0.446 (0.411 to 0.480) |  |  |
| `underspecification.has_error_text` | 0.496 (0.473 to 0.519) | 0.494 (0.461 to 0.527) |  |  |
| `underspecification.tokens` | 0.445 (0.415 to 0.473) | 0.445 (0.404 to 0.485) |  |  |
| `external_links` | 0.517 (0.493 to 0.544) | 0.504 (0.469 to 0.536) | 17.8 % | 10.6 % |
| `location_hints.identifiers` | 0.558 (0.531 to 0.585) | 0.549 (0.512 to 0.587) |  |  |
| `solution_leakage.added_ngrams` | 0.597 (0.570 to 0.627) | 0.588 (0.547 to 0.627) |  |  |

Label `false_negative >= 2`: 1699 annotated tasks, 1039 positive; held-out half: 866 tasks.

| score or metric | AUC, all (95 % interval) | AUC, held-out half | flagged among positives | flagged among negatives |
| --- | ---: | ---: | ---: | ---: |
| `scope_gap` | 0.520 (0.494 to 0.546) | 0.507 (0.470 to 0.543) | 81.9 % | 72.3 % |
| `scope_gap.unmentioned` | 0.642 (0.614 to 0.667) | 0.645 (0.607 to 0.681) |  |  |
| `scope_gap.tests_use_new_names` | 0.676 (0.655 to 0.696) | 0.683 (0.654 to 0.713) |  |  |
| `location_hints` | 0.474 (0.447 to 0.503) | 0.483 (0.447 to 0.519) | 0.0 % | 0.0 % |
| `test_leakage` | 0.496 (0.490 to 0.501) | 0.494 (0.484 to 0.502) | 0.5 % | 1.4 % |
| `solution_leakage.added_ngrams` | 0.703 (0.678 to 0.730) | 0.715 (0.680 to 0.751) |  |  |
