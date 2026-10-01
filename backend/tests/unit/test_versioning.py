"""
Unit test for floor plan source versioning and publishing engine (Task 2.4).
Verifies draft creation, sequential version incrementing, and version publishing.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.domain.revisions.versioning import SourceVersionPublisher


def test_source_version_publishing_lifecycle():
    publisher = SourceVersionPublisher()
    floor_plan_id = "fp_501"

    # 1. Create draft v1
    v1_draft = publisher.create_draft_version(
        floor_plan_id=floor_plan_id,
        source_type="IFC",
        file_name="4420_ashland_v1.ifc",
        file_storage_path="floor_plans/fp_501/v1.ifc",
        geometry_summary={"total_rooms": 12, "area_sqm": 300.0},
    )
    assert v1_draft.version_no == 1
    assert v1_draft.is_published is False

    # 2. Publish v1
    v1_published = publisher.publish_version(
        floor_plan_id=floor_plan_id,
        version_id=v1_draft.version_id,
        publisher_user_id="usr_mgr_909",
    )
    assert v1_published.is_published is True
    assert v1_published.published_by_user_id == "usr_mgr_909"
    assert v1_published.published_at is not None

    # 3. Create draft v2 (sequential version check)
    v2_draft = publisher.create_draft_version(
        floor_plan_id=floor_plan_id,
        source_type="IFC",
        file_name="4420_ashland_v2.ifc",
        file_storage_path="floor_plans/fp_501/v2.ifc",
        geometry_summary={"total_rooms": 14, "area_sqm": 350.0},
    )
    assert v2_draft.version_no == 2

    # 4. Verify version history list
    versions = publisher.get_source_versions(floor_plan_id)
    assert len(versions) == 2
    assert versions[0].version_no == 1
    assert versions[1].version_no == 2

    print("ALL FLOOR PLAN VERSIONING & PUBLISHING TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_source_version_publishing_lifecycle()
