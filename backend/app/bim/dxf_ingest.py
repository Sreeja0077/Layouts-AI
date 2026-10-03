"""
2D AutoCAD DXF Floor Plan Ingestion Engine.
Parses 2D CAD drawing entities (LWPOLYLINE, POLYLINE, LINE, ARC, CIRCLE) using ezdxf
and deterministically classifies layers into spatial categories.
Strict zero-fabricated-geometry policy: missing, unreadable, or malformed files raise
explicit exceptions instead of producing mock or fallback geometry.
"""

import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

try:
    import ezdxf
    HAS_EZDXF = True
except ImportError:
    ezdxf = None
    HAS_EZDXF = False


class DXFEntity(BaseModel):
    """Extracted 2D vector CAD entity."""
    model_config = ConfigDict(extra="forbid")

    entity_type: str = Field(..., description="CAD entity type (e.g. 'LWPOLYLINE', 'POLYLINE', 'LINE', 'ARC', 'CIRCLE')")
    layer_name: str = Field(..., description="CAD layer name (e.g. 'A-WALL', 'A-DOOR')")
    category: str = Field(..., description="Classified category ('WALL', 'DOOR', 'WINDOW', 'COLUMN', 'FURNITURE', 'SPACE', 'GENERIC')")
    coordinates: List[List[float]] = Field(..., description="2D vertices [[x0, y0], [x1, y1], ...]")
    is_closed: bool = Field(default=False, description="True if polyline/geometry forms a closed boundary")


class DXFParsedFloorPlan(BaseModel):
    """Structured result returned by DXF 2D CAD ingestor."""
    model_config = ConfigDict(extra="forbid")

    file_name: str
    total_entities_count: int = Field(..., description="Total count of extracted 2D vector CAD entities")
    entities_by_category: Dict[str, int] = Field(default_factory=dict, description="Counts of extracted entities by category")
    layers_found: List[str] = Field(default_factory=list, description="Unique DXF layer names found in source file")
    extracted_entities: List[DXFEntity] = Field(default_factory=list, description="Extracted vector CAD entities")


