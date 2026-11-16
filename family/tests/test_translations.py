"""Translations: the compiler, and that no interface text was left untranslated."""
import ast
import gettext
import io
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from family.pofiles import build_mo, parse_po

PROJECT_DIR = Path(settings.BASE_DIR)
LOCALES = ("pt_BR", "es")
TRANSLATION_FUNCTIONS = {"_", "gettext", "gettext_lazy", "gettext_noop"}
TEMPLATE_TAG = re.compile(r"""{%\s*(?:translate|trans)\s+(?:"([^"]*)"|'([^']*)')""")

SAMPLE_PO = '''
# A comment.
msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\\n"

msgid "Tree"
msgstr "Árvore"

msgid "A long text "
"in two lines"
msgstr "Um texto longo "
"em duas linhas"

msgid "She said \\"hi\\""
msgstr "Ela disse \\"oi\\""

msgctxt "noun"
msgid "Union"
msgstr "União"

msgid "Not translated yet"
msgstr ""
'''


def po_path(locale: str) -> Path:
    return PROJECT_DIR / "locale" / locale / "LC_MESSAGES" / "django.po"


def texts_in_python_files() -> set[str]:
    """Every text passed to a translation function in the project's code."""
    found = set()
    for folder in ("family", "config"):
        for path in (PROJECT_DIR / folder).rglob("*.py"):
            if "tests" in path.parts or "migrations" in path.parts:
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if not (isinstance(node, ast.Call) and node.args):
                    continue
                name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                first = node.args[0]
                if (
                    name in TRANSLATION_FUNCTIONS
                    and isinstance(first, ast.Constant)
                    and isinstance(first.value, str)
                ):
                    found.add(first.value)
    return found


def texts_in_templates() -> set[str]:
    """Every text inside a {% translate %} tag."""
    found = set()
    for path in (PROJECT_DIR / "family" / "templates").rglob("*.html"):
        for match in TEMPLATE_TAG.finditer(path.read_text(encoding="utf-8")):
            found.add(match[1] if match[1] is not None else match[2])
    return found


class PoCompilerTests(SimpleTestCase):
    def setUp(self):
        self.messages = parse_po(SAMPLE_PO)

    def test_reads_simple_entries(self):
        self.assertEqual(self.messages[(None, "Tree")], "Árvore")

    def test_joins_texts_split_over_several_lines(self):
        self.assertEqual(
            self.messages[(None, "A long text in two lines")],
            "Um texto longo em duas linhas",
        )

    def test_understands_escaped_quotes(self):
        self.assertEqual(self.messages[(None, 'She said "hi"')], 'Ela disse "oi"')

    def test_keeps_the_context_of_an_entry(self):
        self.assertEqual(self.messages[("noun", "Union")], "União")

    def test_compiled_file_is_read_by_python(self):
        catalog = gettext.GNUTranslations(io.BytesIO(build_mo(self.messages)))

        self.assertEqual(catalog.gettext("Tree"), "Árvore")
        self.assertEqual(catalog.pgettext("noun", "Union"), "União")
        self.assertEqual(catalog.gettext('She said "hi"'), 'Ela disse "oi"')

    def test_untranslated_entries_fall_back_to_the_original(self):
        catalog = gettext.GNUTranslations(io.BytesIO(build_mo(self.messages)))

        self.assertEqual(catalog.gettext("Not translated yet"), "Not translated yet")

    def test_line_that_is_not_understood_is_an_error(self):
        with self.assertRaises(ValueError):
            parse_po('msgid "a"\nmsgstr "b"\nsomething else\n')


class TranslationFilesTests(SimpleTestCase):
    def test_the_project_has_texts_to_translate(self):
        self.assertIn("Tree", texts_in_templates())
        self.assertIn("Family", texts_in_python_files())

    def test_every_interface_text_is_translated(self):
        needed = texts_in_python_files() | texts_in_templates()
        for locale in LOCALES:
            messages = parse_po(po_path(locale).read_text(encoding="utf-8"))
            translated = {original for (_ctx, original), text in messages.items() if text}
            with self.subTest(locale=locale):
                self.assertEqual(sorted(needed - translated), [])

    def test_no_translation_is_left_over_from_removed_texts(self):
        needed = texts_in_python_files() | texts_in_templates()
        for locale in LOCALES:
            messages = parse_po(po_path(locale).read_text(encoding="utf-8"))
            listed = {original for (_ctx, original) in messages if original}
            with self.subTest(locale=locale):
                self.assertEqual(sorted(listed - needed), [])

    def test_placeholders_are_the_same_in_the_translation(self):
        placeholder = re.compile(r"%\(\w+\)[sd]|%[sd]|\{\w*\}")
        for locale in LOCALES:
            messages = parse_po(po_path(locale).read_text(encoding="utf-8"))
            for (_ctx, original), text in messages.items():
                if not original or not text:
                    continue
                with self.subTest(locale=locale, original=original):
                    self.assertEqual(
                        sorted(placeholder.findall(original)),
                        sorted(placeholder.findall(text)),
                    )

    def test_compiled_files_are_up_to_date(self):
        for locale in LOCALES:
            path = po_path(locale)
            expected = build_mo(parse_po(path.read_text(encoding="utf-8")))
            with self.subTest(locale=locale):
                self.assertTrue(
                    path.with_suffix(".mo").is_file(),
                    "Run: python manage.py compile_translations",
                )
                self.assertEqual(
                    path.with_suffix(".mo").read_bytes(),
                    expected,
                    "Run: python manage.py compile_translations",
                )
