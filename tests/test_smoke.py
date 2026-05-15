"""Phase 1 smoke test — verifies the rename landed atomically.

Ensures that the top-level ``vibe_cading`` and ``parts`` namespaces
resolve and that a representative class import from each succeeds.
"""


def test_imports():
    """Top-level packages import without error."""
    import vibe_cading  # noqa: F401
    import parts  # noqa: F401


def test_library_class_resolves():
    """A representative library class resolves from the new namespace."""
    from vibe_cading.mechanical.screws import MetricMachineScrew  # noqa: F401


def test_project_specific_class_resolves():
    """A representative project-specific part resolves under ``parts.*``."""
    from parts.arrma_vorteks_223s.esc_mount import EscMount  # noqa: F401
