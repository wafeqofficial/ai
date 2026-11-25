#!/usr/bin/env python3
"""Check the plugin against the OpenAI and Claude directory submission rules.

Covers only what the repository files can show: manifest values, file layout,
file types and sizes, and images. Domain verification, tool scans, safety
scans, name collisions and policy review stay with the portals.

Each rule names its source:
  OPENAI  https://developers.openai.com/plugins/deploy/submission-errors
  CLAUDE  https://claude.com/docs/plugins/pre-submission-checklist
  REPO    our own rule: the manifests must agree with each other

Rules copied from the pages on 2026-11-25. Update this file when a page changes.

Usage: check_submission.py [--base <git ref>]
Uses only the Python standard library, so it needs no install step.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import struct
import subprocess
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]

PORTABLE = "plugin.json"
CODEX = ".codex-plugin/plugin.json"
CLAUDE = ".claude-plugin/plugin.json"
CLAUDE_MARKETPLACE = ".claude-plugin/marketplace.json"
AGENTS_MARKETPLACE = ".agents/plugins/marketplace.json"
PORTABLE_MCP = "mcp.json"
COMPAT_MCP = ".mcp.json"

KIB = 1024
MIB = 1024 * KIB

OPENAI_CATEGORIES = {
    "Productivity", "Creativity", "Developer Tools", "Business & Operations",
    "Data & Analytics", "Communication", "Education & Research", "Security",
    "Finance", "Healthcare", "Travel", "Entertainment", "Other",
}
OPENAI_LISTING_URLS = ("websiteURL", "privacyPolicyURL", "termsOfServiceURL", "supportURL")
CLAUDE_RESERVED_NAMES = {"claude", "anthropic", "official", "plugin", "mcp", "test"}
WINDOWS_DEVICE_NAMES = {"con", "prn", "aux", "nul"} | {f"{p}{i}" for p in ("com", "lpt") for i in range(1, 10)}
SYSTEM_FILES = {".ds_store", "thumbs.db", "desktop.ini", "__macosx"}
FONT_EXTENSIONS = {".ttf", ".otf", ".woff", ".woff2"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}

# semver.org reference pattern. The OpenAI page asks for "semantic versioning"
# without its own pattern.
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


class Report:
    def __init__(self) -> None:
        self.errors = 0
        self.warnings = 0
        self.in_actions = os.environ.get("GITHUB_ACTIONS") == "true"

    def _emit(self, level: str, source: str, file: str, message: str) -> None:
        if self.in_actions:
            print(f"::{level} file={file},title={source}::{message}")
        else:
            print(f"{level.upper():7} [{source}] {file}: {message}")

    def error(self, source: str, file: str, message: str) -> None:
        self.errors += 1
        self._emit("error", source, file, message)

    def warn(self, source: str, file: str, message: str) -> None:
        self.warnings += 1
        self._emit("warning", source, file, message)


# --- helpers -----------------------------------------------------------------


def load_json(report: Report, rel: str) -> dict | None:
    path = ROOT / rel
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        report.error("OPENAI/CLAUDE", rel, f"not valid UTF-8 JSON: {exc}")
        return None
    if not isinstance(data, dict):
        report.error("OPENAI/CLAUDE", rel, "top level must be a JSON object")
        return None
    return data


def unsupported_chars(text: str, allow_newlines: bool) -> list[str]:
    """OPENAI: no control characters, no U+2028/U+2029, no invisible format characters."""
    bad = []
    for ch in text:
        if ch == "\n" and allow_newlines:
            continue
        cat = unicodedata.category(ch)
        if cat in ("Cc", "Cf", "Zl", "Zp"):
            bad.append(f"U+{ord(ch):04X}")
    return bad


def check_text(report: Report, file: str, field: str, value, *, max_len: int,
               required: bool = True, one_line: bool = True) -> None:
    if value is None:
        if required:
            report.error("OPENAI", file, f"`{field}` is required")
        return
    if not isinstance(value, str):
        report.error("OPENAI", file, f"`{field}` must be a string")
        return
    if not value.strip():
        report.error("OPENAI", file, f"`{field}` must not be empty")
        return
    if len(value) > max_len:
        report.error("OPENAI", file, f"`{field}` is {len(value)} characters, max {max_len}")
    if one_line and ("\n" in value or "\r" in value):
        report.error("OPENAI", file, f"`{field}` must fit on one line")
    bad = unsupported_chars(value, allow_newlines=not one_line)
    if bad:
        report.error("OPENAI", file, f"`{field}` has unsupported characters: {', '.join(bad)}")


def check_https_url(report: Report, file: str, field: str, value, *, max_len: int,
                    required: bool = False) -> None:
    if value is None:
        if required:
            report.error("OPENAI", file, f"`{field}` is required")
        return
    if not isinstance(value, str) or not value.strip():
        report.error("OPENAI", file, f"`{field}` must be a non-empty string")
        return
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname:
        report.error("OPENAI", file, f"`{field}` must be an HTTPS URL with a host: {value}")
    if parts.username or parts.password:
        report.error("OPENAI", file, f"`{field}` must not contain credentials")
    if len(value) > max_len:
        report.error("OPENAI", file, f"`{field}` is {len(value)} characters, max {max_len}")
    if unsupported_chars(value, allow_newlines=False) or any(c.isspace() for c in value):
        report.error("OPENAI", file, f"`{field}` has unsupported characters")


def relative_luminance(hex_color: str) -> float:
    def channel(v: int) -> float:
        c = v / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((relative_luminance(a), relative_luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def image_size(data: bytes) -> tuple[str, int, int] | None:
    """Return (format, width, height) for PNG, JPEG or WebP, or None."""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
        w, h = struct.unpack(">II", data[16:24])
        return "png", w, h
    if data[:3] == b"\xff\xd8\xff":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                return None
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return "jpeg", w, h
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
        return None
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        kind = data[12:16]
        if kind == b"VP8X":
            w = int.from_bytes(data[24:27], "little") + 1
            h = int.from_bytes(data[27:30], "little") + 1
            return "webp", w, h
        if kind == b"VP8 ":
            w, h = struct.unpack("<HH", data[26:30])
            return "webp", w & 0x3FFF, h & 0x3FFF
        if kind == b"VP8L":
            bits = int.from_bytes(data[21:25], "little")
            return "webp", (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return None


def svg_size(path: Path) -> tuple[float, float] | str:
    try:
        root = ET.fromstring(path.read_bytes())
    except ET.ParseError as exc:
        return f"SVG is not valid XML: {exc}"
    if root.tag.rsplit("}", 1)[-1] != "svg":
        return "SVG root element must be <svg>"
    view_box = root.get("viewBox")
    try:
        if view_box:
            _, _, w, h = (float(v) for v in re.split(r"[\s,]+", view_box.strip()))
        else:
            w, h = float(root.get("width", "")), float(root.get("height", ""))
    except ValueError:
        return "SVG needs a numeric viewBox, or numeric width and height without units"
    return w, h


def check_image(report: Report, file: str, field: str, value) -> None:
    """OPENAI asset path and image rules for interface.logo and interface.composerIcon."""
    if not isinstance(value, str) or not value:
        report.error("OPENAI", file, f"`{field}` is required and must reference a square image")
        return
    if value != value.strip() or unsupported_chars(value, allow_newlines=False):
        report.error("OPENAI", file, f"`{field}` has outer whitespace or control characters")
    if not value.startswith("./"):
        report.error("OPENAI", file, f"`{field}` must start with `./`")
    if ".." in Path(value).parts or Path(value).is_absolute():
        report.error("OPENAI", file, f"`{field}` must stay inside the plugin")
        return
    path = ROOT / value
    if not path.is_file() or path.is_symlink():
        report.error("OPENAI", file, f"`{field}` must reference a regular file: {value}")
        return
    if path.stat().st_size > 5 * MIB:
        report.error("OPENAI", file, f"`{field}` image is larger than 5 MiB")
    ext = path.suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
        report.error("OPENAI", file, f"`{field}` must be .png, .jpg, .jpeg, .webp or .svg")
        return
    if ext == ".svg":
        size = svg_size(path)
        if isinstance(size, str):
            report.error("OPENAI", file, f"`{field}`: {size}")
            return
        w, h = size
    else:
        info = image_size(path.read_bytes())
        if info is None:
            report.error("OPENAI", file, f"`{field}` is not a readable PNG, JPEG or WebP image")
            return
        fmt, w, h = info
        if {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".webp": "webp"}[ext] != fmt:
            report.error("OPENAI", file, f"`{field}` extension does not match its {fmt.upper()} content")
        if w > 4096 or h > 4096:
            report.error("OPENAI", file, f"`{field}` is {w}x{h}, max 4096x4096")
    if w != h:
        report.error("OPENAI", file, f"`{field}` must be square, got {w}x{h}")
    if w < 48 or h < 48:
        report.error("OPENAI", file, f"`{field}` is {w}x{h}, min 48x48")


# --- OpenAI ------------------------------------------------------------------


def check_openai_manifest(report: Report, file: str, manifest: dict, interface) -> None:
    name = manifest.get("name")
    check_text(report, file, "name", name, max_len=64)
    if isinstance(name, str) and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", name):
        report.error("OPENAI", file, "`name` must start with an ASCII letter or digit and use only letters, digits, `_` and `-`")

    version = manifest.get("version")
    check_text(report, file, "version", version, max_len=64)
    if isinstance(version, str) and not SEMVER.fullmatch(version):
        report.error("OPENAI", file, f"`version` must be a semantic version such as 1.0.0, got {version!r}")

    check_text(report, file, "description", manifest.get("description"), max_len=1024, one_line=False)

    author = manifest.get("author")
    if not isinstance(author, dict):
        report.error("OPENAI", file, "`author` must be an object with `name`")
    else:
        check_text(report, file, "author.name", author.get("name"), max_len=120)
        check_text(report, file, "author.email", author.get("email"), max_len=320, required=False)
        check_https_url(report, file, "author.url", author.get("url"), max_len=2048)
    check_https_url(report, file, "homepage", manifest.get("homepage"), max_len=2048)

    for key, target, kind in (("skills", "skills", "dir"), ("apps", ".app.json", "file"),
                              ("mcpServers", ".mcp.json", "file")):
        value = manifest.get(key)
        if value is None:
            continue
        if not isinstance(value, str) or os.path.normpath(value) != target:
            report.error("OPENAI", file, f"`{key}` must point to the root `{target}`")
        elif (kind == "dir" and not (ROOT / target).is_dir()) or (kind == "file" and not (ROOT / target).is_file()):
            report.error("OPENAI", file, f"`{key}` points to `{target}`, which does not exist")

    if not isinstance(interface, dict):
        report.error("OPENAI", file, "`interface` must be an object")
        return
    # Final directory submission limits. They are stricter than package validation.
    check_text(report, file, "interface.displayName", interface.get("displayName"), max_len=30)
    check_text(report, file, "interface.shortDescription", interface.get("shortDescription"), max_len=30)
    check_text(report, file, "interface.longDescription", interface.get("longDescription"), max_len=4000, one_line=False)
    check_text(report, file, "interface.developerName", interface.get("developerName"), max_len=80)

    category = interface.get("category")
    if category is None:
        report.warn("OPENAI", file, "`interface.category` is not set, so the listing uses `Other`")
    elif category not in OPENAI_CATEGORIES:
        report.error("OPENAI", file, f"`interface.category` {category!r} is not a supported category")

    capabilities = interface.get("capabilities", [])
    if not isinstance(capabilities, list):
        report.error("OPENAI", file, "`interface.capabilities` must be a list of strings")
    else:
        if len(capabilities) > 20:
            report.error("OPENAI", file, f"`interface.capabilities` has {len(capabilities)} entries, max 20")
        for i, cap in enumerate(capabilities):
            check_text(report, file, f"interface.capabilities[{i}]", cap, max_len=120)

    # A remote MCP submission needs all four listing URLs.
    remote_mcp = "mcpServers" in manifest
    for key in OPENAI_LISTING_URLS:
        check_https_url(report, file, f"interface.{key}", interface.get(key), max_len=1024, required=remote_mcp)

    for key, background in (("brandColor", "#FFFFFF"), ("brandColorDark", "#212121")):
        color = interface.get(key)
        if color is None:
            continue
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            report.error("OPENAI", file, f"`interface.{key}` must be a six-digit hex color such as #1ABCFE")
            continue
        ratio = contrast(color, background)
        if ratio < 2:
            report.error("OPENAI", file, f"`interface.{key}` {color} has {ratio:.2f}:1 contrast against {background}, min 2:1")

    prompts = interface.get("defaultPrompt", [])
    if isinstance(prompts, str):
        prompts = [prompts]
    if not isinstance(prompts, list):
        report.error("OPENAI", file, "`interface.defaultPrompt` must be a string or a list of strings")
    else:
        if len(prompts) > 3:
            report.error("OPENAI", file, f"`interface.defaultPrompt` has {len(prompts)} prompts, max 3")
        seen = set()
        for i, prompt in enumerate(prompts):
            check_text(report, file, f"interface.defaultPrompt[{i}]", prompt, max_len=128)
            if not isinstance(prompt, str):
                continue
            if re.search(r"(^|\s)@\S", prompt):
                report.error("OPENAI", file, f"`interface.defaultPrompt[{i}]` must not @mention an MCP server")
            key = " ".join(unicodedata.normalize("NFKC", prompt).split())
            if key in seen:
                report.error("OPENAI", file, f"`interface.defaultPrompt[{i}]` duplicates an earlier prompt")
            seen.add(key)

    check_image(report, file, "interface.logo", interface.get("logo"))
    check_image(report, file, "interface.composerIcon", interface.get("composerIcon"))


def check_mcp_manifest(report: Report, file: str, data: dict | None) -> None:
    if data is None:
        report.error("OPENAI", file, "file is missing or not valid JSON")
        return
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        report.error("OPENAI", file, "`mcpServers` must be an object")
        return
    for name, server in servers.items():
        if not name.strip():
            report.error("OPENAI", file, "every MCP server name needs a non-whitespace character")
        if not isinstance(server, dict):
            report.error("OPENAI", file, f"`mcpServers.{name}` must be an object")


# --- Claude ------------------------------------------------------------------


def writing_systems(text: str) -> set[str]:
    """First word of each letter's Unicode name, such as LATIN or CYRILLIC."""
    return {unicodedata.name(ch, "UNKNOWN").split()[0] for ch in text if ch.isalpha()}


