import React, { useState, useMemo } from "react";
import { GeometryVerificationReport, ElementGeometry } from "../types/verification";

interface Props {
  report: GeometryVerificationReport;
}

export const GeometryPreviewCanvas: React.FC<Props> = ({ report }) => {
  const [zoom, setZoom] = useState<number>(1.0);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Calculate world bounding box across all element geometries and boundary polygon
  const bounds = useMemo(() => {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

    const addPoint = (x: number, y: number) => {
      if (!isNaN(x) && !isNaN(y)) {
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      }
    };

    // Process boundary polygon
    if (report.boundary_polygon && report.boundary_polygon.length > 0) {
      report.boundary_polygon.forEach((pt) => addPoint(pt[0], pt[1]));
    }

    // Process all elements
    report.all_elements_geometry.forEach((elem) => {
      const coords = elem.coordinates;
      if (Array.isArray(coords)) {
        const flatten = (arr: any) => {
          if (Array.isArray(arr) && arr.length >= 2 && typeof arr[0] === "number" && typeof arr[1] === "number") {
            addPoint(arr[0], arr[1]);
          } else if (Array.isArray(arr)) {
            arr.forEach(flatten);
          }
        };
        flatten(coords);
      }
    });

    if (minX === Infinity) {
      minX = 0; minY = 0; maxX = 25; maxY = 15;
    }

    const width = Math.max(maxX - minX, 1.0);
    const height = Math.max(maxY - minY, 1.0);

    return { minX, minY, maxX, maxY, width, height };
  }, [report]);

  const viewWidth = 900;
  const viewHeight = 650;
  const padding = 40;

  // Deterministic World-to-Screen Coordinate Transform
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

  const renderGeometry = (elem: ElementGeometry, key: string) => {
    const cat = (elem.category || "").toUpperCase();

    let stroke = "#38bdf8";
    let fill = "rgba(56, 189, 248, 0.1)";
    let strokeWidth = 1.5;

    if (cat === "WALL") {
      stroke = "#38bdf8";
      fill = "rgba(30, 41, 59, 0.6)";
      strokeWidth = 2.5;
    } else if (cat === "DOOR") {
      stroke = "#10b981";
      fill = "rgba(16, 185, 129, 0.2)";
      strokeWidth = 2;
    } else if (cat === "WINDOW") {
      stroke = "#06b6d4";
      fill = "rgba(6, 182, 212, 0.25)";
      strokeWidth = 2;
    } else if (cat === "COLUMN") {
      stroke = "#c084fc";
      fill = "rgba(192, 132, 252, 0.3)";
      strokeWidth = 2;
    } else if (cat === "SPACE") {
      stroke = "#818cf8";
      fill = "rgba(129, 140, 248, 0.15)";
      strokeWidth = 1.5;
    } else if (cat === "FURNITURE") {
      stroke = "#fbbf24";
      fill = "rgba(251, 191, 36, 0.25)";
      strokeWidth = 1.5;
    }

    const coords = elem.coordinates;

    if (elem.type === "LINE" && Array.isArray(coords) && coords.length >= 2) {
      const d = pointsToSVGPath(coords as number[][]);
      return <path key={key} d={d} stroke={stroke} strokeWidth={strokeWidth} fill="none" />;
    }

    if (elem.type === "Polygon" || elem.type === "LWPOLYLINE" || elem.type === "POLYLINE" || elem.type === "CIRCLE") {
      if (Array.isArray(coords) && coords.length > 0 && Array.isArray(coords[0]) && typeof coords[0][0] === "number") {
        const d = pointsToSVGPath(coords as number[][]) + (elem.is_closed ? " Z" : "");
        return <path key={key} d={d} stroke={stroke} strokeWidth={strokeWidth} fill={fill} />;
      } else if (Array.isArray(coords) && coords.length > 0 && Array.isArray(coords[0]) && Array.isArray(coords[0][0])) {
        // Outer ring + holes
        const outer = coords[0] as number[][];
        let d = pointsToSVGPath(outer) + " Z";
        for (let i = 1; i < coords.length; i++) {
          d += " " + pointsToSVGPath(coords[i] as number[][]) + " Z";
        }
        return <path key={key} d={d} stroke={stroke} strokeWidth={strokeWidth} fill={fill} fillRule="evenodd" />;
      }
    }

    if (elem.type === "MultiPolygon" && Array.isArray(coords)) {
      const paths: string[] = [];
      (coords as number[][][][]).forEach((polyRings) => {
        if (polyRings.length > 0) {
          let d = pointsToSVGPath(polyRings[0]) + " Z";
          for (let i = 1; i < polyRings.length; i++) {
            d += " " + pointsToSVGPath(polyRings[i]) + " Z";
          }
          paths.push(d);
        }
      });
      return <path key={key} d={paths.join(" ")} stroke={stroke} strokeWidth={strokeWidth} fill={fill} fillRule="evenodd" />;
    }

    return null;
  };

  return (
    <div className="canvas-container">
      <div className="controls-overlay">
        <button className="btn-ctrl" onClick={() => setZoom((z) => Math.min(z * 1.2, 5.0))}>Zoom +</button>
        <button className="btn-ctrl" onClick={() => setZoom((z) => Math.max(z / 1.2, 0.5))}>Zoom -</button>
        <button className="btn-ctrl" onClick={() => { setZoom(1.0); setPan({ x: 0, y: 0 }); }}>Fit to View</button>
      </div>

      <svg width={viewWidth} height={viewHeight} style={{ cursor: "grab" }}>
        {/* Render Grid Lines */}
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255, 255, 255, 0.05)" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />

        {/* Render Outer Boundary */}
        {report.boundary_polygon && report.boundary_polygon.length > 0 && (
          <path
            d={pointsToSVGPath(report.boundary_polygon) + " Z"}
            stroke="#f43f5e"
            strokeWidth={2.5}
            strokeDasharray="6 3"
            fill="rgba(244, 63, 94, 0.03)"
          />
        )}

        {/* Render Extracted Element Geometries */}
        {report.all_elements_geometry.map((elem, idx) => renderGeometry(elem, `geom_${idx}`))}
      </svg>
    </div>
  );
};
