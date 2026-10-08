import {
  calculateFloorPlanOrigin,
  normalizePoint,
  normalizePolygonRing,
  normalizeRenderGeometry,
  normalizeFloorPlanRenderModel,
} from "./coordinateNormalization";
import { FloorPlanRenderModel, RenderGeometry } from "../editor/renderer/renderTypes";
import { fitBounds } from "../editor/canvas/viewport";

function assert(condition: boolean, message: string) {
  if (!condition) throw new Error(`Assertion failed: ${message}`);
}

export function runCoordinateNormalizationTests(): { passed: number; total: number } {
  let passed = 0;
  let total = 0;

  const test = (name: string, fn: () => void) => {
    total++;
    try {
      fn();
      passed++;
    } catch (e: any) {
      console.error(`FAILED: ${name} - ${e.message}`);
      throw e;
    }
  };

  test("Test 1: Normalizes boundary polygon to start at (0, 0)", () => {
    const rawBoundary = [
      { x: 100, y: 200 },
      { x: 110, y: 200 },
      { x: 110, y: 208 },
      { x: 100, y: 208 },
    ];
    const origin = calculateFloorPlanOrigin(rawBoundary);
    assert(origin.x === 100 && origin.y === 200, "Origin calculation incorrect");
    const normalized = rawBoundary.map((pt) => normalizePoint(pt, origin));
    assert(normalized[0].x === 0 && normalized[0].y === 0, "Point 0 incorrect");
    assert(normalized[1].x === 10 && normalized[1].y === 0, "Point 1 incorrect");
  });

  test("Test 2: Normalizes wall start and end points correctly", () => {
    const origin = { x: 100, y: 200 };
    const p1 = normalizePoint({ x: 103, y: 201 }, origin);
    const p2 = normalizePoint({ x: 110, y: 201 }, origin);
    assert(p1.x === 3 && p1.y === 1, "p1 incorrect");
    assert(p2.x === 10 && p2.y === 1, "p2 incorrect");
  });

  test("Test 3: Normalizes furniture position correctly", () => {
    const origin = { x: 100, y: 200 };
    const furn = normalizePoint({ x: 105, y: 204 }, origin);
    assert(furn.x === 5 && furn.y === 4, "furniture pos incorrect");
  });

  test("Test 4: Space polygon and furniture preserve relative placement", () => {
    const rawModel: FloorPlanRenderModel = {
      id: "fp_test",
      boundary: [
        { x: 100, y: 200 },
        { x: 120, y: 200 },
        { x: 120, y: 215 },
        { x: 100, y: 215 },
      ],
      walls: [],
      doors: [],
      windows: [],
      columns: [],
      spaces: [
        {
          id: "space_1",
          name: "Office 101",
          geometry: {
            polygons: [
              {
                exterior: [
                  { x: 102, y: 202 },
                  { x: 110, y: 202 },
                  { x: 110, y: 210 },
                  { x: 102, y: 210 },
                ],
              },
            ],
          },
        },
      ],
      furniture: [
        {
          id: "furn_1",
          itemType: "DESK",
          position: { x: 105, y: 205 },
          widthMeters: 1.5,
          depthMeters: 0.8,
          rotationDeg: 0,
        },
      ],
    };
    const normalized = normalizeFloorPlanRenderModel(rawModel);
    assert(normalized.worldOrigin?.x === 100 && normalized.worldOrigin?.y === 200, "worldOrigin incorrect");
    const spacePt = normalized.spaces[0].geometry.polygons[0].exterior[0];
    const furnPos = normalized.furniture[0].position;
    assert(furnPos.x - spacePt.x === 3, "Relative dx failed");
    assert(furnPos.y - spacePt.y === 3, "Relative dy failed");
  });

  test("Test 5: MultiPolygon geometry and holes remain intact", () => {
    const origin = { x: 50, y: 50 };
    const rawGeom: RenderGeometry = {
      polygons: [
        {
          exterior: [
            { x: 50, y: 50 },
            { x: 70, y: 50 },
            { x: 70, y: 70 },
            { x: 50, y: 70 },
          ],
          holes: [
            [
              { x: 55, y: 55 },
              { x: 60, y: 55 },
              { x: 60, y: 60 },
              { x: 55, y: 60 },
            ],
          ],
        },
      ],
    };
    const normalized = normalizeRenderGeometry(rawGeom, origin)!;
    assert(normalized.polygons.length === 1, "Polygons length incorrect");
    assert(normalized.polygons[0].exterior[0].x === 0, "Exterior pt incorrect");
    assert(normalized.polygons[0].holes![0][0].x === 5, "Hole pt incorrect");
  });

  test("Test 6: Populates worldOrigin correctly", () => {
    const rawModel: FloorPlanRenderModel = {
      id: "fp_origin",
      boundary: [
        { x: 300, y: 400 },
        { x: 310, y: 400 },
        { x: 310, y: 410 },
        { x: 300, y: 410 },
      ],
      walls: [],
      doors: [],
      windows: [],
      columns: [],
      spaces: [],
      furniture: [],
    };
    const normalized = normalizeFloorPlanRenderModel(rawModel);
    assert(normalized.worldOrigin?.x === 300 && normalized.worldOrigin?.y === 400, "worldOrigin failed");
  });

  test("Test 7: Does not introduce per-object arbitrary offsets", () => {
    const origin = { x: 10, y: 20 };
    const pt1 = { x: 15, y: 25 };
    const pt2 = { x: 30, y: 40 };
    const n1 = normalizePoint(pt1, origin);
    const n2 = normalizePoint(pt2, origin);
    assert(n2.x - n1.x === pt2.x - pt1.x, "Vector dx changed");
    assert(n2.y - n1.y === pt2.y - pt1.y, "Vector dy changed");
  });

  test("Test 8: fitBounds produces sensible scale for normalized boundary", () => {
    const normalizedBoundary = [
      { x: 0, y: 0 },
      { x: 12, y: 0 },
      { x: 12, y: 8 },
      { x: 0, y: 8 },
    ];
    const vp = fitBounds(normalizedBoundary, 800, 600);
    assert(vp.scale > 10 && vp.scale < 100, "fitBounds scale out of bounds");
  });

  return { passed, total };
}
