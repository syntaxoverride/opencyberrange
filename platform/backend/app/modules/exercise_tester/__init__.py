"""
Exercise Tester manifest (dev-only).

Automated exercise validation harness for admins/instructors. Stripped from
every shipped edition (pipeline/manifests/platform.yaml) and hidden from client
admin panels via OCR_DEV_TOOLS=0. Extends the /api/admin and /api/instructor
prefixes, so it is mounted after the core routers.
"""

from app.modules import ModuleManifest, RouterSpec

MANIFEST = ModuleManifest(
    name="exercise_tester",
    label="Exercise Tester",
    description="Automated exercise validation harness (dev-only)",
    requires="app.routers.exercise_tester",
    kind="devtool",
    routers=[
        RouterSpec("app.routers.exercise_tester", [
            ("/api/admin", "Exercise Tester"),
            ("/api/instructor", "Exercise Tester (Instructor)"),
        ]),
    ],
)
