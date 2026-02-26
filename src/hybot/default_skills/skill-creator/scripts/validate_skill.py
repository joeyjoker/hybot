#!/usr/bin/env python3
"""Validate an agno skill directory structure and SKILL.md content."""

import json
import sys
from pathlib import Path


def validate(skill_dir: str) -> dict:
    """Validate a skill directory, return result dict."""
    try:
        from agno.skills.validator import validate_skill_directory

        errors = validate_skill_directory(Path(skill_dir))
        if errors:
            return {"valid": False, "errors": errors}
        return {"valid": True, "message": f"Skill '{Path(skill_dir).name}' is valid."}
    except ImportError:
        # Fallback: basic validation without agno
        return _basic_validate(skill_dir)


def _basic_validate(skill_dir: str) -> dict:
    """Basic validation without agno dependency."""
    import re

    errors = []
    skill_path = Path(skill_dir)

    if not skill_path.exists():
        return {"valid": False, "errors": [f"Path does not exist: {skill_dir}"]}

    if not skill_path.is_dir():
        return {"valid": False, "errors": [f"Not a directory: {skill_dir}"]}

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return {"valid": False, "errors": ["Missing required file: SKILL.md"]}

    content = skill_md.read_text(encoding="utf-8")

    if not content.startswith("---"):
        errors.append("SKILL.md must start with YAML frontmatter (---)")
        return {"valid": False, "errors": errors}

    parts = content.split("---", 2)
    if len(parts) < 3:
        errors.append("SKILL.md frontmatter not properly closed with ---")
        return {"valid": False, "errors": errors}

    try:
        import yaml
        metadata = yaml.safe_load(parts[1])
    except Exception as e:
        return {"valid": False, "errors": [f"Invalid YAML in frontmatter: {e}"]}

    if not isinstance(metadata, dict):
        errors.append("Frontmatter must be a YAML mapping")
        return {"valid": False, "errors": errors}

    # Check required fields
    if "name" not in metadata:
        errors.append("Missing required field: name")
    else:
        name = metadata["name"]
        if not isinstance(name, str) or not name.strip():
            errors.append("Field 'name' must be a non-empty string")
        else:
            if len(name) > 64:
                errors.append(f"Skill name exceeds 64 character limit ({len(name)} chars)")
            if name != name.lower():
                errors.append("Skill name must be lowercase")
            if name.startswith("-") or name.endswith("-"):
                errors.append("Skill name cannot start or end with a hyphen")
            if "--" in name:
                errors.append("Skill name cannot contain consecutive hyphens")
            if not all(c.isalnum() or c == "-" for c in name):
                errors.append("Skill name contains invalid characters")
            if skill_path.name != name:
                errors.append(f"Directory name '{skill_path.name}' must match skill name '{name}'")

    if "description" not in metadata:
        errors.append("Missing required field: description")
    elif not isinstance(metadata["description"], str) or not metadata["description"].strip():
        errors.append("Field 'description' must be a non-empty string")
    elif len(metadata["description"]) > 1024:
        errors.append("Description exceeds 1024 character limit")

    # Check for unexpected fields
    allowed = {"name", "description", "license", "compatibility", "allowed-tools", "metadata"}
    extra = set(metadata.keys()) - allowed
    if extra:
        errors.append(f"Unexpected fields: {', '.join(sorted(extra))}")

    if errors:
        return {"valid": False, "errors": errors}
    return {"valid": True, "message": f"Skill '{skill_path.name}' is valid."}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"valid": False, "errors": ["Usage: validate_skill.py <skill-directory>"]}))
        sys.exit(1)

    result = validate(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["valid"] else 1)
