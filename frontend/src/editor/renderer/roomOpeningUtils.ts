/**
 * Room opening & door orientation utilities for Layouts AI 2D CAD Editor.
 * Computes host wall alignment, room interior polygon containment, inward/outward swing directions,
 * and hinge placement in pure world coordinates.
 */

import {
  calculatePolygonArea,
  distance,
  pointInPolygon,
  projectPointToLine,
} from "./geometryUtils";
import { RenderPoint, RenderSpace, RenderWall } from "./renderTypes";

export const SMALL_ROOM_THRESHOLD_SQM = 3.0;

export interface DoorOpeningOrientation {
  hostWallAngleDeg: number;
  u: RenderPoint; // Unit vector along host wall tangent in world space
  interiorNormal: RenderPoint; // Unit normal vector pointing into room interior in world space
  hingeSide: "START" | "END";
  swingDirection: "INWARD" | "OUTWARD";
  targetSpace?: RenderSpace;
  matchedWallId?: string;
}

export function findContainingRoom(
  pos: RenderPoint,
  spaces: ReadonlyArray<RenderSpace>
): RenderSpace | undefined {
  for (const space of spaces) {
    if (!space.geometry) continue;
    for (const poly of space.geometry.polygons || []) {
      if (pointInPolygon(pos, poly.exterior)) {
        return space;
      }
    }
  }
  return undefined;
}

