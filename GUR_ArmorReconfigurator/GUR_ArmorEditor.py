#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUR - Armor Reconfigurator
==========================
Dark-themed tkinter editor for the GUR armor patch:

    updated_mod/Stalker2/Content/GameLite/GameData/ItemPrototypes/GUR_Armor_Patch.cfg

STALKER 2 2.0 ships ItemPrototypes only as a binarized ItemPrototypes.cfg.bin
(base game and DLC PreOrder/Deluxe/Ultimate). The loader merges every plain
*.cfg file from the matching ItemPrototypes/ folder, so patches go there and
are matched by section name. Blocks use {bpatch} and only the fields that
differ from vanilla are written.

Usage:
    python GUR_ArmorEditor.py             # GUI
    python GUR_ArmorEditor.py --selftest  # parser/save self-test
    python GUR_ArmorEditor.py --smoke     # build the UI briefly and exit
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

if getattr(sys, "frozen", False):
    ROOT = os.path.dirname(os.path.abspath(sys.executable))
else:
    ROOT = os.path.dirname(os.path.abspath(__file__))
UPDATED_DIR = os.path.join(ROOT, "updated_mod")
PATCH_FILENAME = "GUR_Armor_Patch.cfg"
SOURCE_DIRS = {
    "base": "Stalker2/Content/GameLite/GameData/ItemPrototypes",
    "PreOrder": "Stalker2/Content/GameLite/DLCGameData/PreOrder/ItemPrototypes",
    "Deluxe": "Stalker2/Content/GameLite/DLCGameData/Deluxe/ItemPrototypes",
    "Ultimate": "Stalker2/Content/GameLite/DLCGameData/Ultimate/ItemPrototypes",
}
SOURCE_KEYS = list(SOURCE_DIRS)
PAK_NAME = "GUR_ArmorReconfigurator_P.pak"
PAK_PATH = os.path.join(ROOT, PAK_NAME)
SETTINGS_PATH = os.path.join(ROOT, "GUR_Armor.settings")
VANILLA_ARMOR = os.path.join(ROOT, "data", "vanilla_armor.cfg")
META_PATH = os.path.join(ROOT, "data", "armor_meta.json")


def patch_path(source: str) -> str:
    return os.path.join(UPDATED_DIR, *SOURCE_DIRS[source].split("/"), PATCH_FILENAME)


def patch_entry(source: str) -> str:
    return os.path.relpath(patch_path(source), UPDATED_DIR).replace(os.sep, "/")

# --- theme -----------------------------------------------------------------
BG = "#14171c"
PANEL = "#1b2027"
PANE2 = "#222a34"
FIELD = "#0e1216"
FG = "#e8e6e3"
MUTED = "#98a2b3"
ACCENT = "#d0a84c"
BORDER = "#333c48"
SEL = "#3a4654"
INK = "#17140a"

# --- editable stats --------------------------------------------------------
PROT_FIELDS = [
    ("Protection.Strike", "prot_strike"),
    ("Protection.Burn", "prot_burn"),
    ("Protection.Shock", "prot_shock"),
    ("Protection.ChemicalBurn", "prot_chem"),
    ("Protection.Radiation", "prot_rad"),
    ("Protection.PSY", "prot_psy"),
    ("Protection.Fall", "prot_fall"),
]
EDIT_FIELDS = ["BaseDurability"] + [key for key, _label in PROT_FIELDS]
PROT_ORDER = [key.split(".", 1)[1] for key, _label in PROT_FIELDS]
CATEGORY_KEYS = ["all", "armor", "helmet"]
SORT_KEYS = ["alpha", "sid", "modified"]

FACTION_KEYS = [
    "all", "neutral", "bandit", "mercenaries", "military", "scientific",
    "svoboda", "dolg", "monolith", "varta", "spark",
]
FACTION_LABELS = {
    "neutral": ("Neutral", "Нейтрали"),
    "bandit": ("Bandits", "Бандити"),
    "mercenaries": ("Mercenaries", "Найманці"),
    "military": ("Military", "Військові"),
    "scientific": ("Scientists", "Науковці"),
    "svoboda": ("Freedom", "Свобода"),
    "dolg": ("Duty", "Долг"),
    "monolith": ("Monolith", "Моноліт"),
    "varta": ("Ward", "Варта"),
    "spark": ("Spark", "Іскра"),
}

