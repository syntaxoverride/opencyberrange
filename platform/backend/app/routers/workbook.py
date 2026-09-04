"""
Workbook management API — upload markdown, rebuild wiki.

All endpoints require admin or instructor role.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.auth import get_current_instructor_user
from app.database import get_db
from app.models import User, Course, CourseLabAssignment, Lab
from app.services import workbook_builder
from app.services.course_wiki import rebuild_affected_course_wikis, rebuild_course_wiki

import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/chapters")
async def list_chapters(
    current_user: User = Depends(get_current_instructor_user),
):
    """List all workbook chapters and their files."""
    try:
        return workbook_builder.list_chapters()
    except Exception as e:
        logger.error("Failed to list chapters: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_chapter(
    file: UploadFile = File(...),
    chapter_dir: str = Form(...),
    section_name: str = Form("Course Weekly Challenges"),
    auto_build: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Upload a ZIP of markdown files for a workbook chapter.

    - **file**: ZIP archive containing .md files
    - **chapter_dir**: Target directory name (e.g. CH_COURSE01_Weekly_Challenges)
    - **section_name**: Top-level nav section name (default: Course Weekly Challenges)
    - **auto_build**: Automatically rebuild the wiki after upload (default: true)
    """
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload must be a .zip file")

    contents = await file.read()
    if len(contents) > 50 * 1024 * 1024:  # 50 MB limit
        raise HTTPException(status_code=400, detail="File too large (max 50 MB)")

    # Extract files
    try:
        result = workbook_builder.extract_upload(contents, chapter_dir)
    except Exception as e:
        logger.error("Upload extraction failed: %s", e)
        raise HTTPException(status_code=400, detail=f"Extraction failed: {e}")

    if not result["files_extracted"]:
        raise HTTPException(status_code=400, detail="No .md files found in the ZIP")

    # Nav is per-track now (driven by the wiki manifest); the rebuild below and
    # the course-wiki rebuild pick the chapter up from the relevant config(s).

    # Auto-build wiki
    if auto_build:
        try:
            build_result = workbook_builder.build_wiki()
            result["build"] = build_result
        except Exception as e:
            logger.warning("Auto-build failed (files were extracted): %s", e)
            result["build_warning"] = str(e)

    # Rebuild any course wikis that reference labs in the uploaded chapter
    try:
        course_results = rebuild_affected_course_wikis(db, chapter_dir)
        if course_results:
            result["course_wikis_rebuilt"] = len(course_results)
    except Exception as e:
        logger.warning("Course wiki rebuild after upload failed: %s", e)

    return result


@router.post("/build")
async def trigger_build(
    current_user: User = Depends(get_current_instructor_user),
):
    """Trigger a manual mkdocs build of the track wikis.

    Returns the structured per-track result (success may be partial). In a
    bake-in deployment the wiki source is not mounted in the backend container,
    so builds run host-side via scripts/deploy-wiki.sh; this endpoint then
    reports success=false with an explanatory output rather than erroring.
    """
    try:
        return workbook_builder.build_wiki()
    except Exception as e:
        logger.error("Build failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/build-all-course-wikis")
async def build_all_course_wikis(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Build wikis for all courses that have a wiki_slug and assigned labs."""
    courses = db.query(Course).filter(Course.wiki_slug.isnot(None)).all()

    results = []
    for course in courses:
        r = rebuild_course_wiki(db, course)
        if r:
            results.append({"slug": course.wiki_slug, "success": r.get("success", False)})

    return {
        "courses_built": len(results),
        "results": results,
    }


@router.delete("/chapter/{chapter_dir}")
async def delete_chapter(
    chapter_dir: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor_user),
):
    """Delete a workbook chapter directory and rebuild the wiki."""
    import os
    import shutil

    target = os.path.join(workbook_builder.DOCS_DIR, chapter_dir)
    if not os.path.isdir(target):
        raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_dir}")

    shutil.rmtree(target)

    # Rebuild wiki (nav will still reference the deleted chapter — mkdocs
    # build will warn but succeed; the nav entry becomes a dead link that
    # can be cleaned up separately or on next upload).
    try:
        build_result = workbook_builder.build_wiki()
        # Also rebuild affected course wikis
        rebuild_affected_course_wikis(db, chapter_dir)
        return {"deleted": chapter_dir, "build": build_result}
    except Exception as e:
        return {"deleted": chapter_dir, "build_warning": str(e)}