def check_claude_manifest(report: Report, manifest: dict | None) -> None:
    if manifest is None:
        report.error("CLAUDE", CLAUDE, "`.claude-plugin/plugin.json` is missing (No plugin.json)")
        return
    name = manifest.get("name")
    if not isinstance(name, str) or not name.isascii():
        report.error("CLAUDE", CLAUDE, "`name` must be ASCII (Non-ASCII identifier)")
    elif not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?", name):
        report.warn("CLAUDE", CLAUDE, "`name` should use lowercase letters, digits and hyphens, max 64, starting and ending with a letter or digit")
    if isinstance(name, str) and name.lower() in CLAUDE_RESERVED_NAMES:
        report.error("CLAUDE", CLAUDE, f"`name` {name!r} is a reserved word (Name is taken)")

    for field, value in (("displayName", manifest.get("displayName")),
                         ("author.name", (manifest.get("author") or {}).get("name"))):
        if not isinstance(value, str):
            continue
        invisible = [f"U+{ord(c):04X}" for c in value if unicodedata.category(c) in ("Cf", "Cc")]
        if invisible:
            report.error("CLAUDE", CLAUDE, f"`{field}` has invisible characters: {', '.join(invisible)}")
        systems = writing_systems(value)
        if len(systems) > 1:
            report.error("CLAUDE", CLAUDE, f"`{field}` mixes writing systems: {', '.join(sorted(systems))}")

    for field in ("description", "author", "version"):
        if not manifest.get(field):
            report.warn("CLAUDE", CLAUDE, f"`{field}` is not set")

    if not (ROOT / "LICENSE").is_file() and not manifest.get("license"):
        report.error("CLAUDE", CLAUDE, "add a LICENSE file or set `license` (License missing)")


