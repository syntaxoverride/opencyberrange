"""
Workbook builder service — manages markdown uploads and MkDocs wiki builds.

Handles:
  - Extracting uploaded ZIP/markdown files into the workbook source directory
  - Updating the mkdocs.yml navigation entries
  - Running mkdocs build to generate static HTML
  - Listing current chapters and pages
"""

import json
import logging
import os
import re
import shutil
import subprocess
import zipfile
import tempfile
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

# Paths inside the container — these match the volume mounts in docker-compose.
# /workbook  → persistent volume with Workbook/ source + mkdocs.yml
# /wiki_output → shared volume that nginx reads from
WORKBOOK_ROOT = os.environ.get("WORKBOOK_ROOT", "/workbook")
WIKI_OUTPUT = os.environ.get("WIKI_OUTPUT", "/wiki_output")
DOCS_DIR = os.path.join(WORKBOOK_ROOT, "Workbook")

# Track wiki definitions come from the generated registry (single source of
# truth: wikis.yaml -> tools/wiki-gen). slug -> {config, docs_dir, theme, auth}.
# Courses are dynamic (from the DB) and built by build_course_wiki.
_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "..", "wiki_registry.json")


def _load_tracks() -> dict:
    """Track registry from the committed wiki_registry.json. Returns {} if
    absent so callers degrade gracefully rather than crash."""
    try:
        with open(os.path.abspath(_REGISTRY_PATH)) as f:
            return json.load(f).get("tracks", {})
    except Exception:
        return {}


def _ensure_dirs():
    """Create base directories if they don't exist."""
    os.makedirs(DOCS_DIR, exist_ok=True)
    os.makedirs(WIKI_OUTPUT, exist_ok=True)


def _chapter_label_from_dir(dirname: str) -> str:
    """Derive a human-readable label from a directory name.

    Example: CH_COURSE01_Weekly_Challenges → COURSE01 — Weekly Challenges
    """
    # Strip CH_ prefix variants
    label = dirname
    for prefix in ("CH_COURSE", "CH_"):
        if label.startswith(prefix):
            label = label[len(prefix):]
            break

    # Re-attach course number if it was a COURSE prefix
    if dirname.startswith("CH_COURSE"):
        num_match = re.match(r"(\d+)_(.*)", label)
        if num_match:
            label = f"COURSE{num_match.group(1)} \u2014 {num_match.group(2).replace('_', ' ')}"
    else:
        label = label.replace("_", " ")

    return label


def _page_label(filename: str) -> str:
    """Derive a nav label from a markdown filename.

    Example: 03_SNMP_Community_Strings.md → Challenge 3 — SNMP Community Strings
    """
    stem = Path(filename).stem
    match = re.match(r"(\d+)_(.*)", stem)
    if not match:
        return stem.replace("_", " ")

    num = int(match.group(1))
    title = match.group(2).replace("_", " ")

    if num == 0:
        return "Introduction"
    if "chapter_review" in stem.lower():
        return "Chapter Review"

    return f"Challenge {num} \u2014 {title}"


def _build_chapter_nav(chapter_dir: str, files: list[str]) -> list:
    """Build nav entries for a chapter directory."""
    entries = []
    for fname in sorted(files):
        if not fname.endswith(".md"):
            continue
        rel_path = f"{chapter_dir}/{fname}"
        label = _page_label(fname)
        entries.append({label: rel_path})
    return entries


def list_chapters() -> list[dict]:
    """List all chapter directories and their markdown files."""
    _ensure_dirs()
    chapters = []
    if not os.path.isdir(DOCS_DIR):
        return chapters

    for entry in sorted(os.listdir(DOCS_DIR)):
        chapter_path = os.path.join(DOCS_DIR, entry)
        if not os.path.isdir(chapter_path):
            continue

        md_files = sorted(f for f in os.listdir(chapter_path) if f.endswith(".md"))
        chapters.append({
            "directory": entry,
            "label": _chapter_label_from_dir(entry),
            "page_count": len(md_files),
            "files": md_files,
        })

    return chapters


