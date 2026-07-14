# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from deepset_mcp.tools import skills
from deepset_mcp.tools.skills import _build_docstring, _discover_skills, _parse_skill_file, load_skill


@pytest.fixture
def skills_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(skills, "SKILLS_DIR", tmp_path)
    return tmp_path


def _write_skill(directory: Path, filename: str, name: str, description: str, body: str = "content") -> Path:
    path = directory / filename
    path.write_text(f"---\nname: {name}\ndescription: {description}\n---\n\n{body}\n", encoding="utf-8")
    return path


class TestParseSkillFile:
    def test_parses_frontmatter(self, tmp_path: Path) -> None:
        path = _write_skill(tmp_path, "foo.md", name="foo-skill", description="Does foo things.")

        name, description = _parse_skill_file(path)

        assert name == "foo-skill"
        assert description == "Does foo things."

    def test_falls_back_to_file_stem_without_frontmatter(self, tmp_path: Path) -> None:
        path = tmp_path / "plain.md"
        path.write_text("just some content\n", encoding="utf-8")

        name, description = _parse_skill_file(path)

        assert name == "plain"
        assert description == ""


class TestDiscoverSkills:
    def test_returns_empty_dict_when_dir_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(skills, "SKILLS_DIR", tmp_path / "does-not-exist")

        assert _discover_skills() == {}

    def test_discovers_all_skill_files(self, skills_dir: Path) -> None:
        _write_skill(skills_dir, "a.md", name="skill-a", description="First skill.")
        _write_skill(skills_dir, "b.md", name="skill-b", description="Second skill.")

        discovered = _discover_skills()

        assert set(discovered.keys()) == {"skill-a", "skill-b"}
        assert discovered["skill-a"][0] == "First skill."


class TestLoadSkill:
    @pytest.mark.asyncio
    async def test_returns_skill_content(self, skills_dir: Path) -> None:
        _write_skill(skills_dir, "foo.md", name="foo-skill", description="Does foo things.", body="# Foo\n\nDo foo.")

        result = await load_skill("foo-skill")

        assert "# Foo" in result
        assert "Do foo." in result

    @pytest.mark.asyncio
    async def test_unknown_skill_returns_error_with_available_skills(self, skills_dir: Path) -> None:
        _write_skill(skills_dir, "foo.md", name="foo-skill", description="Does foo things.")

        result = await load_skill("does-not-exist")

        assert "Error" in result
        assert "does-not-exist" in result
        assert "foo-skill" in result

    @pytest.mark.asyncio
    async def test_no_skills_available_error_message(self, skills_dir: Path) -> None:
        result = await load_skill("does-not-exist")

        assert "Available skills: none" in result


class TestBuildDocstring:
    def test_lists_skill_names_and_descriptions(self, skills_dir: Path) -> None:
        _write_skill(skills_dir, "foo.md", name="foo-skill", description="Does foo things.")

        docstring = _build_docstring()

        assert "foo-skill" in docstring
        assert "Does foo things." in docstring

    def test_bundled_custom_code_skill_is_discoverable(self) -> None:
        """The real, bundled `custom-code` skill should be discoverable without monkeypatching."""
        discovered = _discover_skills()

        assert "custom-code" in discovered
