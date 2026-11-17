"""Reads translation files (.po) and compiles them (.mo), in pure Python.

Django reads translations from compiled .mo files. Its own command for that,
`compilemessages`, needs the GNU gettext programs, which Windows does not
have. This small module does the same job without installing anything.

Supported: `msgctxt`, `msgid`, `msgstr`, plural forms (`msgid_plural`,
`msgstr[0]`, `msgstr[1]`...), comments and strings split over several lines.

A plural entry is kept the way .mo files store it: the original is
"singular\\0plural" and the translation "form 0\\0form 1".
"""
import re
import struct
from pathlib import Path

_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}
_KEYWORD_LINE = re.compile(r'^(msgctxt|msgid_plural|msgid|msgstr(?:\[\d+\])?)\s+"(.*)"\s*$')
_CONTINUATION_LINE = re.compile(r'^"(.*)"\s*$')


def _unescape(text: str) -> str:
    return re.sub(r"\\(.)", lambda match: _ESCAPES.get(match[1], match[1]), text)


def parse_po(text: str) -> dict[tuple[str | None, str], str]:
    """Return {(context, original): translation} for every entry in the file.

    The header (the entry with an empty original) is included under ("", "").
    A plural entry with any form left empty counts as untranslated ("").
    """
    messages: dict[tuple[str | None, str], str] = {}
    entry: dict[str, str] = {}
    current = None

    def finish_entry():
        if "msgid" in entry:
            original = entry["msgid"]
            if "msgid_plural" in entry:
                original += "\x00" + entry["msgid_plural"]
                forms = [entry[key] for key in sorted(k for k in entry if k.startswith("msgstr["))]
                translation = "\x00".join(forms) if forms and all(forms) else ""
            else:
                translation = entry.get("msgstr", "")
            messages[(entry.get("msgctxt"), original)] = translation
        entry.clear()

    for number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if match := _KEYWORD_LINE.match(line):
            keyword, value = match[1], _unescape(match[2])
            if keyword == "msgctxt" or (keyword == "msgid" and "msgid" in entry):
                finish_entry()
            entry[keyword] = value
            current = keyword
        elif (match := _CONTINUATION_LINE.match(line)) and current:
            entry[current] += _unescape(match[1])
        else:
            raise ValueError(f"line {number} of the .po file is not understood: {line}")
    finish_entry()
    return messages


def build_mo(messages: dict[tuple[str | None, str], str]) -> bytes:
    """Build the binary contents of a .mo file. Untranslated entries are left out."""
    entries = []
    for (context, original), translation in messages.items():
        if not translation:
            continue
        key = original if context is None else f"{context}\x04{original}"
        entries.append((key.encode("utf-8"), translation.encode("utf-8")))
    entries.sort()

    count = len(entries)
    keys_table_start = 7 * 4
    values_table_start = keys_table_start + count * 8
    data_start = values_table_start + count * 8

    keys_table, values_table, data = [], [], b""
    for key, _value in entries:
        keys_table.append((len(key), data_start + len(data)))
        data += key + b"\x00"
    for _key, value in entries:
        values_table.append((len(value), data_start + len(data)))
        data += value + b"\x00"

    header = struct.pack(
        "<Iiiiiii", 0x950412DE, 0, count, keys_table_start, values_table_start, 0, 0
    )
    tables = b"".join(struct.pack("<ii", length, offset) for length, offset in keys_table)
    tables += b"".join(struct.pack("<ii", length, offset) for length, offset in values_table)
    return header + tables + data


def compile_po_file(po_path: Path) -> Path:
    """Write the .mo file next to the given .po file and return its path."""
    mo_path = po_path.with_suffix(".mo")
    mo_path.write_bytes(build_mo(parse_po(po_path.read_text(encoding="utf-8"))))
    return mo_path