export function calculateDoorOpeningOrientation(
  doorPos: RenderPoint,
  doorWidth: number,
  baseAngleDeg: number,
  spaces: ReadonlyArray<RenderSpace>,
  walls: ReadonlyArray<RenderWall> = [],
  explicitHostWallId?: string,
  otherDoors: ReadonlyArray<{ pos?: RenderPoint; width?: number; id?: string }> = [],
  doorProperties?: Record<string, any>
): DoorOpeningOrientation {
  let wallAngleDeg = baseAngleDeg;
  let matchedWallId: string | undefined = undefined;

  // 1. Explicit Host Wall ID match (authoritative from IFC "Host Id")
  let hostWall: RenderWall | undefined = undefined;
  if (explicitHostWallId) {
    hostWall = walls.find(
      (w) => w.id === explicitHostWallId || w.id.includes(explicitHostWallId)
    );
  }

  // 2. Fallback: Geometric proximity / projection to find host wall
  if (!hostWall) {
    let minWallDist = Infinity;
    for (const wall of walls) {
      if (wall.start && wall.end) {
        const proj = projectPointToLine(doorPos, wall.start, wall.end);
        const dist = distance(doorPos, proj);
        if (dist < minWallDist && dist < 1.5) {
          minWallDist = dist;
          hostWall = wall;
        }
      }
    }
  }

  if (hostWall && hostWall.start && hostWall.end) {
    matchedWallId = hostWall.id;
    const dx = hostWall.end.x - hostWall.start.x;
    const dy = hostWall.end.y - hostWall.start.y;
    if (Math.hypot(dx, dy) > 1e-4) {
      wallAngleDeg = (Math.atan2(dy, dx) * 180) / Math.PI;
    }
  }

  const rad = (wallAngleDeg * Math.PI) / 180;
  const u: RenderPoint = { x: Math.cos(rad), y: Math.sin(rad) };
  // Perpendicular normal vectors to wall line: n1 (left) and n2 (right)
  const n1: RenderPoint = { x: -u.y, y: u.x };
  const n2: RenderPoint = { x: u.y, y: -u.x };

  // Test points placed into room interior along normals n1 and n2
  const testDist = Math.max(0.25, doorWidth * 0.4);
  const p1: RenderPoint = { x: doorPos.x + n1.x * testDist, y: doorPos.y + n1.y * testDist };
  const p2: RenderPoint = { x: doorPos.x + n2.x * testDist, y: doorPos.y + n2.y * testDist };

  const room1 = findContainingRoom(p1, spaces);
  const room2 = findContainingRoom(p2, spaces);

  let interiorNormal = n1;
  let targetSpace: RenderSpace | undefined = room1 || room2;
  let swingDirection: "INWARD" | "OUTWARD" = "INWARD";

  if (room1 && !room2) {
    interiorNormal = n1;
    targetSpace = room1;
  } else if (!room1 && room2) {
    interiorNormal = n2;
    targetSpace = room2;
  } else if (room1 && room2) {
    // Both sides are inside room polygons (e.g. wall between office & corridor)
    const area1 = room1.geometry
      ? calculatePolygonArea(room1.geometry.polygons[0]?.exterior || [])
      : 10;
    const area2 = room2.geometry
      ? calculatePolygonArea(room2.geometry.polygons[0]?.exterior || [])
      : 10;

    // Prefer swinging into larger room space (e.g. Office over Corridor/Toilet)
    if (area1 >= area2) {
      interiorNormal = n1;
      targetSpace = room1;
    } else {
      interiorNormal = n2;
      targetSpace = room2;
    }
  } else {
    // Exterior door or outside building boundary: find closest space centroid
    let bestDist = Infinity;
    for (const space of spaces) {
      if (!space.geometry || !space.geometry.polygons?.[0]?.exterior) continue;
      const poly = space.geometry.polygons[0].exterior;
      const cX = poly.reduce((s, pt) => s + pt.x, 0) / poly.length;
      const cY = poly.reduce((s, pt) => s + pt.y, 0) / poly.length;
      const d1 = Math.hypot(p1.x - cX, p1.y - cY);
      const d2 = Math.hypot(p2.x - cX, p2.y - cY);
      if (d1 < bestDist || d2 < bestDist) {
        if (d1 <= d2) {
          bestDist = d1;
          interiorNormal = n1;
          targetSpace = space;
        } else {
          bestDist = d2;
          interiorNormal = n2;
          targetSpace = space;
        }
      }
    }
  }

  // Check if there is an adjacent paired door along the same wall (Double Door Opening)
  let pairedHingeSide: "START" | "END" | null = null;
  for (const other of otherDoors) {
    if (!other.pos) continue;
    const dist = distance(doorPos, other.pos);
    const otherW = other.width || doorWidth;
    const maxPairedDist = (doorWidth + otherW) * 0.75;
    if (dist > 0.05 && dist <= maxPairedDist) {
      // 1. Same Target Room Check: both doors must open into the exact same room
      const otherTestP1: RenderPoint = {
        x: other.pos.x + n1.x * testDist,
        y: other.pos.y + n1.y * testDist,
      };
      const otherTestP2: RenderPoint = {
        x: other.pos.x + n2.x * testDist,
        y: other.pos.y + n2.y * testDist,
      };
      const otherRoom =
        findContainingRoom(otherTestP1, spaces) ||
        findContainingRoom(otherTestP2, spaces);

      const isSameRoom =
        targetSpace && otherRoom && targetSpace.id === otherRoom.id;

      // 2. Intervening Partition Wall Check: check if any wall meets between the two doors
      let hasInterveningWall = false;
      const minX = Math.min(doorPos.x, other.pos.x);
      const maxX = Math.max(doorPos.x, other.pos.x);
      const minY = Math.min(doorPos.y, other.pos.y);
      const maxY = Math.max(doorPos.y, other.pos.y);

      for (const wall of walls) {
        if (!wall.start || !wall.end) continue;
        if (matchedWallId && wall.id === matchedWallId) continue;

        // Check if either endpoint of a partition wall terminates between the two doors
        for (const pt of [wall.start, wall.end]) {
          const proj = projectPointToLine(pt, doorPos, other.pos);
          const dToDoorLine = distance(pt, proj);
          const isBetween =
            proj.x >= minX - 0.1 &&
            proj.x <= maxX + 0.1 &&
            proj.y >= minY - 0.1 &&
            proj.y <= maxY + 0.1;
          if (dToDoorLine < 0.35 && isBetween) {
            hasInterveningWall = true;
            break;
          }
        }
        if (hasInterveningWall) break;
      }

      // ONLY if both doors open into the SAME room AND there is NO separating wall between them is it a double door!
      if (isSameRoom && !hasInterveningWall) {
        const dx = other.pos.x - doorPos.x;
        const dy = other.pos.y - doorPos.y;
        const proj = dx * u.x + dy * u.y;
        if (proj > 0.1) {
          // Other door is in +u direction (END side), so our END side is the meeting strike point -> hinge at START
          pairedHingeSide = "START";
          break;
        } else if (proj < -0.1) {
          // Other door is in -u direction (START side), so our START side is the meeting strike point -> hinge at END
          pairedHingeSide = "END";
          break;
        }
      }
    }
  }

  // Determine Hinge Side based on corner proximity (adjacent perpendicular walls / room vertices)
  const jStart: RenderPoint = {
    x: doorPos.x - (u.x * doorWidth) / 2,
    y: doorPos.y - (u.y * doorWidth) / 2,
  };
  const jEnd: RenderPoint = {
    x: doorPos.x + (u.x * doorWidth) / 2,
    y: doorPos.y + (u.y * doorWidth) / 2,
  };

  let minCornerDistStart = Infinity;
  let minCornerDistEnd = Infinity;

  // Check proximity to other walls (excluding the host wall itself)
  for (const wall of walls) {
    if (!wall.start || !wall.end) continue;
    if (matchedWallId && wall.id === matchedWallId) {
      // Also check distance to host wall endpoints (corners)
      const dStartCorner = Math.min(
        distance(jStart, wall.start),
        distance(jStart, wall.end)
      );
      const dEndCorner = Math.min(
        distance(jEnd, wall.start),
        distance(jEnd, wall.end)
      );
      minCornerDistStart = Math.min(minCornerDistStart, dStartCorner);
      minCornerDistEnd = Math.min(minCornerDistEnd, dEndCorner);
      continue;
    }

    const projStart = projectPointToLine(jStart, wall.start, wall.end);
    const dStart = distance(jStart, projStart);
    const projEnd = projectPointToLine(jEnd, wall.start, wall.end);
    const dEnd = distance(jEnd, projEnd);

    minCornerDistStart = Math.min(minCornerDistStart, dStart);
    minCornerDistEnd = Math.min(minCornerDistEnd, dEnd);
  }

  // Check proximity to room polygon vertices
  const spacesToCheck = targetSpace ? [targetSpace] : spaces;
  for (const sp of spacesToCheck) {
    for (const poly of sp.geometry?.polygons || []) {
      for (const pt of poly.exterior || []) {
        const dStart = distance(jStart, pt);
        const dEnd = distance(jEnd, pt);
        minCornerDistStart = Math.min(minCornerDistStart, dStart);
        minCornerDistEnd = Math.min(minCornerDistEnd, dEnd);
      }
    }
  }

  // 3. Explicit IFC OperationType override if present in BIM model
  const opType = String(
    doorProperties?.OperationType ||
    doorProperties?.["Pset_DoorCommon.OperationType"] ||
    doorProperties?.operation_type ||
    ""
  ).toUpperCase();

  let ifcHingeSide: "START" | "END" | null = null;
  if (opType.includes("SINGLE_SWING_LEFT")) {
    ifcHingeSide = "START";
  } else if (opType.includes("SINGLE_SWING_RIGHT")) {
    ifcHingeSide = "END";
  }

  const hingeSide: "START" | "END" =
    ifcHingeSide ??
    pairedHingeSide ??
    (minCornerDistEnd < minCornerDistStart ? "END" : "START");


  return {
    hostWallAngleDeg: wallAngleDeg,
    u,
    interiorNormal,
    hingeSide,
    swingDirection,
    targetSpace,
    matchedWallId,
  };
}


