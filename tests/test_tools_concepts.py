import re

from agent.tools import CONCEPTS_DB, SETUP_GUIDES_DB

GUIDE_MINIMUM_RE = re.compile(r"(\d+\.\d+) for ([a-z0-9\-]+(?:/[a-z0-9\-]+)*)")


def _version(raw: str) -> tuple[int, ...]:
    """Parse a min_python string like '3.10+' into a comparable tuple."""
    return tuple(int(part) for part in raw.rstrip("+").split("."))


def _guide_minimums() -> dict[str, tuple[int, ...]]:
    """Map each package named in the installation guide to its advertised Python minimum."""
    minimums: dict[str, tuple[int, ...]] = {}
    for version, packages in GUIDE_MINIMUM_RE.findall(SETUP_GUIDES_DB["installation"]):
        for package in packages.split("/"):
            minimums[package] = _version(version)
    return minimums


def test_concept_min_python_matches_installation_guide():
    guide = _guide_minimums()
    assert guide, "installation guide no longer advertises any Python minimums to check against"
    for concept, data in CONCEPTS_DB.items():
        package = data["package"].split()[0]
        if package not in guide:
            continue
        advertised = ".".join(str(part) for part in guide[package])
        assert _version(data["min_python"]) >= guide[package], (
            f"CONCEPTS_DB['{concept}'] reports Python {data['min_python']} for {package}, "
            f"but the installation guide requires {advertised}+"
        )
