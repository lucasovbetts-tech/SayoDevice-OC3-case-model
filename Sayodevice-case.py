"""
Matte black aluminium case concept for the SayoDevice O3C.

Builds a parametric 2-part case (top shell + bottom plate) with CadQuery,
exports STEP (for CNC quotes) + STL, and renders a studio image with VTK.

All dimensions are ESTIMATES - measure your O3C's PCB with callipers and
edit the PARAMETERS block before ordering anything.

Design: plain key opening with large radii (cheap to machine), stepped bezel
pocket around the screen, M3 corner posts in the top shell, PCB standoffs on
the bottom plate (DXF version is flat, for laser cutting + brass standoffs).

Screws: 4x M3x10 countersunk (case), 4x M2x6 (PCB onto standoffs).

Outputs (~/Downloads/o3c_case):
  o3c_case_top/bottom.step       -> send to CNC shop for the aluminium case
  o3c_case_bottom_lasercut.dxf   -> 2D outline for laser cutting the bottom plate
  top.stl / bottom.stl           -> 3D print these for a test fit 
  keycaps/knob/knob_line/plug/cable/desk.stl -> render props only, ignore
  *.png                          -> preview renders (+ screen texture)

Usage:  py Sayodevice-case.py            -> writes files into ~/Downloads/o3c_case
Needs:  pip install cadquery pillow    (vtk comes with cadquery)
"""
import math
import os
import cadquery as cq
import vtk
from PIL import Image, ImageDraw, ImageFont

#===============================================================================
# Parameters (mm)
#===============================================================================

CASE_W, CASE_D = 68.0, 62.0       # outer footprint (width x depth)
TOP_H, BOTTOM_H = 18.0, 4.0       # top shell height, bottom plate thickness
WALL = 3.0                         # wall thickness
CORNER_R = 7.0                     # vertical corner radius
TOP_CHAMFER = 1.2                  # bright diamond-cut style edge around the top

KEY_PITCH = 19.05                  # standard key spacing
KEY_COUNT = 3
KEY_ROW_Y = -10.0                  # key row centre (front is -Y)
KEY_OPENING_PAD = 1.2              # gap between keycaps and case
KEY_OPENING_R = 3.0                # key opening corner radius (bigger = cheaper)

SCREEN_W, SCREEN_H = 24.0, 13.0    # 0.96" IPS window
SCREEN_BEZEL = 1.5                 # flat ledge between screen and pocket edge
SCREEN_POCKET_DEPTH = 1.2          # how far the screen bezel pocket sinks in
SCREEN_POCKET_R = 2.0
SCREEN_OPENING_R = 1.0
SCREEN_POS = (-12.5, 15.0)
KNOB_HOLE_D = 8.0
KNOB_D, KNOB_H = 17.0, 12.0
KNOB_POS = (18.0, 15.0)
KNURL_TEETH = 70

USB_W, USB_H = 11.0, 5.0           # USB-C slot on the back wall
USB_X = -14.0
SCREW_INSET = 6.0                  # M3 screws through the bottom plate
SCREW_POST_D = 7.0                 # posts inside the top shell the M3 screws thread into
SCREW_PILOT_D = 2.5                # 2.5 = tap for M3 (aluminium), 4.0 = M3 heat-set insert (3D print)
SCREW_DEPTH = 8.0                  # pilot hole depth into the post (M3x10 countersunk screws)

# PCB standoffs on the bottom plate - PLACEHOLDER positions, measure the O3C's mounting holes
PCB_HOLES = [(-22.0, 0.0), (22.0, 0.0), (-22.0, 20.0), (22.0, 20.0)]
PCB_STANDOFF_H = 3.0               # gap between bottom plate and PCB underside
PCB_STANDOFF_D = 6.0
PCB_PILOT_D = 1.6                  # 1.6 = tap for M2 (aluminium), 3.2 = M2 heat-set insert (3D print)
PCB_CLEAR_D = 2.4                  # laser-cut plate: holes for off-the-shelf M2 brass standoffs

SCREEN_TEXT = ("Key Presses", "500")

OUT = os.path.join(os.path.expanduser("~"), "Downloads", "o3c_case")
os.makedirs(OUT, exist_ok=True)
TOP_Z = BOTTOM_H + TOP_H           # height of the top surface

#===============================================================================
# Model
#===============================================================================

def rounded_box(w, d, h, r):
    """Box centred on the origin, sitting on z=0, with rounded vertical corners."""
    return cq.Workplane("XY").rect(w, d).extrude(h).edges("|Z").fillet(r)

def rounded_cut(x, y, w, d, z0, h, r):
    """Rounded box at (x, y) starting at height z0 - used to cut openings and pockets."""
    return (cq.Workplane("XY", origin=(x, y, z0)).rect(w, d).extrude(h)
            .edges("|Z").fillet(r))

