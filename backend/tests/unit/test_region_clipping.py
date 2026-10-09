import math
import sys
from pathlib import Path
import pytest

_backend_root = str(Path(__file__).resolve().parent.parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from pydantic import ValidationError
from shapely.geometry import MultiPolygon, Polygon
from shapely.validation import make_valid

from app.domain.geometry.region_clipping import (

    Point2DModel,
    RegionValidationStatus,
    ValidateRegionRequest,
    ValidatedRegionResponse,
    clip_region_to_boundary,
    construct_shapely_polygon,
    extract_authoritative_boundary_from_report,
)


@pytest.fixture
def sample_rectangular_boundary():
    """Authoritative room boundary: 10m x 8m rectangle from (0,0) to (10,8). Area = 80m²."""
    return Polygon([(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)])


@pytest.fixture
def sample_l_shaped_boundary():
    """Authoritative L-shaped room: 8m x 8m with a 4m x 4m cutout. Area = 48m²."""
    return Polygon([
        (0.0, 0.0),
        (8.0, 0.0),
        (8.0, 4.0),
        (4.0, 4.0),
        (4.0, 8.0),
        (0.0, 8.0),
    ])


def test_1_valid_polygon_fully_inside_room(sample_rectangular_boundary):
    """Test 1: User polygon fully inside room (4m x 3m rectangle from (2,2) to (6,5)). Area = 12m²."""
    user_pts = [
        Point2DModel(x=2.0, y=2.0),
        Point2DModel(x=6.0, y=2.0),
        Point2DModel(x=6.0, y=5.0),
        Point2DModel(x=2.0, y=5.0),
    ]

    result = clip_region_to_boundary(
        user_points=user_pts,
        boundary_geom=sample_rectangular_boundary,
        floor_plan_id="fp_test_101",
        storey_name="Level 1",
    )

    assert result.is_valid is True
    assert result.is_clipped is False
    assert result.status == RegionValidationStatus.VALID
    assert abs(result.area_sqm - 12.0) < 1e-3
    assert abs(result.perimeter_m - 14.0) < 1e-3
    assert result.centroid is not None
    assert abs(result.centroid.x - 4.0) < 1e-3
    assert abs(result.centroid.y - 3.5) < 1e-3


def test_2_polygon_partly_outside_room_is_clipped(sample_rectangular_boundary):
    """Test 2: User polygon partly outside room (extends from x=5 to x=15; room ends at x=10)."""
    # Submitted: 10m wide (5 to 15) x 4m high (2 to 6) -> 40m²
    # Clipped to (5 to 10) x (2 to 6) -> 5m x 4m = 20m²
    user_pts = [
        Point2DModel(x=5.0, y=2.0),
        Point2DModel(x=15.0, y=2.0),
        Point2DModel(x=15.0, y=6.0),
        Point2DModel(x=5.0, y=6.0),
    ]

    result = clip_region_to_boundary(
        user_points=user_pts,
        boundary_geom=sample_rectangular_boundary,
        floor_plan_id="fp_test_102",
        storey_name="Level 1",
    )

    assert result.is_valid is True
    assert result.is_clipped is True
    assert result.status == RegionValidationStatus.CLIPPED
    assert abs(result.area_sqm - 20.0) < 1e-3
    assert result.area_sqm < 40.0, "Clipped area must be smaller than submitted area"
    # Centroid of (5..10, 2..6) is (7.5, 4.0)
    assert result.centroid is not None
    assert abs(result.centroid.x - 7.5) < 1e-3
    assert abs(result.centroid.y - 4.0) < 1e-3


def test_3_polygon_completely_outside_room(sample_rectangular_boundary):
    """Test 3: User polygon completely outside room boundary (x=20 to 25, room is x=0..10)."""
    user_pts = [
        Point2DModel(x=20.0, y=20.0),
        Point2DModel(x=25.0, y=20.0),
        Point2DModel(x=25.0, y=25.0),
        Point2DModel(x=20.0, y=25.0),
    ]

    result = clip_region_to_boundary(
        user_points=user_pts,
        boundary_geom=sample_rectangular_boundary,
        floor_plan_id="fp_test_103",
        storey_name="Level 1",
    )

    assert result.is_valid is False
    assert result.status == RegionValidationStatus.NO_OVERLAP
    assert result.area_sqm == 0.0
    assert len(result.clipped_points) == 0


def test_4_self_intersecting_bowtie_polygon_repaired_by_make_valid(sample_rectangular_boundary):
    """Test 4: Self-intersecting / bowtie polygon is repaired by make_valid without crashing."""
    # Bowtie crossing at center: (1,1) -> (5,5) -> (5,1) -> (1,5)
    user_pts = [
        Point2DModel(x=1.0, y=1.0),
        Point2DModel(x=5.0, y=5.0),
        Point2DModel(x=5.0, y=1.0),
        Point2DModel(x=1.0, y=5.0),
    ]

    result = clip_region_to_boundary(
        user_points=user_pts,
        boundary_geom=sample_rectangular_boundary,
        floor_plan_id="fp_test_104",
        storey_name="Level 1",
    )

    assert result.is_valid is True
    assert result.area_sqm > 0.0, "make_valid should repair bowtie into valid polygonal area"


def test_5_polygon_with_insufficient_vertices_rejected():
    """Test 5: Polygon with less than 3 points raises validation error."""
    with pytest.raises(ValidationError):
        ValidateRegionRequest(
            floor_plan_id="fp_test_105",
            world_points=[
                Point2DModel(x=1.0, y=1.0),
                Point2DModel(x=2.0, y=2.0),
            ],
        )


def test_6_non_finite_coordinates_rejected():
    """Test 6: Coordinates with NaN or Infinity are rejected cleanly by Pydantic validators."""
    with pytest.raises(ValidationError):
        Point2DModel(x=float("nan"), y=2.0)

    with pytest.raises(ValidationError):
        Point2DModel(x=1.0, y=float("inf"))


def test_7_invalid_authoritative_boundary_repaired_by_make_valid():
    """Test 7: If the authoritative boundary geometry is self-intersecting, make_valid repairs it."""
    # Self-intersecting bowtie boundary
    invalid_boundary = Polygon([(0.0, 0.0), (10.0, 10.0), (10.0, 0.0), (0.0, 10.0)])
    assert not invalid_boundary.is_valid

    # Placed inside the left triangular lobe (0,0) -> (5,5) -> (0,10)
    user_pts = [
        Point2DModel(x=0.5, y=4.0),
        Point2DModel(x=2.0, y=4.0),
        Point2DModel(x=2.0, y=6.0),
        Point2DModel(x=0.5, y=6.0),
    ]

    result = clip_region_to_boundary(
        user_points=user_pts,
        boundary_geom=invalid_boundary,
        floor_plan_id="fp_test_107",
    )

    assert result.is_valid is True
    assert result.area_sqm > 0.0



def test_8_multipolygon_boundary_handling():
    """Test 8: Boundary composed of multiple disconnected spaces (MultiPolygon)."""
    room_a = Polygon([(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)])
    room_b = Polygon([(6.0, 0.0), (10.0, 0.0), (10.0, 4.0), (6.0, 4.0)])
    multi_boundary = MultiPolygon([room_a, room_b])

    # User polygon spanning across both rooms (x=2 to 8, y=1 to 3)
    user_pts = [
        Point2DModel(x=2.0, y=1.0),
        Point2DModel(x=8.0, y=1.0),
        Point2DModel(x=8.0, y=3.0),
        Point2DModel(x=2.0, y=3.0),
    ]

    result = clip_region_to_boundary(
        user_points=user_pts,
        boundary_geom=multi_boundary,
        floor_plan_id="fp_test_108",
    )

    assert result.is_valid is True
    assert result.is_clipped is True
    # Area inside room_a: (2..4) x (1..3) = 2 x 2 = 4m²
    # Area inside room_b: (6..8) x (1..3) = 2 x 2 = 4m²
    # Total clipped area = 8m² (submitted was 6 x 2 = 12m²)
    assert abs(result.area_sqm - 8.0) < 1e-3
    assert result.clipped_polygons is not None
    assert len(result.clipped_polygons) == 2


def test_9_storey_specific_boundary_isolation():
    """Test 9: Selected storey uses only that storey's architectural space geometry."""
    report_dict = {
        "floor_plan_name": "Multi-Storey Office Building",
        "available_storeys": [{"name": "Ground Floor"}, {"name": "First Floor"}],
        "all_elements_geometry": [
            {
                "id": "space_gf_1",
                "category": "SPACE",
                "storey_name": "Ground Floor",
                "type": "Polygon",
                "coordinates": [[[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [0.0, 5.0], [0.0, 0.0]]],
            },
            {
                "id": "space_ff_1",
                "category": "SPACE",
                "storey_name": "First Floor",
                "type": "Polygon",
                "coordinates": [[[10.0, 10.0], [20.0, 10.0], [20.0, 20.0], [10.0, 20.0], [10.0, 10.0]]],
            },
        ],
    }

    # Extract boundary for Ground Floor (0..5, 0..5)
    gf_boundary, gf_storey = extract_authoritative_boundary_from_report(report_dict, "Ground Floor")
    assert gf_storey == "Ground Floor"
    assert gf_boundary is not None
    assert abs(gf_boundary.area - 25.0) < 1e-3

    # Extract boundary for First Floor (10..20, 10..20)
    ff_boundary, ff_storey = extract_authoritative_boundary_from_report(report_dict, "First Floor")
    assert ff_storey == "First Floor"
    assert ff_boundary is not None
    assert abs(ff_boundary.area - 100.0) < 1e-3

    # User polygon at (2..4, 2..4) overlaps GF, but NOT FF
    user_pts = [
        Point2DModel(x=2.0, y=2.0),
        Point2DModel(x=4.0, y=2.0),
        Point2DModel(x=4.0, y=4.0),
        Point2DModel(x=2.0, y=4.0),
    ]

    res_gf = clip_region_to_boundary(user_pts, gf_boundary, "fp_multi", "Ground Floor")
    assert res_gf.is_valid is True
    assert abs(res_gf.area_sqm - 4.0) < 1e-3

    res_ff = clip_region_to_boundary(user_pts, ff_boundary, "fp_multi", "First Floor")
    assert res_ff.is_valid is False
    assert res_ff.status == RegionValidationStatus.NO_OVERLAP


def test_10_coordinate_system_consistency_with_task_6_2():
    """
    Test 10: Proves world-metric coordinates produced by Task 6.2 (screenToWorld)
    are directly processed by Task 6.3 backend without scaling drift.
    """
    # Boundary: (0, 0) to (12.0, 8.0)
    boundary = Polygon([(0.0, 0.0), (12.0, 0.0), (12.0, 8.0), (0.0, 8.0)])

    # World points matching client-side freehandManager output:
    world_points = [
        Point2DModel(x=1.500, y=1.200),
        Point2DModel(x=8.500, y=1.200),
        Point2DModel(x=8.500, y=6.800),
        Point2DModel(x=1.500, y=6.800),
    ]

    expected_area = (8.500 - 1.500) * (6.800 - 1.200)  # 7.0 * 5.6 = 39.2 m²
    expected_perimeter = 2 * (7.0 + 5.6)  # 25.2 m

    result = clip_region_to_boundary(
        user_points=world_points,
        boundary_geom=boundary,
        floor_plan_id="fp_test_110",
    )

    assert result.is_valid is True
    assert result.is_clipped is False
    assert abs(result.area_sqm - expected_area) < 1e-2
    assert abs(result.perimeter_m - expected_perimeter) < 1e-2
    assert result.centroid is not None
    assert abs(result.centroid.x - 5.0) < 1e-2
    assert abs(result.centroid.y - 4.0) < 1e-2
