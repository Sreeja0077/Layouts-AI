import sys
from pathlib import Path

try:
    import ezdxf
except ImportError:
    print("ezdxf not installed yet in current python interpreter")
    sys.exit(1)

fixture_dir = Path("docs/fixtures")
fixture_dir.mkdir(parents=True, exist_ok=True)
dxf_path = fixture_dir / "sample_floor_plan.dxf"

doc = ezdxf.new("R2010")
msp = doc.modelspace()

# Define architectural layers
doc.layers.add("A-WALL", color=1)
doc.layers.add("A-DOOR", color=2)
doc.layers.add("A-WINDOW", color=3)
doc.layers.add("A-COLUMN", color=4)
doc.layers.add("A-ROOM", color=5)
doc.layers.add("A-FURN", color=6)

# Outer Wall Polyline (Closed rectangle 0,0 to 20,12)
msp.add_lwpolyline([(0.0, 0.0), (20.0, 0.0), (20.0, 12.0), (0.0, 12.0)], close=True, dxfattribs={"layer": "A-WALL"})

# Interior Wall Line
msp.add_line((10.0, 0.0), (10.0, 8.0), dxfattribs={"layer": "A-WALL"})

# Door Line
msp.add_line((10.0, 8.0), (10.0, 10.0), dxfattribs={"layer": "A-DOOR"})

# Door Swing Arc
msp.add_arc(center=(10.0, 8.0), radius=2.0, start_angle=0, end_angle=90, dxfattribs={"layer": "A-DOOR"})

# Window Line
msp.add_line((4.0, 12.0), (8.0, 12.0), dxfattribs={"layer": "A-WINDOW"})

# Square Column Polyline
msp.add_lwpolyline([(4.0, 4.0), (6.0, 4.0), (6.0, 6.0), (4.0, 6.0)], close=True, dxfattribs={"layer": "A-COLUMN"})

# Circular Column
msp.add_circle(center=(15.0, 5.0), radius=1.0, dxfattribs={"layer": "A-COLUMN"})

# Space / Room Boundary Polyline
msp.add_lwpolyline([(0.0, 0.0), (10.0, 0.0), (10.0, 12.0), (0.0, 12.0)], close=True, dxfattribs={"layer": "A-ROOM"})

# Furniture Polyline (Desk)
msp.add_lwpolyline([(2.0, 2.0), (4.0, 2.0), (4.0, 3.0), (2.0, 3.0)], close=True, dxfattribs={"layer": "A-FURN"})

doc.saveas(str(dxf_path))
print(f"Successfully generated DXF fixture at: {dxf_path.resolve()}")