TRANSLATIONS = {
    "en": {
        "title": "GUR - Armor Reconfigurator",
        "subtitle": "Armor & helmets for STALKER 2 (2.0+)",
        "search": "Search:", "search_hint": "name or SID",
        "category": "Category:", "sort": "Sort:", "faction": "Faction:",
        "col_name": "Armor / helmet", "col_kind": "Type", "col_faction": "Faction",
        "sort_alpha": "A-Z", "sort_sid": "SID", "sort_modified": "Modified first",
        "cat_all": "All", "cat_armor": "Armor", "cat_helmet": "Helmets",
        "fac_all": "All factions", "meta_unique": "Unique item",
        "language": "Language:",
        "list_hint": "{shown} of {total} shown",
        "select_item": "Select an armor piece",
        "group_prot": "Protection",
        "prot_strike": "Physical (Strike)",
        "prot_burn": "Thermal (Burn)",
        "prot_shock": "Electrical (Shock)",
        "prot_chem": "Chemical (ChemicalBurn)",
        "prot_rad": "Radiation",
        "prot_psy": "PSI (PSY)",
        "prot_fall": "Fall",
        "field_dur": "Durability (BaseDurability)",
        "dur_hint": "Maximum durability; higher = wears out slower per point of damage.",
        "status_vanilla": "vanilla, no patch block",
        "status_patch": "patch block present",
        "kind_armor": "Armor",
        "kind_helmet": "Helmet",
        "btn_reload": "Reload patch file",
        "btn_reset": "Reset to Vanilla (Remove Patch)",
        "tip_reset": "Remove this item's {bpatch} block so it uses 100% vanilla stats.",
        "mods_folder": "Game ~mods folder:",
        "browse": "Browse…",
        "save_cfg": "Save .cfg only",
        "save_pack": "Save & Pack to .pak",
        "shortcut": "Ctrl+S packs, Ctrl+Shift+S saves only",
        "notes": (
            "Only changed fields are written, so untouched items keep the game's\n"
            "own values. NPC armor (ProtectionNPC) is never modified. Patches\n"
            "land in ItemPrototypes/GUR_Armor_Patch.cfg next to the base and\n"
            "DLC ItemPrototypes.cfg.bin files as {bpatch} overlays."
        ),
        "status_ready": "Ready.",
        "status_loaded": "Loaded {count} armor pieces and helmets (vanilla + patch).",
        "status_saved": "Saved {count} changed section(s).",
        "status_reset": "{name} is vanilla again.",
        "status_nochange": "No changes to save.",
        "err_number": "{field}: {value} is not a number",
        "err_negative": "{field}: value must be 0 or greater",
        "dlg_invalid_title": "Invalid values",
        "dlg_invalid_msg": "Fix these values before saving:\n\n{errors}",
        "dlg_save_failed": "Save failed",
        "dlg_saved_title": "Saved",
        "dlg_saved_msg": "Patch saved to:\n{path}",
        "dlg_reset_title": "Reset to vanilla",
        "dlg_reset_msg": "Remove the patch block for {name} ({sid})?",
        "dlg_reload_title": "Discard changes?",
        "dlg_reload_msg": "Reload the patch file and discard unsaved edits?",
        "dlg_repak_missing_title": "repak.exe not found",
        "dlg_repak_missing_msg": "Put repak.exe next to this editor (or into the game's Paks folder) and try again.",
        "dlg_pack_failed_title": "Packing failed",
        "dlg_pack_failed_msg": "{error}\n\nYour .cfg was saved successfully.",
        "dlg_pack_ok_title": "Pack complete",
        "dlg_no_changes_title": "Nothing to pack",
        "dlg_no_changes_msg": "No armor differs from vanilla yet, so there is nothing to pack.\nEdit at least one item and try again.",
        "pack_ok": "Armor patch packed and deployed.",
        "pack_archive": "Archive: {path}",
        "pack_entries": "Entries: {total} ({cfgs} cfg)",
        "pack_deployed": "Copied to: {path}",
        "pack_verified": "Verified SHA-256: {hash}…",
        "pack_shadow_disabled": "Disabled duplicate pak: {path}",
        "pack_thr_shadow_other": "Another mod ships this file too: {path}",
        "pack_copy_error": "\nCould not copy into ~mods: {error}",
        "pack_missing_folder": "Patch folder not found:\n{path}",
        "vanilla_missing": "Vanilla armor data not found:\n{path}\n\nKeep the data\\ folder next to the editor.",
        "notes_title": "Notes",
        "browse_title": "Choose the ~mods folder",
    },
    "uk": {
        "title": "GUR - Редактор броні",
        "subtitle": "Броня та шоломи для STALKER 2 (2.0+)",
        "search": "Пошук:", "search_hint": "назва або SID",
        "category": "Категорія:", "sort": "Сортування:", "faction": "Угрупування:",
        "col_name": "Броня / шолом", "col_kind": "Тип", "col_faction": "Угрупування",
        "sort_alpha": "А-Я", "sort_sid": "SID", "sort_modified": "Спочатку змінені",
        "cat_all": "Усі", "cat_armor": "Броня", "cat_helmet": "Шоломи",
        "fac_all": "Усі угрупування", "meta_unique": "Унікальний предмет",
        "language": "Мова:",
        "list_hint": "Показано {shown} з {total}",
        "select_item": "Виберіть броню або шолом",
        "group_prot": "Захист",
        "prot_strike": "Фізичний (Strike)",
        "prot_burn": "Термічний (Burn)",
        "prot_shock": "Електричний (Shock)",
        "prot_chem": "Хімічний (ChemicalBurn)",
        "prot_rad": "Радіація",
        "prot_psy": "Психічний (PSY)",
        "prot_fall": "Від падіння (Fall)",
        "field_dur": "Міцність (BaseDurability)",
        "dur_hint": "Максимальний запас міцності: що більше, то повільніше зношується.",
        "status_vanilla": "ваніль, блоку патча немає",
        "status_patch": "є блок патча",
        "kind_armor": "Броня",
        "kind_helmet": "Шолом",
        "btn_reload": "Перезавантажити файл патча",
        "btn_reset": "Скинути до ванілу (Видалити патч)",
        "tip_reset": "Видалити {bpatch}-блок цього предмета, щоб повернути 100% ванільні значення.",
        "mods_folder": "Тека ~mods гри:",
        "browse": "Огляд…",
        "save_cfg": "Зберегти лише .cfg",
        "save_pack": "Зберегти та запакувати в .pak",
        "shortcut": "Ctrl+S — пакування, Ctrl+Shift+S — лише збереження",
        "notes": (
            "До патча пишуться лише змінені поля, тож незаймані предмети\n"
            "залишаються як у грі. Захист НПС (ProtectionNPC) не змінюється.\n"
            "Патчі лежать у ItemPrototypes/GUR_Armor_Patch.cfg поруч із ванільними\n"
            "та DLC-файлами ItemPrototypes.cfg.bin як {bpatch}-накладки."
        ),
        "status_ready": "Готово.",
        "status_loaded": "Завантажено броні та шоломів: {count} (ваніль + патч).",
        "status_saved": "Збережено змінених секцій: {count}.",
        "status_reset": "{name} знову ванільна.",
        "status_nochange": "Немає змін для збереження.",
        "err_number": "{field}: {value} — не число",
        "err_negative": "{field}: значення має бути 0 або більше",
        "dlg_invalid_title": "Некоректні значення",
        "dlg_invalid_msg": "Виправте ці значення перед збереженням:\n\n{errors}",
        "dlg_save_failed": "Не вдалося зберегти",
        "dlg_saved_title": "Збережено",
        "dlg_saved_msg": "Патч збережено у:\n{path}",
        "dlg_reset_title": "Скинути до ванілу",
        "dlg_reset_msg": "Видалити блок патча для {name} ({sid})?",
        "dlg_reload_title": "Скасувати зміни?",
        "dlg_reload_msg": "Перезавантажити файл патча та скасувати незбережені зміни?",
        "dlg_repak_missing_title": "repak.exe не знайдено",
        "dlg_repak_missing_msg": "Покладіть repak.exe поруч із редактором (або в теку Paks гри) і спробуйте ще раз.",
        "dlg_pack_failed_title": "Не вдалося запакувати",
        "dlg_pack_failed_msg": "{error}\n\nФайл .cfg успішно збережено.",
        "dlg_pack_ok_title": "Пакування завершено",
        "dlg_no_changes_title": "Нічого пакувати",
        "dlg_no_changes_msg": "Поки жодна броня не відрізняється від ванілу — пакувати нічого.\nЗмініть хоча б один предмет і спробуйте ще раз.",
        "pack_ok": "Патч броні запаковано та задеплоєно.",
        "pack_archive": "Архів: {path}",
        "pack_entries": "Записів: {total} ({cfgs} cfg)",
        "pack_deployed": "Скопійовано в: {path}",
        "pack_verified": "Перевірено SHA-256: {hash}…",
        "pack_shadow_disabled": "Вимкнено дубль пakа: {path}",
        "pack_thr_shadow_other": "Інший мод також постачає цей файл: {path}",
        "pack_copy_error": "\nНе вдалося скопіювати в ~mods: {error}",
        "pack_missing_folder": "Теку патча не знайдено:\n{path}",
        "vanilla_missing": "Ванільні дані броні не знайдено:\n{path}\n\nТримайте теку data\\ поруч із редактором.",
        "notes_title": "Примітки",
        "browse_title": "Виберіть теку ~mods",
    },
}