def extract_upload(zip_bytes: bytes, chapter_dir: str) -> dict:
    """Extract a ZIP archive of markdown files into a chapter directory.

    Args:
        zip_bytes: Raw bytes of the uploaded ZIP file.
        chapter_dir: Target directory name under Workbook/ (e.g. CH_COURSE01_Weekly_Challenges).

    Returns:
        dict with keys: chapter_dir, files_extracted, warnings
    """
    _ensure_dirs()
    target = os.path.join(DOCS_DIR, chapter_dir)
    os.makedirs(target, exist_ok=True)

    warnings = []
    extracted = []

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = os.path.join(tmp, "upload.zip")
        with open(zip_path, "wb") as f:
            f.write(zip_bytes)

        # Upload limits (defense against zip bombs / resource exhaustion).
        MAX_ENTRIES = 500
        MAX_MD_BYTES = 2 * 1024 * 1024        # 2 MB per markdown file
        MAX_TOTAL_BYTES = 50 * 1024 * 1024    # 50 MB uncompressed total
        total_bytes = 0

        with zipfile.ZipFile(zip_path, "r") as zf:
            entries = [
                i for i in zf.infolist()
                if not (i.is_dir() or i.filename.startswith("__MACOSX"))
            ]
            if len(entries) > MAX_ENTRIES:
                raise ValueError(f"Archive has too many files ({len(entries)} > {MAX_ENTRIES})")
            for info in entries:
                basename = os.path.basename(info.filename)
                if not basename.endswith(".md"):
                    warnings.append(f"Skipped non-markdown file: {basename}")
                    continue
                if info.file_size > MAX_MD_BYTES:
                    warnings.append(f"Skipped oversized file: {basename} ({info.file_size} bytes)")
                    continue
                # Sanitize filename
                safe_name = re.sub(r"[^\w.\-]", "_", basename)
                dest = os.path.join(target, safe_name)
                # Bounded read: defends against a zip entry whose header understates
                # its real uncompressed size.
                with zf.open(info) as src:
                    data = src.read(MAX_MD_BYTES + 1)
                if len(data) > MAX_MD_BYTES:
                    warnings.append(f"Skipped oversized file: {basename}")
                    continue
                total_bytes += len(data)
                if total_bytes > MAX_TOTAL_BYTES:
                    raise ValueError(f"Archive uncompressed size exceeds {MAX_TOTAL_BYTES} bytes")
                with open(dest, "wb") as dst:
                    dst.write(data)
                extracted.append(safe_name)

    return {
        "chapter_dir": chapter_dir,
        "files_extracted": sorted(extracted),
        "warnings": warnings,
    }




def _range_index_html(tracks: dict) -> str:
    items = "\n".join(
        f'    <li><a href="/wiki/range/{slug}/">{slug}</a></li>'
        for slug, t in sorted(tracks.items()) if t.get("auth") != "admin"
    )
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">\n'
            "<title>OpenCyberRange Wikis</title></head><body>\n"
            "<h1>OpenCyberRange Wikis</h1>\n"
            "<p>General range tracks. Course material is not listed here.</p>\n"
            f"<ul>\n{items}\n</ul>\n</body></html>\n")


