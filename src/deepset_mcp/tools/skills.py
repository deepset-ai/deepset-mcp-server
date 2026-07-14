# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""Tool for loading skill guides bundled with the server."""

from pathlib import Path

import yaml

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def _parse_skill_file(path: Path) -> tuple[str, str]:
    """Parses the name and description from a skill file's YAML frontmatter.

    :param path: Path to the skill markdown file.
    :returns: A tuple of (name, description). Falls back to the file stem as name and an
        empty description if the frontmatter is missing or malformed.
    """
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if text.startswith("---") and len(parts) >= 3:
        metadata = yaml.safe_load(parts[1]) or {}
        name = str(metadata.get("name", path.stem))
        description = str(metadata.get("description", ""))
        return name, description
    return path.stem, ""


def _discover_skills() -> dict[str, tuple[str, Path]]:
    """Discovers all skill files bundled with the server.

    :returns: A mapping of skill name to (description, file path).
    """
    if not SKILLS_DIR.is_dir():
        return {}

    skills: dict[str, tuple[str, Path]] = {}
    for path in sorted(SKILLS_DIR.glob("*.md")):
        name, description = _parse_skill_file(path)
        skills[name] = (description, path)
    return skills


def _build_docstring() -> str:
    """Builds the `load_skill` docstring, listing all currently bundled skills.

    :returns: The docstring text.
    """
    skills = _discover_skills()
    if skills:
        skills_list = "\n".join(
            f"    - {name}: {description}" for name, (description, _) in sorted(skills.items())
        )
    else:
        skills_list = "    (no skills are currently available)"

    return (
        "Loads the full content of a bundled skill guide by name.\n\n"
        "Use this tool to read the step-by-step instructions for a specific skill supported by this server.\n\n"
        "Available skills:\n"
        f"{skills_list}\n\n"
        ":param skill_name: The name of the skill to load (see the list above).\n"
        ":returns: The skill's markdown content, or an error message listing available skills if not found.\n"
    )


async def load_skill(skill_name: str) -> str:
    """Loads the full content of a bundled skill guide by name.

    This docstring is replaced at import time with a dynamically generated version
    that lists every skill currently bundled with the server (see `_build_docstring`).

    :param skill_name: The name of the skill to load.
    :returns: The skill's markdown content, or an error message if not found.
    """
    skills = _discover_skills()

    match = skills.get(skill_name)
    if match is None:
        available = ", ".join(sorted(skills)) or "none"
        return f"Error: Skill '{skill_name}' not found. Available skills: {available}"

    _, path = match
    return path.read_text(encoding="utf-8")


load_skill.__doc__ = _build_docstring()
