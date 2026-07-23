"""Drift protection for the templates embedded in commands/init-playbook.md.

A deterministic, standard-library-only parser extracts every embedded
template using the `## File N/11` section headers and the four-backtick
outer fences (feasibility finding F3: inner template content legitimately
contains three-backtick fences, so three backticks must never be used as
the outer delimiter). The tests then prove — byte for byte — that the
generated copies of the role-first playbook sources cannot silently drift
from their roots. No provider is invoked, no network is used, and the
repository is never modified.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from typing import NamedTuple

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
INIT_PLAYBOOK = PLUGIN_ROOT / "commands" / "init-playbook.md"

EXPECTED_TOTAL = 11

# Embedded copies that must stay byte-identical to their root sources.
SYNCED_SOURCES = (
    "docs/playbook/README.md",
    "docs/playbook/orchestration.md",
    "docs/playbook/task-routing.md",
    "docs/playbook/agent-routing.json",
)

_HEADER_RE = re.compile(r"^## File (\d+)/(\d+): `([^`]+)`\s*$")
_OPEN_FENCE_RE = re.compile(r"^````([A-Za-z0-9_-]*)$")
_CLOSE_FENCE = "````"
_PATH_RE = re.compile(r"^docs/playbook/[A-Za-z0-9._-]+$")


class EmbeddedTemplate(NamedTuple):
    ordinal: int
    declared_total: int
    target_path: str
    fence_language: str
    embedded_bytes: bytes


class TemplateParseError(AssertionError):
    """Raised when the embedded-template inventory violates its contract."""


def parse_embedded_templates(data: bytes) -> "dict[str, EmbeddedTemplate]":
    """Parse init-playbook.md bytes into {target_path: EmbeddedTemplate}.

    Fails closed on: wrong section count, non-contiguous ordinals,
    inconsistent declared totals, duplicate or unrecognizable target
    paths, missing/ambiguous four-backtick fences, and embedded content
    without a trailing newline.
    """
    text = data.decode("utf-8")
    lines = text.splitlines(keepends=True)

    # Locate section headers.
    headers = []  # (line_index, ordinal, total, path)
    for index, line in enumerate(lines):
        match = _HEADER_RE.match(line.rstrip("\n"))
        if match:
            headers.append(
                (index, int(match.group(1)), int(match.group(2)), match.group(3))
            )

    if len(headers) != EXPECTED_TOTAL:
        raise TemplateParseError(
            "expected %d File sections, found %d" % (EXPECTED_TOTAL, len(headers))
        )

    templates: "dict[str, EmbeddedTemplate]" = {}
    for position, (start, ordinal, total, path) in enumerate(headers):
        if total != EXPECTED_TOTAL:
            raise TemplateParseError(
                "section %d declares total %d, expected %d" % (ordinal, total, EXPECTED_TOTAL)
            )
        if ordinal != position + 1:
            raise TemplateParseError(
                "non-contiguous ordinal: got %d at position %d" % (ordinal, position + 1)
            )
        if not _PATH_RE.match(path):
            raise TemplateParseError("unrecognizable target path: %r" % path)
        if path in templates:
            raise TemplateParseError("duplicate target path: %s" % path)

        end = headers[position + 1][0] if position + 1 < len(headers) else len(lines)
        section = lines[start + 1 : end]

        fence_indices = [
            i for i, line in enumerate(section) if line.rstrip("\n").startswith(_CLOSE_FENCE)
        ]
        if len(fence_indices) != 2:
            raise TemplateParseError(
                "section %s must contain exactly one four-backtick fence pair, "
                "found %d fence lines" % (path, len(fence_indices))
            )
        open_index, close_index = fence_indices
        open_match = _OPEN_FENCE_RE.match(section[open_index].rstrip("\n"))
        if not open_match:
            raise TemplateParseError("section %s has a malformed opening fence" % path)
        if section[close_index].rstrip("\n") != _CLOSE_FENCE:
            raise TemplateParseError("section %s has a malformed closing fence" % path)

        embedded_text = "".join(section[open_index + 1 : close_index])
        embedded = embedded_text.encode("utf-8")
        if not embedded.endswith(b"\n"):
            raise TemplateParseError("section %s content lacks a trailing newline" % path)

        templates[path] = EmbeddedTemplate(
            ordinal=ordinal,
            declared_total=total,
            target_path=path,
            fence_language=open_match.group(1),
            embedded_bytes=embedded,
        )
    return templates


def load_templates() -> "dict[str, EmbeddedTemplate]":
    return parse_embedded_templates(INIT_PLAYBOOK.read_bytes())


class FileInventoryTests(unittest.TestCase):
    def setUp(self):
        self.doc_bytes = INIT_PLAYBOOK.read_bytes()
        self.templates = parse_embedded_templates(self.doc_bytes)

    def test_exactly_eleven_sections_with_contiguous_ordinals(self):
        self.assertEqual(len(self.templates), EXPECTED_TOTAL)
        ordinals = sorted(t.ordinal for t in self.templates.values())
        self.assertEqual(ordinals, list(range(1, EXPECTED_TOTAL + 1)))
        self.assertEqual(
            {t.declared_total for t in self.templates.values()}, {EXPECTED_TOTAL}
        )

    def test_target_paths_unique_and_agent_routing_present(self):
        paths = [t.target_path for t in self.templates.values()]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertIn("docs/playbook/agent-routing.json", self.templates)
        self.assertEqual(
            self.templates["docs/playbook/agent-routing.json"].fence_language, "json"
        )

    def test_no_stale_ten_file_counting_remains(self):
        text = self.doc_bytes.decode("utf-8")
        self.assertIsNone(re.search(r"File \d+/10\b", text))
        self.assertNotIn("10 files total", text)
        self.assertIn("11 files total", text)


class ByteForByteSyncTests(unittest.TestCase):
    def setUp(self):
        self.templates = load_templates()

    def test_synced_sources_are_byte_identical_to_roots(self):
        for rel_path in SYNCED_SOURCES:
            with self.subTest(source=rel_path):
                embedded = self.templates[rel_path].embedded_bytes
                source = (PLUGIN_ROOT / rel_path).read_bytes()
                self.assertEqual(
                    embedded,
                    source,
                    "embedded copy of %s drifted from its root source" % rel_path,
                )


class DriftMutationTests(unittest.TestCase):
    """Prove the guard actually fails on drift, not merely that bytes match today."""

    def setUp(self):
        self.templates = load_templates()

    def assert_mismatch(self, mutated: bytes, source_path: str):
        source = (PLUGIN_ROOT / source_path).read_bytes()
        self.assertNotEqual(mutated, source)

    def test_single_character_deletion_is_detected(self):
        source_path = "docs/playbook/README.md"
        embedded = self.templates[source_path].embedded_bytes
        middle = len(embedded) // 2
        self.assert_mismatch(embedded[:middle] + embedded[middle + 1 :], source_path)

    def test_whitespace_change_is_detected(self):
        source_path = "docs/playbook/orchestration.md"
        embedded = self.templates[source_path].embedded_bytes
        self.assertIn(b" ", embedded)
        index = embedded.index(b" ")
        self.assert_mismatch(
            embedded[:index] + b"  " + embedded[index + 1 :], source_path
        )

    def test_removed_trailing_newline_is_detected(self):
        source_path = "docs/playbook/task-routing.md"
        embedded = self.templates[source_path].embedded_bytes
        self.assertTrue(embedded.endswith(b"\n"))
        self.assert_mismatch(embedded[:-1], source_path)

    def test_routing_value_change_is_detected(self):
        source_path = "docs/playbook/agent-routing.json"
        embedded = self.templates[source_path].embedded_bytes
        self.assertIn(b'"codex_cli"', embedded)
        mutated = embedded.replace(b'"codex_cli"', b'"claude_cli"', 1)
        self.assertNotEqual(mutated, embedded)
        self.assert_mismatch(mutated, source_path)


class FenceRobustnessTests(unittest.TestCase):
    """The four-backtick outer fence must survive inner three-backtick fences."""

    def setUp(self):
        self.templates = load_templates()
        self.orchestration = self.templates["docs/playbook/orchestration.md"]

    def test_inner_three_backtick_fences_survive_extraction(self):
        embedded = self.orchestration.embedded_bytes
        self.assertIn(b"```text", embedded)
        self.assertGreaterEqual(embedded.count(b"```"), 4)

    def test_content_after_first_inner_fence_is_not_truncated(self):
        embedded = self.orchestration.embedded_bytes
        first_inner = embedded.index(b"```")
        tail = embedded[first_inner:]
        # Sections that appear far beyond the first inner fence pair.
        self.assertIn("## 統籌七律".encode("utf-8"), tail)
        self.assertIn("## 與專案規範的關係".encode("utf-8"), embedded)

    def test_outer_fences_are_not_part_of_embedded_bytes(self):
        for template in self.templates.values():
            with self.subTest(source=template.target_path):
                self.assertNotIn(b"````", template.embedded_bytes)
                self.assertFalse(template.embedded_bytes.startswith(b"```"))


class NoOverwriteContractTests(unittest.TestCase):
    """Static contract markers for the generation behavior of init-playbook."""

    def setUp(self):
        self.text = INIT_PLAYBOOK.read_text(encoding="utf-8")

    def test_skip_and_never_overwrite_markers(self):
        self.assertIn("**Exists = skip, don't overwrite**", self.text)
        self.assertIn(
            "Never overwrite, replace, merge, append, or auto-repair an existing "
            "target file",
            self.text,
        )

    def test_agent_routing_gets_the_same_no_overwrite_rule(self):
        self.assertIn(
            "The same no-overwrite rule applies to `docs/playbook/agent-routing.json`",
            self.text,
        )
        self.assertIn("SKIP — existing file preserved", self.text)

    def test_completion_report_contract(self):
        self.assertIn("`CREATED` or `SKIPPED — already exists`", self.text)
        self.assertIn("created count", self.text)
        self.assertIn("skipped count", self.text)
        self.assertIn("total = 11", self.text)
        self.assertIn("a skipped file is never a failure", self.text)


class GeneratedPathSafetyTests(unittest.TestCase):
    def setUp(self):
        self.templates = load_templates()

    def test_all_target_paths_are_safe_repository_relative_playbook_paths(self):
        paths = [t.target_path for t in self.templates.values()]
        self.assertEqual(len(paths), EXPECTED_TOTAL)
        self.assertEqual(len(paths), len(set(paths)))
        for path in paths:
            with self.subTest(path=path):
                self.assertFalse(path.startswith("/"))
                self.assertNotIn("..", Path(path).parts)
                self.assertTrue(path.startswith("docs/playbook/"))
                self.assertEqual(Path(path).parent.as_posix(), "docs/playbook")


if __name__ == "__main__":
    unittest.main()