def t(lang, key, **kwargs):
    text = TRANSLATIONS.get(lang, {}).get(key) or TRANSLATIONS["en"].get(key, key)
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return text


_HEADER_RE = re.compile(r"^([A-Za-z0-9_.]+)\s*:\s*struct\.begin\b")


class EditorError(Exception):
    pass


class CfgDoc:
    def __init__(self, path: str):
        self.path = path
        with open(path, "rb") as fh:
            raw = fh.read()
        self.bom = raw.startswith(b"\xef\xbb\xbf")
        text = raw.decode("utf-8-sig")
        self.eol = "\r\n" if "\r\n" in text else "\n"
        self.lines = text.replace("\r\n", "\n").split("\n")

    def save(self, path: str | None = None) -> None:
        path = path or self.path
        data = self.eol.join(self.lines).encode("utf-8")
        if self.bom:
            data = b"\xef\xbb\xbf" + data
        with open(path, "wb") as fh:
            fh.write(data)

    def sections(self) -> list["Section"]:
        out = []
        lines = self.lines
        n = len(lines)
        i = 0
        while i < n:
            match = _HEADER_RE.match(lines[i])
            if not match:
                i += 1
                continue
            depth = 0
            j = i
            while j < n:
                depth += lines[j].count("struct.begin") - lines[j].count("struct.end")
                if depth == 0:
                    break
                j += 1
            out.append(Section(self, match.group(1), i, min(j, n - 1)))
            i = j + 1
        return out


class Section:
    __slots__ = ("doc", "name", "start", "end")

    def __init__(self, doc: CfgDoc, name: str, start: int, end: int):
        self.doc = doc
        self.name = name
        self.start = start
        self.end = end

    def find_scalar(self, name: str, within=None):
        s, e = within if within else (self.start, self.end)
        pat = re.compile(r"^(\s*)" + re.escape(name) + r"\s*=\s*(.*?)\s*$")
        for i in range(s + 1, e):
            line = self.doc.lines[i]
            if line.lstrip().startswith("//"):
                continue
            match = pat.match(line)
            if match:
                return i, match.group(1), match.group(2)
        return None

    def find_struct(self, name: str, within=None):
        s, e = within if within else (self.start, self.end)
        pat = re.compile(r"^(\s*)" + re.escape(name) + r"\s*:\s*struct\.begin\b")
        for i in range(s + 1, e):
            if not pat.match(self.doc.lines[i]):
                continue
            depth = 0
            for j in range(i, e):
                depth += self.doc.lines[j].count("struct.begin") - self.doc.lines[j].count("struct.end")
                if depth == 0:
                    return i, j
        return None


def fmt_float(value) -> str:
    text = str(value).strip().replace(",", ".")
    number = float(text)
    if number == int(number) and abs(number) < 1e15:
        return f"{number:.1f}"
    return repr(number)


def _same_value(left: str, right: str) -> bool:
    try:
        return abs(float(left.replace(",", ".")) - float(right.replace(",", "."))) < 1e-6
    except (AttributeError, TypeError, ValueError):
        return (left or "").strip().casefold() == (right or "").strip().casefold()


def _to_number(mapping, key):
    try:
        return float(str(mapping.get(key, "")).replace(",", "."))
    except (TypeError, ValueError):
        return None


def load_meta(path=META_PATH):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    items = data.get("items") if isinstance(data, dict) else None
    return items if isinstance(items, dict) else {}


def _header_lines(source):
    folder = SOURCE_DIRS[source].split("Stalker2/Content/GameLite/", 1)[-1]
    kind = "vanilla" if source == "base" else "DLC"
    return [
        "// GUR - Armor Reconfigurator patch.",
        f"// Folder: {folder}/ next to the {kind} ItemPrototypes.cfg.bin.",
        "// Blocks are written as {bpatch} so only listed fields override vanilla.",
        "// ProtectionNPC is never touched. Generated by GUR_ArmorEditor.",
    ]


def ensure_patch_file(path, source):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(_header_lines(source)) + "\n")
    return path


def read_settings() -> dict:
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_settings(data: dict) -> None:
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
    except OSError:
        pass


def find_repak() -> str | None:
    for path in (
        os.path.join(ROOT, "repak.exe"),
        os.path.join(UPDATED_DIR, "repak.exe"),
        os.path.join(ROOT, "tools", "repak.exe"),
    ):
        if os.path.isfile(path):
            return path
    return shutil.which("repak")


def _run_hidden(cmd):
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    return subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=300, creationflags=flags,
    )


def sha256_file(path: str) -> str:
    import hashlib

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ArmorItem:
    def __init__(self, sid: str, meta: dict | None = None):
        self.sid = sid
        self.meta = meta or {}
        self.vanilla: dict[str, str] = {}
        self.values: dict[str, str] = {}
        self.patch: Section | None = None

    @property
    def kind(self) -> str:
        return "helmet" if self.sid.endswith("_Helmet") else "armor"

    @property
    def source(self) -> str:
        return self.meta.get("source", "base")

    @property
    def unique(self) -> bool:
        return bool(self.meta.get("unique"))

    def in_game_name(self, lang: str) -> str:
        name = self.meta.get("uk" if lang == "uk" else "en")
        return name or self.sid.replace("_", " ")

    def faction_key(self) -> str:
        return self.meta.get("faction", "neutral")

    def faction_label(self, lang: str) -> str:
        pair = FACTION_LABELS.get(self.faction_key())
        return pair[1 if lang == "uk" else 0] if pair else self.faction_key()

    def display(self, lang: str) -> str:
        name = self.in_game_name(lang)
        return ("\u2605 " + name) if self.unique else name


def _read_values(sec: Section) -> dict[str, str]:
    values: dict[str, str] = {}
    found = sec.find_scalar("BaseDurability")
    if found:
        values["BaseDurability"] = found[2]
    span = sec.find_struct("Protection")
    if span:
        for key in PROT_ORDER:
            hit = sec.find_scalar(key, within=span)
            if hit:
                values["Protection." + key] = hit[2]
    return values


def load_items(vanilla_path: str, patch_paths=None) -> list[ArmorItem]:
    if isinstance(patch_paths, str):
        patch_paths = {"base": patch_paths}
    meta = load_meta()
    vanilla_doc = CfgDoc(vanilla_path)
    items: list[ArmorItem] = []
    by_sid: dict[str, ArmorItem] = {}
    for sec in vanilla_doc.sections():
        item = ArmorItem(sec.name, meta.get(sec.name))
        item.vanilla = _read_values(sec)
        item.values = dict(item.vanilla)
        items.append(item)
        by_sid[sec.name] = item
    for source, path in (patch_paths or {}).items():
        if not path or not os.path.exists(path):
            continue
        for sec in CfgDoc(path).sections():
            item = by_sid.get(sec.name)
            if item is None:
                item = ArmorItem(sec.name, meta.get(sec.name))
                items.append(item)
                by_sid[sec.name] = item
            item.patch = sec
            item.values.update(_read_values(sec))
    return items


