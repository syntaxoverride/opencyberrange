"""
Lab ZIP upload validation and extraction service.

Handles the complete pipeline from receiving a ZIP file to having
validated files on disk ready for Docker to build and run.
"""

import io
import os
import re
import shutil
import stat
import zipfile

import yaml


MAX_ZIP_SIZE = 100 * 1024 * 1024       # 100 MB compressed
MAX_EXTRACTED_SIZE = 500 * 1024 * 1024  # 500 MB uncompressed
REQUIRED_FILES = ["lab.yaml", "docker-compose.yml"]
VALID_DIFFICULTIES = {"beginner", "intermediate", "advanced"}


class ZipValidationError(Exception):
    """Raised when ZIP validation fails."""
    pass


def generate_slug(name: str, track: str) -> str:
    """Generate a URL-safe slug from a lab name and track.

    Returns e.g. 'linux-my-ssh-exercise' from name='My SSH Exercise', track='linux'.
    """
    # Lowercase and replace non-alphanumeric with hyphens
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    # Remove consecutive hyphens
    base = re.sub(r"-{2,}", "-", base)
    slug = f"{track.lower()}-{base}"
    # Validate format
    if not re.match(r"^[a-z][a-z0-9-]*$", slug):
        raise ZipValidationError(
            f"Generated slug '{slug}' is invalid. Lab name must start with "
            f"a letter and contain only letters, numbers, spaces, and hyphens."
        )
    # Cap length
    if len(slug) > 80:
        slug = slug[:80].rstrip("-")
    return slug


