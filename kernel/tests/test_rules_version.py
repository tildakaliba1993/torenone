"""Every DesignResult must carry the pinned code editions (PRD NFR-3, FR-20).

This is the first TDD harness proof: it asserts the audit/reproducibility contract that
the rest of the kernel will depend on.
"""

from torenone_kernel import rules_version


def test_as_dict_contains_all_required_codes() -> None:
    versions = rules_version.as_dict()
    for code in ("SANS 10160-1", "SANS 10160-2", "SANS 10160-3", "SANS 10162-1"):
        assert code in versions, f"missing pinned edition for {code}"


def test_versions_are_non_empty_strings() -> None:
    for code, edition in rules_version.as_dict().items():
        assert isinstance(edition, str) and edition, f"{code} has no pinned edition"
