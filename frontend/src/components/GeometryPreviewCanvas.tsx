import React, { useState, useMemo } from "react";
import { GeometryVerificationReport, ElementGeometry } from "../types/verification";

interface Props {
  report: GeometryVerificationReport;
}

export const GeometryPreviewCanvas: React.FC<Props> = ({ report }) => {
  const [zoom, setZoom] = useState<number>(1.0);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Calculate global world bounding box across all geometries (including boundary_geometry & boundary_polygon)
  const bounds = useMemo(() => {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

    const addPoint = (x: number, y: number) => {
      if (typeof x === "number" && typeof y === "number" && !isNaN(x) && !isNaN(y) && isFinite(x) && isFinite(y)) {
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      }
    };

    const addCoordsRecursive = (arr: any) => {
      if (!Array.isArray(arr)) return;
      if (arr.length >= 2 && typeof arr[0] === "number" && typeof arr[1] === "number") {
        addPoint(arr[0], arr[1]);
      } else {
        arr.forEach(addCoordsRecursive);
      }
    };

    // 1. Process legacy boundary_polygon
    if (report.boundary_polygon && report.boundary_polygon.length > 0) {
      report.boundary_polygon.forEach((pt) => addPoint(pt[0], pt[1]));
    }

    // 2. Process authoritative boundary_geometry
    if (report.boundary_geometry && report.boundary_geometry.coordinates) {
      addCoordsRecursive(report.boundary_geometry.coordinates);
    }

    // 3. Process all extracted elements
    if (report.all_elements_geometry) {
      report.all_elements_geometry.forEach((elem) => {
        if (elem.coordinates) {
          addCoordsRecursive(elem.coordinates);
        }
      });
    }

    if (minX === Infinity || minY === Infinity || maxX === -Infinity || maxY === -Infinity) {
      minX = 0; minY = 0; maxX = 30; maxY = 20;
    }

    const width = Math.max(maxX - minX, 1.0);
    const height = Math.max(maxY - minY, 1.0);

    return { minX, minY, maxX, maxY, width, height };
  }, [report]);

  const viewWidth = 900;
  const viewHeight = 650;
  const padding = 50;

  // Deterministic World-to-Screen Coordinate Transform with Y-axis flip
  const scale = Math.min(
    (viewWidth - 2 * padding) / bounds.width,
    (viewHeight - 2 * padding) / bounds.height
  ) * zoom;

  const transformPoint = (x: number, y: number): [number, number] => {
    const sx = padding + (x - bounds.minX) * scale + pan.x;
    const sy = viewHeight - (padding + (y - bounds.minY) * scale) + pan.y;
    return [sx, sy];
  };

  const pointsToSVGPath = (pts: number[][]): string => {
    if (!pts || pts.length === 0) return "";
    const [startSx, startSy] = transformPoint(pts[0][0], pts[0][1]);
    let d = `M ${startSx.toFixed(2)} ${startSy.toFixed(2)}`;
    for (let i = 1; i < pts.length; i++) {
      const [sx, sy] = transformPoint(pts[i][0], pts[i][1]);
      d += ` L ${sx.toFixed(2)} ${sy.toFixed(2)}`;
    }
    return d;
  };

  const renderGeometryContainer = (
    type: string,
    coords: any,
    stroke: string,
    fill: string,
    strokeWidth: number,
    key: string,
    dashed: boolean = false
  ) => {
    if (!coords) return null;

    if (type === "Polygon") {
      if (Array.isArray(coords) && coords.length > 0 && Array.isArray(coords[0]) && typeof coords[0][0] === "number") {
        const d = pointsToSVGPath(coords as number[][]) + " Z";
        return (
          <path
            key={key}
            d={d}
            stroke={stroke}
            strokeWidth={strokeWidth}
            fill={fill}
            strokeDasharray={dashed ? "5 3" : undefined}
          />
        );
      } else if (Array.isArray(coords) && coords.length > 0 && Array.isArray(coords[0]) && Array.isArray(coords[0][0])) {
        // Outer ring + interior holes
        const outer = coords[0] as number[][];
        let d = pointsToSVGPath(outer) + " Z";
        for (let i = 1; i < coords.length; i++) {
          d += " " + pointsToSVGPath(coords[i] as number[][]) + " Z";
        }
        return (
          <path
            key={key}
            d={d}
            stroke={stroke}
            strokeWidth={strokeWidth}
            fill={fill}
            fillRule="evenodd"
            strokeDasharray={dashed ? "5 3" : undefined}
          />
        );
      }
    }

    if (type === "MultiPolygon" && Array.isArray(coords)) {
      const paths: string[] = [];
      (coords as number[][][][]).forEach((polyRings) => {
        if (Array.isArray(polyRings) && polyRings.length > 0) {
          let d = pointsToSVGPath(polyRings[0]) + " Z";
          for (let i = 1; i < polyRings.length; i++) {
            d += " " + pointsToSVGPath(polyRings[i]) + " Z";
          }
          paths.push(d);
        }
      });
      return (
        <path
          key={key}
          d={paths.join(" ")}
          stroke={stroke}
          strokeWidth={strokeWidth}
          fill={fill}
          fillRule="evenodd"
          strokeDasharray={dashed ? "5 3" : undefined}
        />
      );
    }

    if ((type === "LINE" || type === "LWPOLYLINE" || type === "POLYLINE") && Array.isArray(coords)) {
      if (coords.length > 0 && typeof coords[0][0] === "number") {
        const d = pointsToSVGPath(coords as number[][]);
        return (
          <path
            key={key}
            d={d}
            stroke={stroke}
            strokeWidth={strokeWidth}
            fill="none"
            strokeDasharray={dashed ? "5 3" : undefined}
          />
        );
      }
    }

    return null;
  };

  const renderElement = (elem: ElementGeometry, key: string) => {
    const cat = (elem.category || "").toUpperCase();

    let stroke = "#38bdf8";
    let fill = "rgba(56, 189, 248, 0.12)";
    let strokeWidth = 1.5;

    if (cat === "WALL") {
      stroke = "#334155";
      fill = "rgba(51, 65, 85, 0.45)";
      strokeWidth = 2.5;
    } else if (cat === "DOOR") {
      stroke = "#06b6d4";
      fill = "rgba(6, 182, 212, 0.25)";
      strokeWidth = 2;
    } else if (cat === "WINDOW") {
      stroke = "#3b82f6";
      fill = "rgba(59, 130, 246, 0.2)";
      strokeWidth = 2;
    } else if (cat === "COLUMN") {
      stroke = "#f59e0b";
      fill = "rgba(245, 158, 11, 0.4)";
      strokeWidth = 2;
    } else if (cat === "SPACE") {
      stroke = "#6366f1";
      fill = "rgba(99, 102, 241, 0.12)";
      strokeWidth = 1.5;
    } else if (cat === "FURNITURE") {
      stroke = "#ec4899";
      fill = "rgba(236, 72, 153, 0.25)";
      strokeWidth = 1.5;
    }

    return renderGeometryContainer(elem.type, elem.coordinates, stroke, fill, strokeWidth, key, cat === "SPACE");
  };

  return (
    <div className="canvas-container">
      <div className="controls-overlay">
        <button className="btn-ctrl" onClick={() => setZoom((z) => Math.min(z * 1.2, 5.0))}>Zoom +</button>
        <button className="btn-ctrl" onClick={() => setZoom((z) => Math.max(z / 1.2, 0.5))}>Zoom -</button>
        <button className="btn-ctrl" onClick={() => { setZoom(1.0); setPan({ x: 0, y: 0 }); }}>Fit to View</button>
      </div>

      <svg width={viewWidth} height={viewHeight} style={{ cursor: "grab" }}>
        {/* Render Grid */}
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255, 255, 255, 0.05)" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />

        {/* Render Authoritative Boundary Geometry */}
        {report.boundary_geometry &&
          renderGeometryContainer(
            report.boundary_geometry.type,
            report.boundary_geometry.coordinates,
            "#10b981",
            "rgba(16, 185, 129, 0.04)",
            2.5,
            "authoritative_boundary",
            true
          )}

        {/* Fallback boundary_polygon rendering if boundary_geometry is absent */}
        {!report.boundary_geometry && report.boundary_polygon && report.boundary_polygon.length > 0 && (
          <path
            d={pointsToSVGPath(report.boundary_polygon) + " Z"}
            stroke="#10b981"
            strokeWidth={2.5}
            strokeDasharray="6 3"
            fill="rgba(16, 185, 129, 0.04)"
          />
        )}

        {/* Render Extracted Elements */}
        {report.all_elements_geometry.map((elem, idx) => renderElement(elem, `elem_${idx}`))}
      </svg>
    </div>
  );
};