def check_claude_mcp(report: Report, data: dict | None) -> None:
    if data is None:
        return
    for name, server in (data.get("mcpServers") or {}).items():
        if not isinstance(server, dict):
            continue
        url = server.get("url")
        if url is not None:
            if server.get("type") not in ("http", "sse", "ws"):
                report.error("CLAUDE", COMPAT_MCP, f"`{name}.type` must be http, sse or ws for a remote server")
            if url != "" and not re.match(r"^(https|wss)://[^/\s]+", url) and not re.fullmatch(r"\$\{user_config\.[A-Za-z0-9_]+\}", url):
                report.error("CLAUDE", COMPAT_MCP, f"`{name}.url` must be https:// or wss:// (MCP server URL is not https)")
        for header, value in (server.get("headers") or {}).items():
            if not re.fullmatch(r"(Bearer )?\$\{user_config\.[A-Za-z0-9_]+\}", str(value)):
                report.error("CLAUDE", COMPAT_MCP, f"`{name}.headers.{header}` must use a `${{user_config.KEY}}` reference, not a literal value (Secret in MCP headers)")
        command = " ".join([str(server.get("command", ""))] + [str(a) for a in server.get("args", [])])
        if re.search(r"\.(mcpb|dxt)\b", command):
            report.error("CLAUDE", COMPAT_MCP, f"`{name}` must not run a .mcpb or .dxt bundle")