def build_wiki() -> dict:
    """Build every track wiki from the registry into the namespaced layout
    (WIKI_OUTPUT/range/<slug>) and write the /wiki/ landing index. Course
    wikis are built separately by build_course_wiki.

    Returns:
        dict with keys: success, output, duration_seconds, results
    """
    import time
    _ensure_dirs()
    start = time.monotonic()

    tracks = _load_tracks()
    results = []
    for slug, t in sorted(tracks.items()):
        config_path = os.path.join(WORKBOOK_ROOT, t["config"])
        output_dir = os.path.join(WIKI_OUTPUT, "range", slug)
        r = _build_single_wiki(config_path, output_dir)
        r["slug"] = slug
        results.append(r)

    try:
        os.makedirs(WIKI_OUTPUT, exist_ok=True)
        with open(os.path.join(WIKI_OUTPUT, "index.html"), "w") as f:
            f.write(_range_index_html(tracks))
    except Exception as e:
        logger.warning("failed to write wiki landing index: %s", e)

    duration = round(time.monotonic() - start, 2)
    failed = [r for r in results if not r["success"]]
    msg = f"built {len(results) - len(failed)}/{len(results)} track wikis"
    if failed:
        msg += f"; failed: {', '.join(r['slug'] for r in failed)}"
    return {
        "success": not failed,
        "output": msg,
        "duration_seconds": duration,
        "results": results,
    }