def changed_fields(item: ArmorItem) -> dict[str, str]:
    out: dict[str, str] = {}
    source = item.vanilla if item.vanilla else {}
    for key in EDIT_FIELDS:
        value = item.values.get(key)
        if value is None:
            continue
        base = source.get(key)
        if base is None or not _same_value(value, base):
            out[key] = value
    return out


def build_block(sid: str, changed: dict[str, str]) -> list[str]:
    out = [f"{sid} : struct.begin {{bpatch}}"]
    if "BaseDurability" in changed:
        out.append(f"   BaseDurability = {fmt_float(changed['BaseDurability'])}")
    prot = {key: changed["Protection." + key] for key in PROT_ORDER if "Protection." + key in changed}
    if prot:
        out.append("   Protection : struct.begin {bpatch}")
        for key in PROT_ORDER:
            if key in prot:
                out.append(f"      {key} = {fmt_float(prot[key])}")
        out.append("   struct.end")
    out.append("struct.end")
    return out


def apply_model_to_doc(items: list[ArmorItem], doc: CfgDoc, source=None) -> int:
    secs = doc.sections()
    first = secs[0].start if secs else len(doc.lines)
    header = doc.lines[:first]
    while header and header[-1].strip() == "":
        header.pop()
    doc.lines = header
    if doc.lines:
        doc.lines.append("")
    written = 0
    for item in items:
        if source is not None and item.source != source:
            continue
        changed = changed_fields(item)
        if not changed:
            continue
        doc.lines.extend(build_block(item.sid, changed))
        doc.lines.append("")
        written += 1
    return written


def save_patches(items, paths=None):
    written = 0
    changed_paths = []
    for source in SOURCE_KEYS:
        path = (paths or {}).get(source) or patch_path(source)
        ensure_patch_file(path, source)
        doc = CfgDoc(path)
        count = apply_model_to_doc(items, doc, source=source)
        doc.save()
        written += count
        if count:
            changed_paths.append(path)
    return written, changed_paths


def remove_section(doc: CfgDoc, name: str) -> bool:
    for sec in doc.sections():
        if sec.name != name:
            continue
        start, end = sec.start, sec.end
        del doc.lines[start:end + 1]
        while (
            start > 0
            and start < len(doc.lines)
            and doc.lines[start] == ""
            and doc.lines[start - 1] == ""
        ):
            del doc.lines[start]
        while doc.lines and doc.lines[-1] == "":
            doc.lines.pop()
        return True
    return False


def validate(items: list[ArmorItem], lang: str) -> list[str]:
    errors = []
    for item in items:
        label = item.display(lang)
        for key in EDIT_FIELDS:
            value = item.values.get(key)
            if value is None:
                continue
            try:
                number = float(str(value).replace(",", "."))
            except (TypeError, ValueError):
                errors.append(t(lang, "err_number", field=f"{label} / {key}", value=value))
                continue
            if number < 0:
                errors.append(t(lang, "err_negative", field=f"{label} / {key}"))
    return errors


def filter_items(items, lang, query, category, faction, sort_key):
    q = (query or "").strip().casefold()
    out = []
    for item in items:
        if category != "all" and item.kind != category:
            continue
        if faction != "all" and item.faction_key() != faction:
            continue
        if q:
            blob = " ".join([
                item.sid,
                item.in_game_name("en"),
                item.in_game_name("uk"),
                item.faction_label("en"),
                item.faction_label("uk"),
            ]).casefold()
            if item.unique:
                blob += " unique унікальний"
            if q not in blob:
                continue
        out.append(item)
    name_key = lambda it: it.in_game_name(lang).casefold()
    if sort_key == "sid":
        out.sort(key=lambda it: it.sid.casefold())
    elif sort_key == "modified":
        out.sort(key=lambda it: (not changed_fields(it), name_key(it)))
    else:
        out.sort(key=name_key)
    return out