def git_files() -> list[tuple[str, str]]:
    """Return (mode, path) for every committed file."""
    out = subprocess.run(["git", "ls-files", "-s", "-z"], cwd=ROOT, check=True, capture_output=True).stdout
    entries = []
    for line in out.decode("utf-8").split("\0"):
        if line:
            meta, path = line.split("\t", 1)
            entries.append((meta.split()[0], path))
    return entries


def is_allowed_binary(data: bytes, ext: str) -> bool:
    """CLAUDE: complete PNG, JPEG, GIF and WebP images and font files only."""
    if ext in FONT_EXTENSIONS:
        return True
    return (data.startswith(b"\x89PNG\r\n\x1a\n") and data.endswith(b"IEND\xaeB`\x82")) \
        or (data.startswith(b"\xff\xd8\xff") and data.rstrip(b"\x00").endswith(b"\xff\xd9")) \
        or data[:6] in (b"GIF87a", b"GIF89a") \
        or (data[:4] == b"RIFF" and data[8:12] == b"WEBP")


def check_claude_files(report: Report) -> None:
    files = git_files()
    if len(files) > 512:
        report.error("CLAUDE", ".", f"{len(files)} files, max 512 (held for a reviewer)")

    folders = {str(p) for _, path in files for p in Path(path).parents if str(p) != "."}
    if len(files) + len(folders) >= 10_000:
        report.error("CLAUDE", ".", "repository must have fewer than 10,000 files and folders")

    seen_lower: dict[str, str] = {}
    total = 0
    for mode, path in files:
        for part in Path(path).parts:
            stem = part.split(".")[0].lower()
            if part.lower() in SYSTEM_FILES:
                report.error("CLAUDE", path, "remove macOS or Windows system files")
            if ":" in part or part.endswith((".", " ")) or stem in WINDOWS_DEVICE_NAMES:
                report.error("CLAUDE", path, "name is not valid on Windows or macOS (Couldn't validate that repository)")
        lower = path.lower()
        if lower in seen_lower and seen_lower[lower] != path:
            report.error("CLAUDE", path, f"differs only by capitalization from {seen_lower[lower]}")
        seen_lower[lower] = path

        if mode == "120000":
            report.error("CLAUDE", path, "commit a regular file, not a symbolic link")
            continue
        if mode == "160000":
            report.error("CLAUDE", path, "Git submodules are not allowed")
            continue

        data = (ROOT / path).read_bytes()
        total += len(data)
        ext = Path(path).suffix.lower()
        if data.startswith(b"version https://git-lfs.github.com/spec/"):
            report.error("CLAUDE", path, "commit the real file, not a Git LFS pointer")
        if len(data) >= 5 * MIB:
            report.error("CLAUDE", path, "every file must be under 5 MiB")
        is_binary = b"\0" in data[:8192]
        if is_binary and not is_allowed_binary(data, ext):
            report.error("CLAUDE", path, "only text, complete PNG/JPEG/GIF/WebP images and fonts are allowed (held for a reviewer)")
        if ext not in IMAGE_EXTENSIONS | FONT_EXTENSIONS and len(data) >= 256 * KIB:
            report.error("CLAUDE", path, "files that are not images or fonts must be under 256 KiB (held for a reviewer)")
        if Path(path).name == ".gitattributes":
            text = data.decode("utf-8", "replace")
            for attr in ("export-ignore", "export-subst", "filter"):
                if re.search(rf"(^|\s)-?{attr}\b", text, re.MULTILINE):
                    report.error("CLAUDE", path, f"remove `{attr}` (Couldn't validate that repository)")
        if Path(path).name in (".npmrc", "bunfig.toml", "uv.toml"):
            report.error("CLAUDE", path, "package-manager config files are blocked or held when the plugin installs packages")

    if total >= 256 * MIB:
        report.error("CLAUDE", ".", "repository must be under 256 MiB unpacked")

    lockfiles = ("package-lock.json", "npm-shrinkwrap.json", "bun.lock", "bun.lockb")
    if (ROOT / "package.json").is_file() and any((ROOT / f).is_file() for f in lockfiles):
        report.error("CLAUDE", "package.json", "a root package.json with a lockfile is held for a reviewer (Dependencies install from a lockfile)")


