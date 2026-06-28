"""Section classification in flexure vs SAISC Red Book §5.1.3 / Table 5.3 (S355JR, Grade 350).

The Red Book states that all listed I/H-sections are Class 1 in flexure **except** an explicit
list (flange-governed Class 2/3, plus one Class 4). This exercises
``checks/classification.py::classify_section`` for pure bending (cu = 0). fy = 350 MPa is fed to
match the Red Book's Grade-350 classification basis (its limits 7.75/9.09/10.7 = 145/170/200 ÷√350).
"""

from __future__ import annotations

import pytest
from cases import RED_BOOK
from torenone_kernel.checks.classification import Class4Error, classify_section
from torenone_kernel.sections import SectionLibrary

_LIB = SectionLibrary.load_default()
_FY = 350.0  # Red Book Table 5.3 basis (Grade 350)

# (designation, expected overall class | None → Class 4, must raise Class4Error)
CASES = [
    ("IPE 200", 1),  # not in the exception list → Class 1 (default)
    ("254x146x37", 1),  # not listed → Class 1
    ("203x133x25", 2),
    ("254x146x31", 2),
    ("356x171x45", 2),
    ("406x140x39", 2),
    ("406x178x54", 2),
    ("533x210x82", 2),
    ("152x152x30", 2),
    ("203x203x52", 2),
    ("254x254x73", 2),
    ("305x305x118", 2),
    ("203x203x46", 3),
    ("305x305x97", 3),
    ("152x152x23", None),  # Class 4 → kernel rejects (out of MVP scope)
]


@pytest.mark.parametrize("designation,expected", CASES, ids=[c[0] for c in CASES])
def test_classification(designation: str, expected: int | None) -> None:
    section = _LIB.get(designation)
    if expected is None:
        with pytest.raises(Class4Error):
            classify_section(section, _FY, 0.0)
        return
    result = classify_section(section, _FY, 0.0)
    assert int(result.overall_class) == expected, (
        f"{designation} ({RED_BOOK}, Table 5.3): kernel Class {int(result.overall_class)} "
        f"(flange {int(result.flange_class)}, web {int(result.web_class)}, b/t={result.flange_bt:.2f}) "
        f"vs Red Book Class {expected}"
    )