class Tooltip:
    def __init__(self, widget, get_text, delay=450):
        self.widget = widget
        self.get_text = get_text
        self.delay = delay
        self.tip = None
        self._after = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None):
        self._hide()
        try:
            self._after = self.widget.after(self.delay, self._show)
        except tk.TclError:
            pass

    def _show(self):
        text = self.get_text()
        if not text:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        frame = tk.Frame(self.tip, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        frame.pack()
        tk.Label(
            frame, text=text, bg=PANEL, fg=FG, font=("Segoe UI", 9),
            justify="left", padx=8, pady=4,
        ).pack()

    def _hide(self, _event=None):
        if self._after is not None:
            try:
                self.widget.after_cancel(self._after)
            except tk.TclError:
                pass
            self._after = None
        if self.tip is not None:
            try:
                self.tip.destroy()
            except tk.TclError:
                pass
            self.tip = None


class App(tk.Tk):
    def __init__(self, lang_override=None):
        super().__init__()
        self.settings = read_settings()
        self.lang = lang_override or self.settings.get("language", "uk")
        if self.lang not in TRANSLATIONS:
            self.lang = "uk"
        self.items: list[ArmorItem] = []
        self.visible: list[ArmorItem] = []
        self.current: ArmorItem | None = None
        self.vars: dict[str, tk.StringVar] = {}
        self._loading = False

        self.title(self.tt("title"))
        self.configure(bg=BG)
        self.geometry("1000x640")
        self.minsize(860, 540)
        self._init_style()
        self.reload()
        self._build_ui()
        self.refresh_view()
        self.set_status(t(self.lang, "status_loaded", count=len(self.items)))
        self.bind("<Control-s>", lambda _e: self.do_save(pack=True))
        self.bind("<Control-S>", lambda _e: self.do_save(pack=False))
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def tt(self, key, **kwargs):
        return t(self.lang, key, **kwargs)

    def _init_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox", fieldbackground=FIELD, background=PANE2,
                        foreground=FG, arrowcolor=FG, bordercolor=BORDER,
                        lightcolor=BORDER, darkcolor=BORDER)
        style.map("TCombobox", fieldbackground=[("readonly", FIELD)],
                  foreground=[("readonly", FG)], selectbackground=[("readonly", FIELD)],
                  selectforeground=[("readonly", FG)])
        style.configure("TEntry", fieldbackground=FIELD, foreground=FG,
                        insertcolor=FG, bordercolor=BORDER, lightcolor=BORDER,
                        darkcolor=BORDER, padding=2)
        style.map("TEntry", fieldbackground=[("readonly", FIELD)],
                  foreground=[("disabled", MUTED)])
        style.configure("Treeview", background=FIELD, fieldbackground=FIELD,
                        foreground=FG, bordercolor=BORDER, rowheight=24)
        style.configure("Treeview.Heading", background=PANE2, foreground=FG,
                        bordercolor=BORDER, relief="flat", padding=(6, 3))
        style.map("Treeview.Heading", background=[("active", SEL)])
        style.map("Treeview", background=[("selected", SEL)],
                  foreground=[("selected", FG)])
        style.configure("Vertical.TScrollbar", background=PANE2, troughcolor=FIELD,
                        bordercolor=BORDER, arrowcolor=MUTED)
        style.configure("Dark.TCheckbutton", background=PANEL, foreground=FG)

    def reload(self, confirm=False):
        if confirm and not messagebox.askyesno(
            self.tt("dlg_reload_title"), self.tt("dlg_reload_msg")
        ):
            return
        if not os.path.exists(VANILLA_ARMOR):
            messagebox.showerror(
                self.tt("title"), self.tt("vanilla_missing", path=VANILLA_ARMOR)
            )
            return
        for source in SOURCE_KEYS:
            ensure_patch_file(patch_path(source), source)
        self.items = load_items(
            VANILLA_ARMOR, {source: patch_path(source) for source in SOURCE_KEYS}
        )
        self.current = None

    # -- layout ---------------------------------------------------------
    def _build_ui(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(top, textvariable=self._title_var(), bg=BG, fg=ACCENT,
                 font=("Segoe UI Semibold", 15)).pack(side="left")
        self.lang_combo = ttk.Combobox(top, values=["uk", "en"], state="readonly", width=4)
        self.lang_combo.set(self.lang)
        self.lang_combo.pack(side="right")
        tk.Label(top, text=self.tt("language"), bg=BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="right", padx=(0, 6))
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_lang)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=4)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=4)
        body.rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        right.grid(row=0, column=1, sticky="nsew")

        # filters
        filters = tk.Frame(left, bg=PANEL)
        filters.pack(fill="x", padx=8, pady=(8, 4))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(filters, textvariable=self.search_var)
        self.search_entry.pack(fill="x")
        combos = tk.Frame(filters, bg=PANEL)
        combos.pack(fill="x", pady=(6, 0))
        self.cat_combo = ttk.Combobox(combos, state="readonly", width=10)
        self.cat_combo.pack(side="left")
        self.fac_combo = ttk.Combobox(combos, state="readonly", width=18)
        self.fac_combo.pack(side="left", padx=(6, 0))
        self.sort_combo = ttk.Combobox(combos, state="readonly", width=14)
        self.sort_combo.pack(side="right")
        self.search_var.trace_add("write", lambda *_a: self.refresh_view())
        self.cat_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_view())
        self.fac_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_view())
        self.sort_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_view())

        self.list_hint = tk.Label(left, bg=PANEL, fg=MUTED, font=("Segoe UI", 8))
        self.list_hint.pack(anchor="w", padx=10)

        list_frame = tk.Frame(left, bg=PANEL)
        list_frame.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self.tree = ttk.Treeview(list_frame, columns=("name", "kind", "faction"),
                                 show="headings", selectmode="browse")
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self._apply_columns()
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # right pane
        self.head_name = tk.Label(right, text=self.tt("select_item"), bg=PANEL, fg=FG,
                                  font=("Segoe UI Semibold", 13), anchor="w")
        self.head_name.pack(fill="x", padx=12, pady=(10, 0))
        self.head_sid = tk.Label(right, text="", bg=PANEL, fg=MUTED,
                                 font=("Consolas", 9), anchor="w")
        self.head_sid.pack(fill="x", padx=12)
        self.head_meta = tk.Label(right, text="", bg=PANEL, fg=MUTED,
                                  font=("Segoe UI", 9), anchor="w")
        self.head_meta.pack(fill="x", padx=12)
        self.head_status = tk.Label(right, text="", bg=PANEL, fg=MUTED,
                                    font=("Segoe UI", 9), anchor="w")
        self.head_status.pack(fill="x", padx=12, pady=(2, 8))

        form = tk.Frame(right, bg=PANEL)
        form.pack(fill="x", padx=12)
        self.group_label = tk.Label(form, text=self.tt("group_prot"), bg=PANEL,
                                    fg=ACCENT, font=("Segoe UI Semibold", 10), anchor="w")
        self.group_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(4, 6))
        row = 1
        for key in EDIT_FIELDS:
            label_key = "field_dur" if key == "BaseDurability" else dict(PROT_FIELDS)[key]
            tk.Label(form, text=self.tt(label_key), bg=PANEL, fg=FG,
                     font=("Segoe UI", 9), anchor="w").grid(
                row=row, column=0, sticky="w", pady=2, padx=(0, 10))
            var = tk.StringVar()
            self.vars[key] = var
            ttk.Entry(form, textvariable=var, width=14).grid(
                row=row, column=1, sticky="w", pady=2)
            row += 1
        tk.Label(form, text=self.tt("dur_hint"), bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 8), anchor="w", justify="left").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(6, 0))

        actions = tk.Frame(right, bg=PANEL)
        actions.pack(fill="x", padx=12, pady=(10, 4))
        self.reset_btn = tk.Button(
            actions, text=self.tt("btn_reset"), command=self.reset_current,
            bg=PANE2, fg=FG, activebackground=SEL, activeforeground=FG,
            relief="flat", padx=10, pady=4, font=("Segoe UI", 9),
        )
        self.reset_btn.pack(side="left")
        Tooltip(self.reset_btn, lambda: self.tt("tip_reset"))
        tk.Button(
            actions, text=self.tt("btn_reload"), command=lambda: self.reload(confirm=True),
            bg=PANE2, fg=FG, activebackground=SEL, activeforeground=FG,
            relief="flat", padx=10, pady=4, font=("Segoe UI", 9),
        ).pack(side="left", padx=(8, 0))

        notes = tk.Frame(right, bg=PANE2)
        notes.pack(fill="x", padx=12, pady=(6, 0))
        tk.Label(notes, text=self.tt("notes_title"), bg=PANE2, fg=ACCENT,
                 font=("Segoe UI Semibold", 9), anchor="w").pack(
            fill="x", padx=8, pady=(6, 0))
        tk.Label(notes, text=self.tt("notes"), bg=PANE2, fg=MUTED,
                 font=("Segoe UI", 8), justify="left", anchor="w").pack(
            fill="x", padx=8, pady=(2, 6))

        bottom = tk.Frame(self, bg=BG)
        bottom.pack(fill="x", padx=12, pady=(4, 10))
        tk.Label(bottom, text=self.tt("mods_folder"), bg=BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="left")
        self.mods_var = tk.StringVar(value=self.settings.get("mods_dir", ""))
        ttk.Entry(bottom, textvariable=self.mods_var, width=48).pack(
            side="left", padx=6)
        tk.Button(
            bottom, text=self.tt("browse"), command=self._browse_mods,
            bg=PANE2, fg=FG, activebackground=SEL, activeforeground=FG,
            relief="flat", padx=8, pady=3, font=("Segoe UI", 9),
        ).pack(side="left")
        self.save_pack_btn = tk.Button(
            bottom, text=self.tt("save_pack"), command=lambda: self.do_save(pack=True),
            bg=ACCENT, fg=INK, activebackground="#e0bc66", activeforeground=INK,
            relief="flat", padx=12, pady=4, font=("Segoe UI Semibold", 9),
        )
        self.save_pack_btn.pack(side="right")
        tk.Button(
            bottom, text=self.tt("save_cfg"), command=lambda: self.do_save(pack=False),
            bg=PANE2, fg=FG, activebackground=SEL, activeforeground=FG,
            relief="flat", padx=10, pady=4, font=("Segoe UI", 9),
        ).pack(side="right", padx=(0, 8))

        self.status = tk.Label(self, text="", bg=BG, fg=MUTED, anchor="w",
                               font=("Segoe UI", 9))
        self.status.pack(fill="x", padx=14, pady=(0, 6))
        tk.Label(self, text=self.tt("shortcut"), bg=BG, fg=MUTED,
                 font=("Segoe UI", 8), anchor="w").pack(fill="x", padx=14, pady=(0, 6))

        self._refresh_filter_values()
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_lang)

    def _apply_columns(self):
        self.tree.heading("name", text=self.tt("col_name"))
        self.tree.heading("kind", text=self.tt("col_kind"))
        self.tree.heading("faction", text=self.tt("col_faction"))
        self.tree.column("name", width=230, minwidth=140, anchor="w")
        self.tree.column("kind", width=70, minwidth=55, anchor="w", stretch=False)
        self.tree.column("faction", width=105, minwidth=80, anchor="w", stretch=False)

    def _title_var(self):
        self._title_text = tk.StringVar(value=self.tt("title"))
        return self._title_text

    def _refresh_filter_values(self):
        self.cat_combo["values"] = [self.tt("cat_" + k) for k in CATEGORY_KEYS]
        idx = CATEGORY_KEYS.index("all")
        if self.cat_combo.current() < 0:
            self.cat_combo.current(idx)
        fac_values = [self.tt("fac_all")] + [
            FACTION_LABELS[key][1 if self.lang == "uk" else 0]
            for key in FACTION_KEYS[1:]
        ]
        fac_index = max(self.fac_combo.current(), 0)
        self.fac_combo["values"] = fac_values
        self.fac_combo.current(min(fac_index, len(fac_values) - 1))
        self.sort_combo["values"] = [self.tt("sort_" + k) for k in SORT_KEYS]
        if self.sort_combo.current() < 0:
            self.sort_combo.current(0)

    def _on_lang(self, _event=None):
        lang = self.lang_combo.get()
        if lang in TRANSLATIONS:
            self.lang = lang
            self.settings["language"] = lang
            write_settings(self.settings)
            self._retranslate()
            self.refresh_view()

    def _retranslate(self):
        self.tree.delete(*self.tree.get_children())
        self._apply_columns()
        self.title(self.tt("title"))
        self._title_text.set(self.tt("title"))
        self.search_entry.configure(values=[])
        self._refresh_filter_values()
        self.head_name.configure(text=self.tt("select_item") if self.current is None
                                 else self.current.display(self.lang))
        if self.current is None:
            self.head_meta.configure(text="")
        self.group_label.configure(text=self.tt("group_prot"))
        self.reset_btn.configure(text=self.tt("btn_reset"))
        self.save_pack_btn.configure(text=self.tt("save_pack"))
        if self.current is not None:
            self._show_item(self.current)

    # -- list ----------------------------------------------------------
    def _filter_keys(self):
        query = self.search_var.get()
        category = CATEGORY_KEYS[max(self.cat_combo.current(), 0)]
        faction = FACTION_KEYS[max(self.fac_combo.current(), 0)]
        sort_key = SORT_KEYS[max(self.sort_combo.current(), 0)]
        return query, category, faction, sort_key

    def refresh_view(self, keep_sid=None):
        query, category, faction, sort_key = self._filter_keys()
        self.visible = filter_items(self.items, self.lang, query, category,
                                    faction, sort_key)
        current_sid = keep_sid or (self.current.sid if self.current else None)
        self.tree.delete(*self.tree.get_children())
        for item in self.visible:
            self.tree.insert("", "end", iid=item.sid,
                             values=(item.display(self.lang),
                                     self.tt("kind_" + item.kind),
                                     item.faction_label(self.lang)))
        self.list_hint.configure(
            text=self.tt("list_hint", shown=len(self.visible), total=len(self.items)))
        if current_sid and any(it.sid == current_sid for it in self.visible):
            self.tree.selection_set(current_sid)
            self.tree.see(current_sid)

    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        sid = sel[0]
        item = next((it for it in self.items if it.sid == sid), None)
        if item is None:
            return
        self.commit_current()
        self.current = item
        self._show_item(item)

    def _show_item(self, item: ArmorItem):
        self._loading = True
        self.head_name.configure(text=item.display(self.lang))
        self.head_sid.configure(text=item.sid)
        meta_bits = [item.faction_label(self.lang)]
        if item.unique:
            meta_bits.append(self.tt("meta_unique"))
        self.head_meta.configure(text="  \u00b7  ".join(meta_bits))
        self.head_status.configure(
            text=self.tt("status_patch") if item.patch is not None
            else self.tt("status_vanilla"))
        for key in EDIT_FIELDS:
            self.vars[key].set(item.values.get(key, ""))
        self.reset_btn.configure(state="normal" if item.patch is not None else "disabled")
        self._loading = False

    def commit_current(self):
        item = self.current
        if item is None or self._loading:
            return
        for key in EDIT_FIELDS:
            value = self.vars[key].get().strip()
            if value == "":
                item.values.pop(key, None)
            else:
                item.values[key] = value

    def set_status(self, text):
        self.status.configure(text=text)

    # -- save ----------------------------------------------------------
    def do_save(self, pack=False):
        if self.current is not None:
            self.commit_current()
        errors = validate(self.items, self.lang)
        if errors:
            messagebox.showerror(self.tt("dlg_invalid_title"),
                                 self.tt("dlg_invalid_msg", errors="\n".join(errors[:15])))
            return
        try:
            written, changed_paths = save_patches(self.items)
        except Exception as exc:
            messagebox.showerror(self.tt("dlg_save_failed"), str(exc))
            return
        keep = self.current.sid if self.current else None
        self.reload()
        self.refresh_view(keep_sid=keep)
        if keep:
            self.current = next((it for it in self.items if it.sid == keep), None)
            if self.current:
                self._show_item(self.current)
        if pack:
            if written == 0:
                messagebox.showinfo(self.tt("dlg_no_changes_title"),
                                    self.tt("dlg_no_changes_msg"))
                return
            self.pack_and_deploy()
        elif written == 0:
            self.set_status(self.tt("status_nochange"))
        else:
            self.set_status(self.tt("status_saved", count=written))
            messagebox.showinfo(self.tt("dlg_saved_title"),
                                self.tt("dlg_saved_msg", path="\n".join(changed_paths)))

    def reset_current(self):
        item = self.current
        if item is None or item.patch is None:
            return
        name = item.display(self.lang)
        if not messagebox.askyesno(self.tt("dlg_reset_title"),
                                   self.tt("dlg_reset_msg", name=name, sid=item.sid)):
            return
        self.commit_current()
        item.values = dict(item.vanilla)
        item.patch = None
        try:
            save_patches(self.items)
        except Exception as exc:
            messagebox.showerror(self.tt("dlg_save_failed"), str(exc))
            return
        self.reload()
        self.refresh_view()
        self.current = next((it for it in self.items if it.sid == item.sid), None)
        if self.current:
            self._show_item(self.current)
        self.set_status(self.tt("status_reset", name=name))

    # -- packing -------------------------------------------------------
    def _browse_mods(self):
        folder = filedialog.askdirectory(title=self.tt("browse_title"))
        if not folder:
            return
        folder = os.path.normpath(folder)
        if os.path.basename(folder).lower() == "paks":
            folder = os.path.join(folder, "~mods")
        self.mods_var.set(folder)
        self.settings["mods_dir"] = folder
        write_settings(self.settings)

    def pack_and_deploy(self):
        repak = find_repak()
        if not repak:
            messagebox.showwarning(self.tt("dlg_repak_missing_title"),
                                   self.tt("dlg_repak_missing_msg"))
            return
        source_tree = os.path.join(UPDATED_DIR, "Stalker2")
        if not os.path.isdir(source_tree):
            messagebox.showerror(self.tt("dlg_pack_failed_title"),
                                 self.tt("pack_missing_folder", path=source_tree))
            return
        expected = []
        for source in SOURCE_KEYS:
            cfg = patch_path(source)
            if os.path.exists(cfg) and CfgDoc(cfg).sections():
                expected.append(patch_entry(source))
        if not expected:
            messagebox.showinfo(self.tt("dlg_no_changes_title"),
                                self.tt("dlg_no_changes_msg"))
            return
        staging = None
        try:
            staging = tempfile.mkdtemp(prefix="gur_armor_pak_")
            shutil.copytree(
                source_tree, os.path.join(staging, "Stalker2"),
                ignore=shutil.ignore_patterns("*.pak", "*.exe", "*.utoc", "*.ucas"),
            )
            for entry in expected:
                staged_cfg = os.path.join(staging, *entry.split("/"))
                if not os.path.exists(staged_cfg):
                    raise EditorError(self.tt("pack_missing_folder", path=staged_cfg))
            old = os.path.join(ROOT, PAK_NAME)
            if os.path.exists(old):
                os.remove(old)
            proc = _run_hidden([repak, "pack", staging, PAK_PATH])
            if proc.returncode != 0:
                raise EditorError("repak failed:\n" + (proc.stderr or proc.stdout or "no output"))
            check = _run_hidden([repak, "list", PAK_PATH])
            entries = [line.strip() for line in check.stdout.splitlines() if line.strip()]
            packed = {e.replace("\\", "/").lstrip("/") for e in entries}
            missing = [entry for entry in expected if entry not in packed]
            if missing:
                raise EditorError("Packed archive is missing " + ", ".join(missing))
            built_hash = sha256_file(PAK_PATH)
        except Exception as exc:
            messagebox.showerror(self.tt("dlg_pack_failed_title"),
                                 self.tt("dlg_pack_failed_msg", error=exc))
            return
        finally:
            if staging:
                shutil.rmtree(staging, ignore_errors=True)

        deployed = ""
        warning = ""
        mods_dir = self.mods_var.get().strip()
        if mods_dir:
            target = os.path.join(mods_dir, PAK_NAME)
            try:
                os.makedirs(mods_dir, exist_ok=True)
                shutil.copy2(PAK_PATH, target)
                if sha256_file(target) != built_hash:
                    raise OSError("copied pak does not match the freshly built one")
                deployed = target
                self.settings["mods_dir"] = mods_dir
                write_settings(self.settings)
            except OSError as exc:
                warning = self.tt("pack_copy_error", error=exc)

        summary = [
            self.tt("pack_ok"), "",
            self.tt("pack_archive", path=PAK_PATH),
            self.tt("pack_entries", total=len(entries), cfgs=len([e for e in entries if e.lower().endswith(".cfg")])),
        ]
        if deployed:
            summary.append(self.tt("pack_deployed", path=deployed))
            summary.append(self.tt("pack_verified", hash=built_hash[:12]))
        messagebox.showinfo(self.tt("dlg_pack_ok_title"), "\n".join(summary) + warning)


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    import io
    import tempfile

    out = sys.stdout
    checks = []

    def check(ok, label):
        checks.append((bool(ok), label))

    if not os.path.exists(VANILLA_ARMOR):
        print("missing", VANILLA_ARMOR)
        return 1
    if not os.path.exists(META_PATH):
        print("missing", META_PATH)
        return 1
    vanilla = CfgDoc(VANILLA_ARMOR).sections()
    check(len(vanilla) == 54, f"vanilla armor sections: {len(vanilla)}")
    check(all(s.find_scalar("BaseDurability") for s in vanilla), "every item has BaseDurability")
    check(all(s.find_struct("Protection") for s in vanilla), "every item has Protection")

    tmp = tempfile.mkdtemp(prefix="gur_armor_test_")
    paths = {source: os.path.join(tmp, source + ".cfg") for source in SOURCE_KEYS}
    for source, path in paths.items():
        ensure_patch_file(path, source)

    items = load_items(VANILLA_ARMOR, paths)
    check(len(items) == 54, f"loaded items: {len(items)}")
    zorya = next(it for it in items if it.sid == "Zorya_Neutral_Armor")
    check(zorya.values.get("Protection.Strike") == "2.0", "vanilla Strike read")
    check(zorya.values.get("BaseDurability") == "910.0", "vanilla durability read")
    check(zorya.kind == "armor", "armor category")
    check(zorya.display("uk") == "Комбінезон «Зоря»", "uk in-game name")
    check(zorya.display("en") == "Sunrise Suit", "en in-game name")
    check(zorya.faction_key() == "neutral" and not zorya.unique, "faction / unique meta")
    tourist = next(it for it in items if it.sid == "Zorya_Tourist_Armor")
    check(tourist.unique and tourist.source == "PreOrder", "PreOrder unique detected")
    check(tourist.display("uk") == "★ Комбінезон туриста", "unique star marker")
    x7 = next(it for it in items if it.sid == "Battle_Dolg_End_Armor")
    check(x7.unique and x7.faction_key() == "dolg", "quest unique meta")
    check(next(it for it in items if it.sid == "Light_Neutral_Helmet").kind == "helmet", "helmet category")

    zorya.values["Protection.Strike"] = "12.5"
    zorya.values["BaseDurability"] = "1500"
    tourist.values["Protection.Radiation"] = "77"
    doc = CfgDoc(paths["base"])
    written = apply_model_to_doc(items, doc, source="base")
    check(written == 1, f"one changed section written: {written}")
    doc.save()
    text = open(paths["base"], encoding="utf-8").read()
    check("Zorya_Neutral_Armor : struct.begin {bpatch}" in text, "bpatch marker")
    check("Protection : struct.begin {bpatch}" in text, "nested Protection bpatch")
    check("Strike = 12.5" in text, "changed strike written")
    check("BaseDurability = 1500.0" in text, "changed durability written")
    check("Burn =" not in text, "unchanged protection fields are not written")
    check(text.strip().startswith("// GUR - Armor Reconfigurator patch."), "header comments kept")
    check("," not in text.split("Strike = ")[1].split("\n")[0], "dot decimals")

    doc = CfgDoc(paths["PreOrder"])
    written_dlc = apply_model_to_doc(items, doc, source="PreOrder")
    doc.save()
    text_dlc = open(paths["PreOrder"], encoding="utf-8").read()
    check(written_dlc == 1, f"DLC patch written: {written_dlc}")
    check("Zorya_Tourist_Armor : struct.begin {bpatch}" in text_dlc, "DLC block in PreOrder patch")
    check("Zorya_Neutral_Armor" not in text_dlc, "base item kept out of DLC patch")

    saved = CfgDoc(paths["base"])
    sec = saved.sections()[0]
    span = sec.find_struct("Protection")
    hit = sec.find_scalar("Strike", within=span)
    check(hit and abs(float(hit[2]) - 12.5) < 1e-6, "roundtrip strike value")

    items2 = load_items(VANILLA_ARMOR, paths)
    z2 = next(it for it in items2 if it.sid == "Zorya_Neutral_Armor")
    t2 = next(it for it in items2 if it.sid == "Zorya_Tourist_Armor")
    check(z2.values["Protection.Strike"] == "12.5", "patch overlay on load")
    check(abs(float(t2.values["Protection.Radiation"]) - 77) < 1e-6, "DLC patch overlay on load")
    check(z2.patch is not None and t2.patch is not None, "patch sections detected")

    written, changed = save_patches(items2, paths)
    check(written == 2 and len(changed) == 2, f"save_patches wrote {written} into {len(changed)} files")

    t2.values = dict(t2.vanilla)
    t2.patch = None
    written, _ = save_patches(items2, paths)
    check(written == 1, "reset DLC item leaves one block")
    check("Zorya_Tourist_Armor" not in open(paths["PreOrder"], encoding="utf-8").read(),
          "reset removes the DLC block")

    z2.values = dict(z2.vanilla)
    z2.patch = None
    written, _ = save_patches(items2, paths)
    check(written == 0, "everything reset")
    check(all(not CfgDoc(p).sections() for p in paths.values()), "empty patches have no sections")
    check(all(open(p, encoding="utf-8").read().strip().startswith("// GUR")
              for p in paths.values()), "headers kept on empty patches")

    # UI-independent filtering
    items = load_items(VANILLA_ARMOR, paths)
    helmets = filter_items(items, "uk", "", "helmet", "all", "alpha")
    check(len(helmets) == 10 and all(it.kind == "helmet" for it in helmets), "helmet filter")
    dolg = filter_items(items, "uk", "", "all", "dolg", "alpha")
    check(len(dolg) == 9 and all(it.faction_key() == "dolg" for it in dolg),
          f"dolg faction filter: {len(dolg)}")
    uniques = [it for it in items if it.unique]
    check(len(uniques) == 6, f"unique items: {len(uniques)}")
    check(filter_items(items, "en", "Tourist", "all", "all", "alpha")[0].sid == "Zorya_Tourist_Armor",
          "search by in-game name")
    zorya_hits = {it.sid for it in filter_items(items, "en", "Zorya", "all", "all", "alpha")}
    check(zorya_hits == {"Zorya_Neutral_Armor", "Zorya_Tourist_Armor"}, "search by SID")

    failed = [label for ok, label in checks if not ok]
    for ok, label in checks:
        print(("  OK   " if ok else "  FAIL ") + label)
    print("SELFTEST OK" if not failed else "SELFTEST FAILED")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if not failed else 1