class DXFIngestor:
    """Ingestor parsing 2D DXF CAD drawing files into spatial vector structures using ezdxf."""

    def parse_file(self, file_path_or_name: str) -> DXFParsedFloorPlan:
        """
        Parse a 2D DXF file and extract classified CAD entities using native ezdxf engine.
        Enforces strict zero-fabricated-geometry policy: missing, unreadable, or malformed
        files raise explicit errors instead of returning mock fallback data.
        """
        path = Path(file_path_or_name)

        if not path.exists():
            raise FileNotFoundError(f"DXF file not found at path: '{file_path_or_name}'")

        if not HAS_EZDXF or ezdxf is None:
            raise ImportError(
                "ezdxf library is not installed in the environment. "
                "Please install ezdxf to parse DXF CAD files."
            )

        try:
            doc = ezdxf.readfile(str(path))
        except Exception as exc:
            raise ValueError(f"Failed to open or parse DXF file '{path.name}': {str(exc)}") from exc

        return self._parse_with_ezdxf(doc, path.name)

    def _classify_layer(self, layer_name: str) -> str:
        """Classify CAD layer name into domain spatial categories deterministically."""
        upper = layer_name.upper().strip()
        tokens = [t for t in re.split(r"[^A-Z0-9]", upper) if t]

        if any(w in upper for w in ["WALL", "A-WALL", "EXTERIOR", "PARTITION"]) or ("INTERIOR" in tokens and "WALL" in tokens):
            return "WALL"
        elif any(w in upper for w in ["DOOR", "A-DOOR", "OPENING"]):
            return "DOOR"
        elif any(w in upper for w in ["WINDOW", "GLAZ", "A-GLAZ"]):
            return "WINDOW"
        elif any(w in upper for w in ["COLUMN", "A-COL", "PILLAR"]) or "COL" in tokens or "STRUCT" in tokens:
            return "COLUMN"
        elif any(w in upper for w in ["FURN", "FURNITURE", "EQUIP", "DESK"]):
            return "FURNITURE"
        elif any(w in upper for w in ["ROOM", "AREA", "SPACE", "ZONE"]):
            return "SPACE"
        return "GENERIC"

    def _parse_with_ezdxf(self, doc: Any, file_name: str) -> DXFParsedFloorPlan:
        """Extract entities using native ezdxf library."""
        msp = doc.modelspace()
        extracted: List[DXFEntity] = []
        categories: Dict[str, int] = {}
        layers_set = set()

        for entity in msp:
            layer = getattr(entity.dxf, "layer", "0")
            layers_set.add(layer)
            dxftype = entity.dxftype()

            coords: List[List[float]] = []
            is_closed = False

            if dxftype == "LWPOLYLINE":
                try:
                    points = list(entity.get_points())
                    coords = [[round(float(p[0]), 4), round(float(p[1]), 4)] for p in points]
                    is_closed = bool(getattr(entity, "closed", False))
                except Exception:
                    coords = []

            elif dxftype == "POLYLINE":
                try:
                    if hasattr(entity, "points"):
                        points = [p.dxf.location for p in entity.points()]
                        coords = [[round(float(p.x), 4), round(float(p.y), 4)] for p in points]
                    elif hasattr(entity, "vertices"):
                        coords = [[round(float(v.dxf.location.x), 4), round(float(v.dxf.location.y), 4)] for v in entity.vertices]
                    is_closed = bool(getattr(entity, "is_closed", False))
                except Exception:
                    coords = []

            elif dxftype == "LINE":
                try:
                    start = entity.dxf.start
                    end = entity.dxf.end
                    coords = [
                        [round(float(start.x), 4), round(float(start.y), 4)],
                        [round(float(end.x), 4), round(float(end.y), 4)],
                    ]
                    is_closed = False
                except Exception:
                    coords = []

            elif dxftype == "ARC":
                try:
                    center = entity.dxf.center
                    radius = float(entity.dxf.radius)
                    start_angle = float(entity.dxf.start_angle)
                    end_angle = float(entity.dxf.end_angle)

                    if end_angle < start_angle:
                        end_angle += 360.0

                    angle_span = end_angle - start_angle
                    segments = max(4, int(angle_span / 15.0))
                    coords = []
                    for i in range(segments + 1):
                        angle_deg = start_angle + (angle_span * i / segments)
                        rad = math.radians(angle_deg)
                        x = round(float(center.x + radius * math.cos(rad)), 4)
                        y = round(float(center.y + radius * math.sin(rad)), 4)
                        coords.append([x, y])
                    is_closed = False
                except Exception:
                    coords = []

            elif dxftype == "CIRCLE":
                try:
                    center = entity.dxf.center
                    radius = float(entity.dxf.radius)
                    segments = 16
                    coords = []
                    for i in range(segments):
                        angle_deg = 360.0 * i / segments
                        rad = math.radians(angle_deg)
                        x = round(float(center.x + radius * math.cos(rad)), 4)
                        y = round(float(center.y + radius * math.sin(rad)), 4)
                        coords.append([x, y])
                    if coords:
                        coords.append(coords[0])  # Close circle boundary ring
                    is_closed = True
                except Exception:
                    coords = []

            if coords and len(coords) >= 2:
                cat = self._classify_layer(layer)
                categories[cat] = categories.get(cat, 0) + 1
                extracted.append(
                    DXFEntity(
                        entity_type=dxftype,
                        layer_name=layer,
                        category=cat,
                        coordinates=coords,
                        is_closed=is_closed,
                    )
                )

        return DXFParsedFloorPlan(
            file_name=file_name,
            total_entities_count=len(extracted),
            entities_by_category=categories,
            layers_found=sorted(list(layers_set)),
            extracted_entities=extracted,
        )
