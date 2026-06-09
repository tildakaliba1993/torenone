"""TorenOne engineering kernel.

Pure, deterministic, version-pinned structural engineering. No IO, no network, no LLM.
Every public computation is unit-tested and validated against published worked examples
and the benchmark project (see docs/REFERENCES-AND-VALIDATION.md).
"""

from torenone_kernel import rules_version

__all__ = ["rules_version"]