def check_claude_readme(report: Report) -> None:
    readme = next((p for p in sorted(ROOT.iterdir()) if p.is_file() and p.name.lower().startswith("readme")), None)
    if readme is None:
        report.error("CLAUDE", "README.md", "README missing")
        return
    text = readme.read_text(encoding="utf-8")
    text = re.sub(r"^(```|~~~).*?^\1", "", text, flags=re.MULTILINE | re.DOTALL)
    words = len(re.findall(r"[^\W_]+(?:['’-][^\W_]+)*", text))
    if words < 40:
        report.error("CLAUDE", readme.name, f"README has {words} words outside code blocks, min 40 (README too short)")


# --- consistency across manifests ---------------------------------------------


def plugin_entry(marketplace: dict | None, name) -> dict | None:
    for entry in (marketplace or {}).get("plugins", []):
        if isinstance(entry, dict) and entry.get("name") == name:
            return entry
    return None


def check_consistency(report: Report, manifests: dict[str, dict | None]) -> None:
    portable = manifests[PORTABLE] or {}
    name = portable.get("name")
    claude_entry = plugin_entry(manifests[CLAUDE_MARKETPLACE], name)
    agents_entry = plugin_entry(manifests[AGENTS_MARKETPLACE], name)
    if manifests[CLAUDE_MARKETPLACE] is not None and claude_entry is None:
        report.error("REPO", CLAUDE_MARKETPLACE, f"no plugin entry named {name!r}")
    if manifests[AGENTS_MARKETPLACE] is not None and agents_entry is None:
        report.error("REPO", AGENTS_MARKETPLACE, f"no plugin entry named {name!r}")

    sources = {
        CODEX: manifests[CODEX],
        CLAUDE: manifests[CLAUDE],
        f"{CLAUDE_MARKETPLACE} plugins[{name}]": claude_entry,
    }
    for field in ("name", "version", "description", "author", "homepage", "repository", "keywords", "license"):
        for label, other in sources.items():
            if other is None or field not in other:
                continue
            if other[field] != portable.get(field):
                report.error("REPO", label, f"`{field}` differs from {PORTABLE}")

    openai_interface = portable.get("extensions", {}).get("com.openai", {}).get("interface")
    codex_interface = (manifests[CODEX] or {}).get("interface")
    if openai_interface != codex_interface:
        keys = sorted({*(openai_interface or {}), *(codex_interface or {})})
        diff = [k for k in keys if (openai_interface or {}).get(k) != (codex_interface or {}).get(k)]
        report.error("REPO", CODEX, f"`interface` differs from {PORTABLE} extensions.com.openai.interface: {', '.join(diff)}")

    category = (openai_interface or {}).get("category")
    for label, entry in ((CLAUDE_MARKETPLACE, claude_entry), (AGENTS_MARKETPLACE, agents_entry)):
        if entry and "category" in entry and entry["category"] != category:
            report.error("REPO", label, f"`category` {entry['category']!r} differs from the OpenAI interface {category!r}")

    portable_servers = (manifests[PORTABLE_MCP] or {}).get("mcpServers") or {}
    compat_servers = (manifests[COMPAT_MCP] or {}).get("mcpServers") or {}
    if set(portable_servers) != set(compat_servers):
        report.error("REPO", COMPAT_MCP, f"server names differ from {PORTABLE_MCP}")
    for server, config in portable_servers.items():
        other = compat_servers.get(server)
        if isinstance(config, dict) and isinstance(other, dict) and config.get("url") != other.get("url"):
            report.error("REPO", COMPAT_MCP, f"`{server}.url` differs from {PORTABLE_MCP}")