def pins(points, d, z0, h):
    """Vertical cylinders at each (x, y) point - used for posts, standoffs and holes."""
    return cq.Workplane("XY", origin=(0, 0, z0)).pushPoints(points).circle(d / 2).extrude(h)

# M3 screw positions: SCREW_INSET in from each edge, one per corner
sx, sy = CASE_W / 2 - SCREW_INSET, CASE_D / 2 - SCREW_INSET
screws = [(x, y) for x in (-sx, sx) for y in (-sy, sy)]   # all 4 combinations of left/right, front/back

# top shell: hollow box, open at the bottom, chamfered top edge
top = rounded_box(CASE_W, CASE_D, TOP_H, CORNER_R).faces(">Z").edges().chamfer(TOP_CHAMFER)
top = top.cut(rounded_box(CASE_W - 2 * WALL, CASE_D - 2 * WALL, TOP_H - WALL, CORNER_R - WALL))
# corner posts from the roof down, for the M3 screws coming up through the bottom plate
top = top.union(pins(screws, SCREW_POST_D, 0, TOP_H - WALL))

# key opening fits all keys in a row plus a small gap around the keycaps
key_open_w = KEY_COUNT * KEY_PITCH + KEY_OPENING_PAD
key_open_d = KEY_PITCH + KEY_OPENING_PAD
# everything to subtract from the shell (cuts start at -1 / overshoot by 2 so they go cleanly through)
cuts = [
    # switches/keycaps: plain through opening
    rounded_cut(0, KEY_ROW_Y, key_open_w, key_open_d, -1, TOP_H + 2, KEY_OPENING_R),
    # screen: stepped bezel pocket + window
    rounded_cut(*SCREEN_POS, SCREEN_W + 2 * SCREEN_BEZEL, SCREEN_H + 2 * SCREEN_BEZEL,
                TOP_H - SCREEN_POCKET_DEPTH, SCREEN_POCKET_DEPTH + 1, SCREEN_POCKET_R),
    rounded_cut(*SCREEN_POS, SCREEN_W, SCREEN_H, -1, TOP_H + 2, SCREEN_OPENING_R),
    # knob shaft + USB-C
    cq.Workplane("XY", origin=(*KNOB_POS, -1)).circle(KNOB_HOLE_D / 2).extrude(TOP_H + 2),
    cq.Workplane("XY").box(USB_W, WALL * 3, USB_H).edges("|Y").fillet(USB_H / 2 - 0.01)
      .translate((USB_X, CASE_D / 2 - WALL / 2, USB_H / 2 + 2.0)),
    # M3 pilot holes in the corner posts
    pins(screws, SCREW_PILOT_D, -1, SCREW_DEPTH + 1),
]
for c in cuts:
    top = top.cut(c)
top = top.translate((0, 0, BOTTOM_H)) #Raises the top so it sits ontop of the bottom instead of overlapping

# bottom plate: M3 clearance holes (countersink by hand)
bottom = rounded_box(CASE_W, CASE_D, BOTTOM_H, CORNER_R).cut(pins(screws, 3.4, -1, BOTTOM_H + 2))
# laser-cut version stays flat: PCB holes take off-the-shelf M2 brass standoffs instead
plate_flat = bottom.cut(pins(PCB_HOLES, PCB_CLEAR_D, -1, BOTTOM_H + 2))
# CNC / 3D print version: standoffs built in, PCB screws down into them (1 mm floor left under each hole)
bottom = bottom.union(pins(PCB_HOLES, PCB_STANDOFF_D, BOTTOM_H, PCB_STANDOFF_H))
bottom = bottom.cut(pins(PCB_HOLES, PCB_PILOT_D, 1.0, BOTTOM_H + PCB_STANDOFF_H))

#===============================================================================
# Display-Only Parts
# NOT included in the STEP/DXF files sent for manufacturing
#===============================================================================

# keycaps (Cherry-ish profile)
keycaps = cq.Workplane("XY")
for i in range(KEY_COUNT):
    x = (i - (KEY_COUNT - 1) / 2) * KEY_PITCH   # spread keys evenly around x=0 (-19.05, 0, 19.05)
    cap = (cq.Workplane("XY", origin=(x, KEY_ROW_Y, TOP_Z - 4.0))
           .rect(KEY_PITCH - 1.4, KEY_PITCH - 1.4).workplane(offset=8.5)
           .rect(KEY_PITCH - 5.5, KEY_PITCH - 6.5).loft().edges().fillet(0.9))
    keycaps = keycaps.union(cap)