def main() -> int:
    tests = "--selftest" in sys.argv or "--smoke" in sys.argv
    if tests and (sys.stdout is None or sys.stderr is None):
        log_path = os.path.join(ROOT, "GUR_Armor_test.log")
        stream = open(log_path, "w", encoding="utf-8", buffering=1)
        sys.stdout = sys.stdout or stream
        sys.stderr = sys.stderr or stream
    if "--selftest" in sys.argv:
        return run_selftest()
    lang_override = None
    if "--lang" in sys.argv:
        index = sys.argv.index("--lang")
        if index + 1 < len(sys.argv):
            lang_override = sys.argv[index + 1]
    app = App(lang_override=lang_override)
    if "--smoke" in sys.argv:
        app.update()
        try:
            if len(app.items) != 54:
                raise AssertionError(f"expected 54 items, got {len(app.items)}")
            if len(app.tree.get_children()) != 54:
                raise AssertionError("list does not show every item")
            app.search_var.set("Zorya")
            if {it.sid for it in app.visible} != {"Zorya_Neutral_Armor", "Zorya_Tourist_Armor"}:
                raise AssertionError("search filter failed")
            app.search_var.set("")
            app.cat_combo.current(CATEGORY_KEYS.index("helmet"))
            app.refresh_view()
            if len(app.visible) != 10:
                raise AssertionError("helmet filter failed")
            app.cat_combo.current(0)
            app.fac_combo.current(FACTION_KEYS.index("monolith"))
            app.refresh_view()
            if len(app.visible) != 5 or not all(it.faction_key() == "monolith" for it in app.visible):
                raise AssertionError("faction filter failed")
            app.fac_combo.current(0)
            app.sort_combo.current(SORT_KEYS.index("sid"))
            app.refresh_view()
            expected = sorted((it.sid for it in app.items), key=str.casefold)
            if [it.sid for it in app.visible] != expected:
                raise AssertionError("sort by SID failed")
            app.sort_combo.current(0)
            app.refresh_view()
            app.tree.selection_set("Zorya_Neutral_Armor")
            app.update()
            if app.current is None or app.current.sid != "Zorya_Neutral_Armor":
                raise AssertionError("selection failed")
            if app.vars["Protection.Strike"].get() != "2.0":
                raise AssertionError("field load failed")
            if app.head_name.cget("text") != "Комбінезон «Зоря»":
                raise AssertionError("in-game header name failed")
            if "Нейтрали" not in app.head_meta.cget("text"):
                raise AssertionError("faction meta failed")
            app.tree.selection_set("Zorya_Tourist_Armor")
            app.update()
            if app.current is None or not app.current.unique:
                raise AssertionError("unique selection failed")
            if not app.head_name.cget("text").startswith("\u2605 "):
                raise AssertionError("unique marker failed")
        except AssertionError as exc:
            app.destroy()
            print("SMOKE FAILED:", exc)
            return 1
        app.after(300, app.destroy)
        app.mainloop()
        print("SMOKE OK")
        return 0
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
