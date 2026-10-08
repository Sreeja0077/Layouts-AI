/**
 * Room opening & door orientation utilities for Layouts AI 2D CAD Editor.
 * Computes host wall alignment, room interior polygon containment, inward/outward swing directions,
 * and hinge placement.
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
  hingeSide: "START" | "END";
  swingDirection: "INWARD" | "OUTWARD";
  interiorNormal: RenderPoint; // Unit normal vector pointing into room interior
  targetSpace?: RenderSpace;
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
  walls: ReadonlyArray<RenderWall> = []
): DoorOpeningOrientation {
  let wallAngleDeg = baseAngleDeg;
  let minWallDist = Infinity;

  // 1. Host wall alignment: match nearest host wall angle if door is within 1.5m of wall segment
  for (const wall of walls) {
    if (wall.start && wall.end) {
      const proj = projectPointToLine(doorPos, wall.start, wall.end);
      const dist = distance(doorPos, proj);
      if (dist < minWallDist && dist < 1.5) {
        minWallDist = dist;
        const dx = wall.end.x - wall.start.x;
        const dy = wall.end.y - wall.start.y;
        wallAngleDeg = (Math.atan2(dy, dx) * 180) / Math.PI;
      }
    }
  }

  const rad = (wallAngleDeg * Math.PI) / 180;
  const u = { x: Math.cos(rad), y: Math.sin(rad) };
  // Perpendicular normal vectors to wall line: n1 (left) and n2 (right)
  const n1 = { x: -u.y, y: u.x };
  const n2 = { x: u.y, y: -u.x };

  // Test points placed into room interior along normals n1 and n2
  const testDist = Math.max(0.3, doorWidth * 0.5);
  const p1 = { x: doorPos.x + n1.x * testDist, y: doorPos.y + n1.y * testDist };
  const p2 = { x: doorPos.x + n2.x * testDist, y: doorPos.y + n2.y * testDist };

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
    // Exterior door or outside building boundary
    interiorNormal = n1;
  }

  // Small room policy check (< 3m2 threshold)
  if (targetSpace && targetSpace.geometry) {
    const spaceArea = calculatePolygonArea(
      targetSpace.geometry.polygons[0]?.exterior || []
    );
    if (spaceArea > 0 && spaceArea < SMALL_ROOM_THRESHOLD_SQM) {
      swingDirection = "OUTWARD";
    }
  }

  return {
    hostWallAngleDeg: wallAngleDeg,
    hingeSide: "START",
    swingDirection,
    interiorNormal,
    targetSpace,
  };
}
