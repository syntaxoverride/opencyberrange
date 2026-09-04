"""Course wiki rebuild orchestration.

Bridges the DB-aware router layer with the file-based workbook_builder.
Called by course endpoints (lab assign/remove) and the workbook upload endpoint
to keep per-course wikis in sync.
"""

import logging
from sqlalchemy.orm import Session

from app.models import Course, CourseLabAssignment, Lab
from app.services import workbook_builder

logger = logging.getLogger(__name__)


def rebuild_course_wiki(db: Session, course: Course) -> dict | None:
    """Gather lab workbook paths and trigger a wiki rebuild for a course.

    Returns the build result dict, or None if the course has no wiki_slug.
    Errors are logged but not raised.
    """
    if not course.wiki_slug:
        return None

    assignments = db.query(CourseLabAssignment).filter(
        CourseLabAssignment.course_id == course.id,
    ).order_by(CourseLabAssignment.sort_order).all()

    workbook_paths = []
    for a in assignments:
        if a.lab and a.lab.workbook:
            workbook_paths.append(a.lab.workbook)

    try:
        result = workbook_builder.build_course_wiki(
            slug=course.wiki_slug,
            course_name=course.name,
            theme_color=course.wiki_theme_color or "blue",
            workbook_paths=workbook_paths,
        )
        if not result.get("success"):
            logger.warning(
                "Course wiki build failed for %s: %s",
                course.wiki_slug, result.get("output", "")[:200],
            )
        return result
    except Exception as e:
        logger.error("Course wiki rebuild error for %s: %s", course.wiki_slug, e)
        return None


def rebuild_affected_course_wikis(db: Session, chapter_dir: str) -> list[dict]:
    """Rebuild all course wikis that reference labs in the given chapter directory.

    Used after a workbook upload to cascade the content change into every
    course wiki that includes labs from the affected chapter.
    """
    affected_courses = db.query(Course).join(
        CourseLabAssignment, CourseLabAssignment.course_id == Course.id
    ).join(Lab, Lab.id == CourseLabAssignment.lab_id).filter(
        Lab.workbook.isnot(None),
        Lab.workbook.like(f"{chapter_dir}/%"),
        Course.wiki_slug.isnot(None),
    ).distinct().all()

    results = []
    for course in affected_courses:
        r = rebuild_course_wiki(db, course)
        if r:
            results.append(r)
    return results
