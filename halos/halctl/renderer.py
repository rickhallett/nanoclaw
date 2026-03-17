"""Personality profile renderer for microHAL fleet.

Loads a YAML personality schema and profile, validates dimensions,
and concatenates prose blocks into a single personality section.

Key invariant: deterministic. Same inputs = same output. No LLM. No randomness.
"""

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    from halos.nightctl import yaml_shim as yaml


class SchemaValidationError(Exception):
    """Raised when a profile fails validation against the schema."""


def _load_yaml(path: Path) -> dict:
    """Load a YAML file and return its contents."""
    with open(path) as f:
        return yaml.safe_load(f)


def _strip_frontmatter(text: str) -> tuple[dict, str]:
    """Strip YAML frontmatter from a block, returning (metadata, body)."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            fm_text = text[4:end]
            body = text[end + 5:]
            meta = yaml.safe_load(fm_text) or {}
            return meta, body
    return {}, text


def _load_block(blocks_dir: Path, dimension: str, value: Any) -> tuple[dict, str]:
    """Load a block file for a dimension/value pair.

    Returns (frontmatter_metadata, prose_body). If block file does not
    exist or is empty, returns ({}, "").
    """
    # Normalize booleans to lowercase filenames (True -> "true.md")
    file_value = str(value).lower() if isinstance(value, bool) else str(value)
    block_path = blocks_dir / dimension / f"{file_value}.md"
    if not block_path.exists():
        return {}, ""
    text = block_path.read_text()
    if not text.strip():
        return {}, ""
    return _strip_frontmatter(text)


def _build_dimension_index(schema: dict) -> dict:
    """Build a flat lookup: dimension_name -> {type, levels/min/max, default}."""
    index = {}
    for category in schema["categories"]:
        for dim in category["dimensions"]:
            index[dim["name"]] = dim
    return index


def _validate_profile(profile: dict, dim_index: dict) -> None:
    """Validate profile dimensions against schema.

    Raises SchemaValidationError for:
    - Missing dimensions (in schema but not in profile)
    - Unknown dimensions (in profile but not in schema)
    - Invalid values (out of range, not in levels)
    """
    profile_dims = profile.get("dimensions", {})

    # Check for unknown dimensions
    unknown = set(profile_dims.keys()) - set(dim_index.keys())
    if unknown:
        raise SchemaValidationError(
            f"Unknown dimensions in profile: {sorted(unknown)}"
        )

    # Check for missing dimensions
    missing = set(dim_index.keys()) - set(profile_dims.keys())
    if missing:
        raise SchemaValidationError(
            f"Missing dimensions in profile: {sorted(missing)}"
        )

    # Validate values
    for name, value in profile_dims.items():
        spec = dim_index[name]
        dtype = spec["type"]

        if dtype == "ordinal":
            if value not in spec["levels"]:
                raise SchemaValidationError(
                    f"Dimension '{name}': value '{value}' not in "
                    f"allowed levels {spec['levels']}"
                )
        elif dtype == "boolean":
            if not isinstance(value, bool):
                raise SchemaValidationError(
                    f"Dimension '{name}': expected boolean, got {type(value).__name__}"
                )
        elif dtype == "integer":
            if not isinstance(value, int):
                raise SchemaValidationError(
                    f"Dimension '{name}': expected integer, got {type(value).__name__}"
                )
            if value < spec.get("min", 0) or value > spec.get("max", 999):
                raise SchemaValidationError(
                    f"Dimension '{name}': value {value} outside range "
                    f"[{spec.get('min', 0)}, {spec.get('max', 999)}]"
                )


def render_personality(
    profile_name: str,
    schema_path: Path,
    profiles_dir: Path,
    blocks_dir: Path,
) -> str:
    """Render a personality profile into CLAUDE.md prose.

    Args:
        profile_name: Name of the profile (e.g., "ben", "default").
        schema_path: Path to personality-schema.yaml.
        profiles_dir: Directory containing profile YAML files.
        blocks_dir: Directory containing prose block files.

    Returns:
        Rendered personality prose as a string.

    Raises:
        FileNotFoundError: If schema or profile file is missing.
        SchemaValidationError: If profile fails validation.
    """
    schema = _load_yaml(schema_path)
    profile = _load_yaml(profiles_dir / f"{profile_name}.yaml")
    dim_index = _build_dimension_index(schema)

    _validate_profile(profile, dim_index)

    profile_dims = profile["dimensions"]
    sections: list[str] = []

    # Always include preamble first
    preamble_path = blocks_dir / "_preamble.md"
    if preamble_path.exists():
        preamble = preamble_path.read_text().strip()
        if preamble:
            sections.append(preamble)

    # Process each category in schema-defined order
    satisfied: set[str] = set()

    for category in schema["categories"]:
        category_blocks: list[str] = []

        for dim_spec in category["dimensions"]:
            dim_name = dim_spec["name"]

            if dim_name in satisfied:
                continue

            value = profile_dims[dim_name]
            meta, body = _load_block(blocks_dir, dim_name, value)

            # Mark covered dimensions
            covers = meta.get("covers", [])
            if covers:
                satisfied.update(covers)
            satisfied.add(dim_name)

            body = body.strip()
            if body:
                category_blocks.append(body)

        if category_blocks:
            heading = f"### {category['heading']}"
            sections.append(heading + "\n\n" + "\n\n".join(category_blocks))

    return "\n\n".join(sections) + "\n"