def check_version_bump(report: Report, base: str) -> None:
    """OPENAI plugin_version_unchanged and CLAUDE "raise version with every release"."""
    tracked = [PORTABLE, CODEX, CLAUDE, CLAUDE_MARKETPLACE, AGENTS_MARKETPLACE, PORTABLE_MCP, COMPAT_MCP]
    diff = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD", "--", *tracked],
                          cwd=ROOT, capture_output=True, text=True)
    if diff.returncode != 0:
        report.warn("REPO", PORTABLE, f"could not compare with {base}: {diff.stderr.strip()}")
        return
    if not diff.stdout.strip():
        return
    old = subprocess.run(["git", "show", f"{base}:{PORTABLE}"], cwd=ROOT, capture_output=True, text=True)
    if old.returncode != 0:
        return
    old_version = json.loads(old.stdout).get("version")
    new_version = json.loads((ROOT / PORTABLE).read_text(encoding="utf-8")).get("version")
    if old_version == new_version:
        report.warn("REPO", PORTABLE, f"manifests changed but `version` is still {new_version}. Raise it before the next release.")


# --- main --------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", help="git ref to compare with, for the version check")
    args = parser.parse_args()

    report = Report()
    manifests = {rel: load_json(report, rel) for rel in
                 (PORTABLE, CODEX, CLAUDE, CLAUDE_MARKETPLACE, AGENTS_MARKETPLACE, PORTABLE_MCP, COMPAT_MCP)}

    portable = manifests[PORTABLE]
    if portable is None:
        report.error("OPENAI", PORTABLE, "root plugin.json is missing")
    else:
        interface = portable.get("extensions", {}).get("com.openai", {}).get("interface")
        check_openai_manifest(report, PORTABLE, portable, interface)
    if manifests[CODEX] is not None:
        check_openai_manifest(report, CODEX, manifests[CODEX], manifests[CODEX].get("interface"))
    check_mcp_manifest(report, PORTABLE_MCP, manifests[PORTABLE_MCP])
    check_mcp_manifest(report, COMPAT_MCP, manifests[COMPAT_MCP])

    check_claude_manifest(report, manifests[CLAUDE])
    check_claude_mcp(report, manifests[COMPAT_MCP])
    check_claude_files(report)
    check_claude_readme(report)

    check_consistency(report, manifests)
    if args.base:
        check_version_bump(report, args.base)

    print(f"\n{report.errors} error(s), {report.warnings} warning(s)")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