def validate_and_extract_lab_zip(contents: bytes, target_dir: str) -> dict:
    """Validate a lab ZIP file and extract it to target_dir.

    Args:
        contents: Raw bytes of the uploaded ZIP file.
        target_dir: Absolute path to extract files into (must not exist).

    Returns:
        dict with keys:
            lab_data:        parsed lab.yaml as dict
            compose_content: raw docker-compose.yml string
            file_count:      number of files extracted
            warnings:        list of non-fatal warning strings

    Raises:
        ZipValidationError: on any validation failure.
    """
    warnings = []

    # --- Size check ---
    if len(contents) > MAX_ZIP_SIZE:
        raise ZipValidationError(
            f"ZIP file too large ({len(contents) // (1024*1024)} MB). "
            f"Maximum is {MAX_ZIP_SIZE // (1024*1024)} MB."
        )

    # --- Open ZIP ---
    try:
        zf = zipfile.ZipFile(io.BytesIO(contents))
    except zipfile.BadZipFile:
        raise ZipValidationError("File is not a valid ZIP archive.")

    # --- Zip bomb check ---
    total_uncompressed = sum(info.file_size for info in zf.infolist())
    if total_uncompressed > MAX_EXTRACTED_SIZE:
        raise ZipValidationError(
            f"Uncompressed size too large ({total_uncompressed // (1024*1024)} MB). "
            f"Maximum is {MAX_EXTRACTED_SIZE // (1024*1024)} MB."
        )

    # --- Path traversal check (pre-extraction) ---
    for name in zf.namelist():
        if ".." in name or name.startswith("/"):
            raise ZipValidationError(f"Unsafe path in ZIP: {name}")

    # --- Filter out macOS resource forks ---
    entries = [n for n in zf.namelist() if not n.startswith("__MACOSX/")]

    # --- Detect single-root-directory wrapper ---
    top_level = set()
    for name in entries:
        parts = name.split("/")
        top_level.add(parts[0])

    strip_prefix = ""
    if len(top_level) == 1:
        candidate = list(top_level)[0]
        if any(n.startswith(candidate + "/") for n in entries):
            strip_prefix = candidate + "/"

    # --- Build adjusted name set ---
    adjusted = set()
    for name in entries:
        if name.startswith(strip_prefix):
            rel = name[len(strip_prefix):]
            if rel:
                adjusted.add(rel)

    # --- Required files ---
    for req in REQUIRED_FILES:
        if req not in adjusted:
            raise ZipValidationError(
                f"Missing required file: {req}. "
                f"Your ZIP must contain both lab.yaml and docker-compose.yml."
            )

    # --- Check for at least one Dockerfile ---
    has_dockerfile = any(
        os.path.basename(n) == "Dockerfile" for n in adjusted
    )
    if not has_dockerfile:
        warnings.append(
            "No Dockerfile found. Exercises typically need a containers/ "
            "directory with at least one Dockerfile."
        )

    # --- Parse lab.yaml ---
    yaml_raw = zf.read(strip_prefix + "lab.yaml").decode("utf-8")
    try:
        lab_data = yaml.safe_load(yaml_raw) or {}
    except yaml.YAMLError as e:
        raise ZipValidationError(f"Invalid lab.yaml syntax: {e}")

    if not lab_data.get("name"):
        raise ZipValidationError(
            "lab.yaml must have a 'name' field."
        )

    if not lab_data.get("flag"):
        warnings.append(
            "No 'flag' field in lab.yaml. The exercise won't be completable "
            "without a flag for students to submit."
        )

    test_config = lab_data.get("test", {})
    if not test_config.get("steps"):
        warnings.append(
            "No 'test.steps' in lab.yaml. The automated tester can only "
            "perform generic checks without custom solve steps."
        )

    difficulty = lab_data.get("difficulty", "beginner")
    if difficulty not in VALID_DIFFICULTIES:
        warnings.append(
            f"Unknown difficulty '{difficulty}'. "
            f"Valid values: {', '.join(sorted(VALID_DIFFICULTIES))}. "
            f"Defaulting to 'beginner'."
        )
        lab_data["difficulty"] = "beginner"

    # --- Parse docker-compose.yml ---
    compose_raw = zf.read(strip_prefix + "docker-compose.yml").decode("utf-8")
    try:
        compose_data = yaml.safe_load(compose_raw) or {}
    except yaml.YAMLError as e:
        raise ZipValidationError(f"Invalid docker-compose.yml syntax: {e}")

    services = compose_data.get("services", {})
    if not services:
        raise ZipValidationError(
            "docker-compose.yml must define at least one service."
        )

    for svc_name, svc_def in services.items():
        labels = svc_def.get("labels", {})
        if "ip_offset" not in labels:
            warnings.append(
                f"Service '{svc_name}' missing 'labels.ip_offset'. "
                f"Container won't get a static IP address."
            )
        build = svc_def.get("build", {})
        if isinstance(build, dict):
            ctx = build.get("context", "")
            # Normalize: remove leading ./ for comparison
            ctx_clean = ctx.lstrip("./")
            if ctx_clean and ctx_clean + "/" not in adjusted and not any(
                a.startswith(ctx_clean + "/") for a in adjusted
            ):
                warnings.append(
                    f"Service '{svc_name}' build context '{ctx}' "
                    f"not found in ZIP."
                )

    # --- Extract to disk ---
    if os.path.exists(target_dir):
        raise ZipValidationError(
            f"Lab directory already exists on disk. "
            f"If re-uploading, delete the existing exercise first."
        )

    os.makedirs(target_dir, mode=0o755)
    file_count = 0

    try:
        for info in zf.infolist():
            if info.filename.startswith("__MACOSX/"):
                continue
            if not info.filename.startswith(strip_prefix):
                continue
            relative = info.filename[len(strip_prefix):]
            if not relative:
                continue

            target_path = os.path.join(target_dir, relative)
            resolved = os.path.realpath(target_path)

            # Post-extraction path traversal check
            if not resolved.startswith(os.path.realpath(target_dir)):
                raise ZipValidationError(f"Path traversal detected: {relative}")

            if relative.endswith("/"):
                os.makedirs(target_path, mode=0o755, exist_ok=True)
            else:
                parent = os.path.dirname(target_path)
                if parent and not os.path.exists(parent):
                    os.makedirs(parent, mode=0o755, exist_ok=True)
                with open(target_path, "wb") as f:
                    f.write(zf.read(info.filename))
                # Make scripts/entrypoints executable
                if relative.endswith((".sh", ".py")):
                    os.chmod(target_path, 0o755)
                else:
                    os.chmod(target_path, 0o644)
                file_count += 1

    except ZipValidationError:
        shutil.rmtree(target_dir, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(target_dir, ignore_errors=True)
        raise ZipValidationError(f"Extraction failed: {e}")

    return {
        "lab_data": lab_data,
        "compose_content": compose_raw,
        "file_count": file_count,
        "warnings": warnings,
    }
