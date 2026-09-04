"""
Workbook upload manifest (dev-only).

ZIP upload + MkDocs build for authoring workbooks. Stripped from shipped
editions (pipeline/manifests/platform.yaml) and hidden from client admin panels
via OCR_DEV_TOOLS=0.
"""

from app.modules import ModuleManifest, RouterSpec

MANIFEST = ModuleManifest(
    name="workbook",
    label="Workbook Upload",
    description="Workbook ZIP upload + MkDocs build (dev-only)",
    requires="app.routers.workbook",
    kind="devtool",
    routers=[
        RouterSpec("app.routers.workbook", [("/api/admin/workbook", "Workbook")]),
    ],
)