# knurled knob: star-shaped profile = knurl ridges, smooth top with indicator line
r_out, r_in = KNOB_D / 2, KNOB_D / 2 - 0.45
pts = []   # points around the knob, alternating outer/inner radius to make the ridges
for i in range(KNURL_TEETH * 2):
    a = math.pi * i / KNURL_TEETH
    r = r_out if i % 2 == 0 else r_in
    pts.append((KNOB_POS[0] + r * math.cos(a), KNOB_POS[1] + r * math.sin(a)))
knob = cq.Workplane("XY", origin=(0, 0, TOP_Z + 0.6)).polyline(pts).close().extrude(KNOB_H - 2.5)
knob = knob.union(cq.Workplane("XY", origin=(*KNOB_POS, TOP_Z + 0.6 + KNOB_H - 2.5))
                  .circle(r_out - 0.3).extrude(2.5).faces(">Z").edges().chamfer(0.8))
indicator = (cq.Workplane("XY").box(0.7, r_out - 2.5, 1.0)
             .translate((KNOB_POS[0], KNOB_POS[1] + (r_out - 2.5) / 2 + 1.2, TOP_Z + 0.6 + KNOB_H)))
knob_line = indicator.intersect(cq.Workplane("XY", origin=(*KNOB_POS, TOP_Z)).circle(r_out).extrude(KNOB_H + 2))

# braided cable: plug boot + swept cable leaving the back
plug_y = CASE_D / 2
plug = (cq.Workplane("XZ", origin=(USB_X, plug_y, BOTTOM_H + USB_H / 2 + 2.0))
        .rect(12, 7).extrude(-16).edges("|Y").fillet(3.0))
path = cq.Workplane("XY").spline(
    [(USB_X, plug_y + 15, BOTTOM_H + 4.5), (USB_X - 8, plug_y + 45, 4.0),
     (USB_X - 30, plug_y + 90, 2.6), (USB_X - 70, plug_y + 140, 2.6)], includeCurrent=False)
cable = (cq.Workplane("XZ", origin=(USB_X, plug_y + 15, BOTTOM_H + 4.5))
         .circle(2.6).sweep(path, transition="round"))

desk = cq.Workplane("XY").box(3000, 3000, 2).translate((0, 0, -1))

#===============================================================================
# Export
#===============================================================================

#Exports the Top/Bottom step files for the CNC machine
cq.exporters.export(top, f"{OUT}/o3c_case_top.step")
cq.exporters.export(bottom, f"{OUT}/o3c_case_bottom.step")

# 2D outline for laser cutting the bottom plate
outline = plate_flat.faces("<Z").val()
outline = outline.translate(cq.Vector(0, 0, -outline.Center().z))
cq.exporters.export(cq.Workplane("XY").add(outline), f"{OUT}/o3c_case_bottom_lasercut.dxf")

# STL files: top/bottom for 3D-print test fits, all parts are loaded by the render below
parts = {"top": top, "bottom": bottom, "keycaps": keycaps, "knob": knob,
         "knob_line": knob_line, "plug": plug, "cable": cable, "desk": desk}
for name, shape in parts.items():
    cq.exporters.export(shape, f"{OUT}/{name}.stl", tolerance=0.02, angularTolerance=0.08)

#===============================================================================
# Render
# NOT included in the STEP/DXF files sent for manufacturing
#===============================================================================

# screen image (what the display shows)
def make_screen_png(path, w=480, h=260):
    """Draw the fake screen contents (title, number, bar icon) as an image for the render."""
    img = Image.new("RGB", (w, h), (8, 9, 12))
    d = ImageDraw.Draw(img)
    def font(size, bold=False):
        for f in (["DejaVuSans-Bold.ttf"] if bold else ["DejaVuSans.ttf"]):
            try:
                return ImageFont.truetype(f, size)
            except OSError:
                pass
        return ImageFont.load_default()
    d.text((34, 38), SCREEN_TEXT[0], fill=(225, 228, 235), font=font(34))
    d.text((34, 92), SCREEN_TEXT[1], fill=(245, 247, 250), font=font(84, bold=True))
    d.line((34, 205, w - 34, 205), fill=(70, 74, 82), width=3)
    for i, bh in enumerate((14, 24, 18, 30)):           # little bar-graph icon
        d.rectangle((w - 80 + i * 11, 64 - bh, w - 74 + i * 11, 64), fill=(225, 228, 235))
    img.save(path)

make_screen_png(f"{OUT}/screen.png")