def _build_single_wiki(config_file: str, output_dir: str) -> dict:
    """Build a single MkDocs site from the given config file.

    Args:
        config_file: Absolute path to the mkdocs YAML config.
        output_dir: Absolute path for the built HTML output.

    Returns:
        dict with keys: success, output, duration_seconds, config
    """
    import time

    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(config_file):
        return {
            "success": False,
            "output": f"Config not found: {config_file}",
            "duration_seconds": 0,
            "config": config_file,
        }

    start = time.monotonic()
    try:
        result = subprocess.run(
            [
                "mkdocs", "build",
                "--config-file", config_file,
                "--site-dir", output_dir,
                "--clean",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=WORKBOOK_ROOT,
        )
        duration = round(time.monotonic() - start, 2)

        if result.returncode != 0:
            logger.error("mkdocs build failed for %s: %s", config_file, result.stderr)
            return {
                "success": False,
                "output": result.stderr or result.stdout,
                "duration_seconds": duration,
                "config": config_file,
            }

        logger.info("mkdocs build for %s completed in %.2fs", config_file, duration)
        return {
            "success": True,
            "output": result.stdout,
            "duration_seconds": duration,
            "config": config_file,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": f"Build timed out after 120 seconds: {config_file}",
            "duration_seconds": 120,
            "config": config_file,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "output": "mkdocs command not found. Is it installed?",
            "duration_seconds": 0,
            "config": config_file,
        }




# ── Dynamic course config generation ──────────────────────────────

# Template for the mkdocs config — everything except site_name, theme color, and nav.
_MKDOCS_TEMPLATE = {
    "site_description": "",
    "site_url": "",
    "docs_dir": "Workbook",
    "theme": {
        "name": "material",
        "palette": [
            {
                "scheme": "slate",
                "primary": "blue",
                "accent": "blue",
                "toggle": {
                    "icon": "material/brightness-7",
                    "name": "Switch to light mode",
                },
            },
            {
                "scheme": "default",
                "primary": "blue",
                "accent": "blue",
                "toggle": {
                    "icon": "material/brightness-4",
                    "name": "Switch to dark mode",
                },
            },
        ],
        "features": [
            "content.code.copy",
            "content.code.annotate",
            "navigation.instant",
            "navigation.tracking",
            "navigation.sections",
            "navigation.expand",
            "navigation.top",
            "search.suggest",
            "search.highlight",
            "toc.follow",
        ],
    },
    "plugins": ["search"],
    "markdown_extensions": [
        "admonition",
        "pymdownx.details",
        {
            "pymdownx.superfences": {
                "custom_fences": [
                    {
                        "name": "mermaid",
                        "class": "mermaid",
                        "format": "!!python/name:pymdownx.superfences.fence_code_format",
                    }
                ]
            }
        },
        {"pymdownx.highlight": {"anchor_linenums": True}},
        "pymdownx.inlinehilite",
        {"pymdownx.tabbed": {"alternate_style": True}},
        "tables",
        "attr_list",
        "md_in_html",
        {"pymdownx.tasklist": {"custom_checkbox": True}},
        {
            "pymdownx.emoji": {
                "emoji_index": "!!python/name:material.extensions.emoji.twemoji",
                "emoji_generator": "!!python/name:material.extensions.emoji.to_svg",
            }
        },
    ],
    "extra_css": ["stylesheets/extra.css?v=4"],
    "extra_javascript": [
        "javascripts/mermaid-fix.js?v=4",
        "https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.2/html2pdf.bundle.min.js",
        "javascripts/pdf-export.js?v=2",
    ],
}


def _write_yaml_with_python_tags(config: dict, path: str):
    """Write a mkdocs config to disk, restoring !!python/name tags.

    PyYAML's safe_dump cannot emit !!python/name tags, so we dump first
    then do string replacements for the known tags.
    """
    raw = yaml.dump(config, default_flow_style=False, allow_unicode=True, sort_keys=False)
    # Restore !!python/name tags that yaml.dump quoted as strings
    raw = raw.replace(
        "format: '!!python/name:pymdownx.superfences.fence_code_format'",
        "format: !!python/name:pymdownx.superfences.fence_code_format",
    )
    raw = raw.replace(
        "emoji_index: '!!python/name:material.extensions.emoji.twemoji'",
        "emoji_index: !!python/name:material.extensions.emoji.twemoji",
    )
    raw = raw.replace(
        "emoji_generator: '!!python/name:material.extensions.emoji.to_svg'",
        "emoji_generator: !!python/name:material.extensions.emoji.to_svg",
    )
    with open(path, "w") as f:
        f.write(raw)


def generate_course_config(
    slug: str,
    course_name: str,
    theme_color: str,
    workbook_paths: list[str],
) -> str:
    """Generate a course-specific mkdocs.yml from assigned lab workbook paths.

    Args:
        slug: Course wiki slug (e.g. "sec101").
        course_name: Human-readable course name for site_name.
        theme_color: Material theme primary color (e.g. "deep-orange").
        workbook_paths: Lab workbook paths like "CH01_Enumeration/01_Basic_Port_Scan/".

    Returns:
        Absolute path to the generated config file.
    """
    import copy

    _ensure_dirs()

    # Derive unique chapter directories from workbook paths
    chapter_dirs = []
    seen = set()
    for wp in workbook_paths:
        # First path component is the chapter directory
        chapter = wp.strip("/").split("/")[0] if wp else ""
        if chapter and chapter not in seen:
            seen.add(chapter)
            chapter_dirs.append(chapter)

    # Build nav from chapter directories
    nav = []
    for chapter_dir in chapter_dirs:
        chapter_path = os.path.join(DOCS_DIR, chapter_dir)
        if not os.path.isdir(chapter_path):
            continue
        md_files = sorted(f for f in os.listdir(chapter_path) if f.endswith(".md"))
        if not md_files:
            continue
        label = _chapter_label_from_dir(chapter_dir)
        entries = _build_chapter_nav(chapter_dir, md_files)
        nav.append({label: entries})

    # Build the config
    config = copy.deepcopy(_MKDOCS_TEMPLATE)
    config["site_name"] = course_name
    config["site_dir"] = f"_site_course_{slug}"

    # Set theme color
    for palette in config["theme"]["palette"]:
        palette["primary"] = theme_color
        palette["accent"] = theme_color

    config["nav"] = nav

    # Write to disk
    config_path = os.path.join(WORKBOOK_ROOT, f"mkdocs-course-{slug}.yml")
    _write_yaml_with_python_tags(config, config_path)

    logger.info("Generated course wiki config: %s (%d chapters)", config_path, len(nav))
    return config_path


def build_course_wiki(
    slug: str,
    course_name: str,
    theme_color: str,
    workbook_paths: list[str],
) -> dict:
    """Generate a mkdocs config and build a course wiki.

    Returns:
        Build result dict with keys: success, output, duration_seconds, slug, config
    """
    config_path = generate_course_config(slug, course_name, theme_color, workbook_paths)
    output_dir = os.path.join(WIKI_OUTPUT, "course", slug)
    result = _build_single_wiki(config_path, output_dir)
    result["slug"] = slug
    return result