MATERIALS = {   # colour, diffuse, specular, specular power, ambient
    "top":       ((0.085, 0.085, 0.09), 0.95, 0.30, 18, 0.30),  # matte black anodised
    "bottom":    ((0.075, 0.075, 0.08), 0.95, 0.30, 18, 0.30),
    "keycaps":   ((0.07, 0.07, 0.075), 1.00, 0.10, 6, 0.30),    # PBT keycaps
    "knob":      ((0.07, 0.07, 0.075), 0.90, 0.55, 30, 0.30),   # knurled aluminium
    "knob_line": ((0.85, 0.85, 0.85), 0.80, 0.30, 20, 0.60),
    "plug":      ((0.06, 0.06, 0.065), 0.90, 0.30, 15, 0.30),
    "cable":     ((0.05, 0.05, 0.055), 1.00, 0.15, 8, 0.30),    # braided cable
    "desk":      ((0.13, 0.13, 0.135), 1.00, 0.02, 2, 0.35),    # desk mat
}

def actor_from_stl(path):
    """Load an STL into VTK as a renderable object, with smoothed shading."""
    reader = vtk.vtkSTLReader(); reader.SetFileName(path)
    normals = vtk.vtkPolyDataNormals(); normals.SetInputConnection(reader.GetOutputPort())
    normals.SetFeatureAngle(30)
    mapper = vtk.vtkPolyDataMapper(); mapper.SetInputConnection(normals.GetOutputPort())
    actor = vtk.vtkActor(); actor.SetMapper(mapper)
    return actor

def screen_actor():
    """Flat rectangle in the screen pocket, textured with screen.png."""
    plane = vtk.vtkPlaneSource()
    x, y, z = SCREEN_POS[0], SCREEN_POS[1], TOP_Z - SCREEN_POCKET_DEPTH - 0.4
    plane.SetOrigin(x - SCREEN_W / 2, y - SCREEN_H / 2, z)
    plane.SetPoint1(x + SCREEN_W / 2, y - SCREEN_H / 2, z)
    plane.SetPoint2(x - SCREEN_W / 2, y + SCREEN_H / 2, z)
    reader = vtk.vtkPNGReader(); reader.SetFileName(f"{OUT}/screen.png")
    tex = vtk.vtkTexture(); tex.SetInputConnection(reader.GetOutputPort()); tex.InterpolateOn()
    mapper = vtk.vtkPolyDataMapper(); mapper.SetInputConnection(plane.GetOutputPort())
    actor = vtk.vtkActor(); actor.SetMapper(mapper); actor.SetTexture(tex)
    p = actor.GetProperty(); p.SetAmbient(1.0); p.SetDiffuse(0.0)
    p.SetSpecular(0.6); p.SetSpecularPower(80)                 # glossy glass reflection
    return actor

def render(path, azimuth, elevation, zoom=0.85):
    """Render all parts to a PNG. azimuth = angle around the case, elevation = angle from above."""
    ren = vtk.vtkRenderer()
    ren.GradientBackgroundOn()
    ren.SetBackground(0.05, 0.05, 0.055); ren.SetBackground2(0.12, 0.12, 0.13)
    for name, (col, dif, spec, power, amb) in MATERIALS.items():
        a = actor_from_stl(f"{OUT}/{name}.stl")
        p = a.GetProperty()
        p.SetColor(*col); p.SetDiffuse(dif); p.SetSpecular(spec)
        p.SetSpecularPower(power); p.SetAmbient(amb)
        ren.AddActor(a)
    ren.AddActor(screen_actor())
    # soft studio lighting: key light front-left, fill right, strong rim from behind
    ren.RemoveAllLights()
    for pos, inten in [((-180, -160, 260), 1.0), ((220, -120, 140), 0.45), ((40, 260, 160), 1.1)]:
        light = vtk.vtkLight(); light.SetPositional(False)
        light.SetPosition(*pos); light.SetFocalPoint(0, 0, 10)
        light.SetIntensity(inten); ren.AddLight(light)
    ren.UseSSAOOn(); ren.SetSSAORadius(6.0); ren.SetSSAOBias(0.05); ren.SetSSAOKernelSize(128)
    cam = ren.GetActiveCamera()
    cam.SetFocalPoint(0, 4, 10); cam.SetPosition(0, -260, 10); cam.SetViewUp(0, 0, 1)
    cam.Azimuth(azimuth); cam.Elevation(elevation); cam.SetViewAngle(22)
    cam.SetClippingRange(1, 2000)
    cam.Zoom(zoom)
    win = vtk.vtkRenderWindow(); win.SetOffScreenRendering(1); win.AddRenderer(ren)
    win.SetSize(1600, 1400); win.SetMultiSamples(8); win.Render()
    ren.ResetCameraClippingRange(); win.Render()
    grab = vtk.vtkWindowToImageFilter(); grab.SetInput(win); grab.Update()
    writer = vtk.vtkPNGWriter(); writer.SetFileName(path)
    writer.SetInputConnection(grab.GetOutputPort()); writer.Write()

render(f"{OUT}/o3c_case_render.png", azimuth=-25, elevation=42)
render(f"{OUT}/o3c_case_render_back.png", azimuth=150, elevation=28)
print("Done ->", OUT)
