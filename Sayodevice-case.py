"""
Matte black aluminium enclosure for the SayoDevice O3C.

Builds a parametric 2-part case (top shell + base) with CadQuery,
exports STEP (for CNC quotes) + STL, and renders a studio image with VTK.

What stays from the original O3C: the PCB and the top acrylic frame (it holds
the screen). The roof of the top shell replaces the black metal switch plate,
the base replaces the bottom acrylic + bottom metal plate. Only the keycaps,
knob, screen and USB-C port are visible from outside.

Dimensions measured off the original plates (+-0.1 mm), except where a
parameter says "estimate".

Design: roof is ROOF thick, thinned to PLATE_T from the top in one long recess
under the keycaps and a round recess under the knob, so the switch clips catch
like on the original plate. 4 hidden M2 screws come up through the base, posts,
PCB and acrylic into tapped holes in the roof (the front two end flush with the
key recess floor, the same 1.4 mm of thread as the original plate).

Screws: 4x M2x12 countersunk, from underneath.

Outputs (~/Downloads/o3c_case):
  o3c_case_top/bottom.step       -> send to CNC shop for the aluminium case
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

# the original O3C stack that goes inside (measured)
OC3_W, OC3_D = 65.0, 50.0          # outline of the original plates / PCB
OC3_CORNER_R = 3.2                 # rough (+-0.3)
PCB_T = 1.5
ACRYLIC_T = 3.7                    # top acrylic frame, holds the screen
POST_H = 3.8                       # = old bottom acrylic, room for the hot-swap sockets under the PCB

# case
FIT_GAP = 0.3                      # clearance between the O3C stack and the inside walls, per side
WALL = 3.0                         # side wall thickness
FLOOR = 1.6                        # base thickness under the posts (sets how far M2x12 screws reach)
ROOF = 3.0                         # roof thickness (screw threads go in here)
PLATE_T = 1.4                      # roof thinned to this around switches/knob, same as the original plate
TOP_CHAMFER = 1.2                  # bright diamond-cut style edge around the top
CASE_W = OC3_W + 2 * (FIT_GAP + WALL)    # outer footprint -> 71.6 x 56.6
CASE_D = OC3_D + 2 * (FIT_GAP + WALL)
CORNER_R = OC3_CORNER_R + FIT_GAP + WALL # vertical corner radius, follows the O3C's corners
STACK_H = POST_H + PCB_T + ACRYLIC_T     # everything between base and roof (9.0)
TOP_H, BOTTOM_H = STACK_H + ROOF, FLOOR  # top shell height, base thickness

# switches (positions are centres, origin = middle of the case, front is -Y)
KEY_CAP_W = 18.2                   # single keycap width
KEY_PITCH = 20.0                   # switch hole spacing, centre to centre (measured off the original plate)
KEY_COUNT = 3
KEY_ROW_Y = -12.6
SWITCH_HOLE = 14.0                 # standard switch cutout
KEY_POCKET_CLEAR = 0.8             # gap around the keycaps in the recess (pressed caps sit ~1 mm above the plate)
KEY_POCKET_R = 1.5

SCREEN_W, SCREEN_H = 22.0, 11.0    # 0.96" IPS window (measured off the original plate)
SCREEN_BEZEL = 1.5                 # flat ledge between screen and pocket edge
SCREEN_POCKET_DEPTH = 1.0          # how far the screen bezel pocket sinks in
SCREEN_POCKET_R = 2.0
SCREEN_OPENING_R = 1.0
SCREEN_POS = (8.7, 11.0)

ENCODER_HOLE = 12.6                # square hole, the encoder body pokes ~0.9 mm up into it
KNOB_D, KNOB_H = 19.7, 15.0        # knob size (measured)
KNOB_POCKET_D = KNOB_D + 2.0       # recess under the knob down to PLATE_T so it sits like on the original
KNOB_POS = (-20.0, 11.1)
KNURL_TEETH = 70

USB_X = 19.6                       # port centre (measured 51.7 / 52.4 from the left edge, averaged)
USB_PORT_H = 3.3                   # port hangs this far below the PCB
USB_SLOT_W, USB_SLOT_H = 12.5, 7.0 # slot in the back wall, fits the cable plug's moulded boot

SCREW_INSET = 3.0                  # screw centres from the O3C plate edges (2.1 to the hole edge)
POST_D = 5.0                       # posts on the base the PCB sits on
SCREW_CLEAR_D = 2.4                # M2 clearance through base + posts
SCREW_CSK_D = 4.0                  # M2 countersunk head
SCREW_TAP_D = 1.6                  # M2 tap drill, holes in the roof underside
SCREW_TAP_DEPTH = 2.0              # M2x12 screws reach 1.4 in; front two break through into the key recess

SCREEN_TEXT = ("Key Presses", "500")

OUT = os.path.join(os.path.expanduser("~"), "Downloads", "o3c_case")
os.makedirs(OUT, exist_ok=True)
TOP_Z = BOTTOM_H + TOP_H           # height of the top surface
PLATE_Z = BOTTOM_H + STACK_H + PLATE_T   # height of the thinned roof the switches/knob sit on
USB_Z = BOTTOM_H + POST_H - USB_PORT_H / 2   # height of the USB-C port centre

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

def countersinks(points, d_head, d_hole):
    """90 degree countersink cones opening onto the underside (z=0)."""
    cones = cq.Workplane("XY")
    for x, y in points:
        cones = cones.union(cq.Workplane("XY", origin=(x, y, -0.01)).circle(d_head / 2)
                            .workplane(offset=(d_head - d_hole) / 2).circle(d_hole / 2).loft())
    return cones

# M2 screw positions: the original corner holes, SCREW_INSET in from each plate edge
sx, sy = OC3_W / 2 - SCREW_INSET, OC3_D / 2 - SCREW_INSET
screws = [(x, y) for x in (-sx, sx) for y in (-sy, sy)]   # all 4 combinations of left/right, front/back
key_xs = [(i - (KEY_COUNT - 1) / 2) * KEY_PITCH for i in range(KEY_COUNT)]   # (-20, 0, 20)

# USB-C slot in the back wall, in world coordinates (cuts both the top shell and the base)
# U-shaped: rounded top, open at the bottom - the port sits so low that a closed slot
# would leave a paper-thin sliver of base underneath
usb_len = FIT_GAP + WALL + 1
usb_y = OC3_D / 2 + usb_len / 2
usb_slot = (cq.Workplane("XY").box(USB_SLOT_W, usb_len, USB_SLOT_H)
            .edges("|Y").fillet(USB_SLOT_H / 2 - 0.01)
            .translate((USB_X, usb_y, USB_Z))
            .union(cq.Workplane("XY").box(USB_SLOT_W, usb_len, USB_Z + 1)
                   .translate((USB_X, usb_y, (USB_Z - 1) / 2))))

# top shell: hollow box, open at the bottom, chamfered top edge, cavity fits the O3C stack exactly
top = rounded_box(CASE_W, CASE_D, TOP_H, CORNER_R).faces(">Z").edges().chamfer(TOP_CHAMFER)
top = top.cut(rounded_box(OC3_W + 2 * FIT_GAP, OC3_D + 2 * FIT_GAP, STACK_H, OC3_CORNER_R + FIT_GAP))

# everything to subtract from the shell (cuts start below / overshoot so they go cleanly through)
pocket_z = STACK_H + PLATE_T       # floor of the key/knob recesses
key_pocket_w = (KEY_COUNT - 1) * KEY_PITCH + KEY_CAP_W + 2 * KEY_POCKET_CLEAR
key_pocket_d = KEY_CAP_W + 2 * KEY_POCKET_CLEAR
cuts = [
    # keys: one long recess the keycaps can press down into, plus the switch holes
    rounded_cut(0, KEY_ROW_Y, key_pocket_w, key_pocket_d, pocket_z, ROOF, KEY_POCKET_R),
    *[rounded_cut(x, KEY_ROW_Y, SWITCH_HOLE, SWITCH_HOLE, STACK_H - 1, ROOF + 2, 0.5) for x in key_xs],
    # screen: stepped bezel pocket + window
    rounded_cut(*SCREEN_POS, SCREEN_W + 2 * SCREEN_BEZEL, SCREEN_H + 2 * SCREEN_BEZEL,
                TOP_H - SCREEN_POCKET_DEPTH, SCREEN_POCKET_DEPTH + 1, SCREEN_POCKET_R),
    rounded_cut(*SCREEN_POS, SCREEN_W, SCREEN_H, STACK_H - 1, ROOF + 2, SCREEN_OPENING_R),
    # knob: round recess + square hole for the encoder body
    cq.Workplane("XY", origin=(*KNOB_POS, pocket_z)).circle(KNOB_POCKET_D / 2).extrude(ROOF),
    rounded_cut(*KNOB_POS, ENCODER_HOLE, ENCODER_HOLE, STACK_H - 1, ROOF + 2, 0.5),
    # USB-C (slot is in world coordinates, the shell is still sitting on z=0 here)
    usb_slot.translate((0, 0, -BOTTOM_H)),
    # M2 blind tapped holes in the roof underside
    pins(screws, SCREW_TAP_D, STACK_H - 1, SCREW_TAP_DEPTH + 1),
]
for c in cuts:
    top = top.cut(c)
top = top.translate((0, 0, BOTTOM_H)) #Raises the top so it sits ontop of the bottom instead of overlapping

# base: plate + posts the PCB sits on, countersunk M2 holes from underneath
bottom = rounded_box(CASE_W, CASE_D, BOTTOM_H, CORNER_R)
bottom = bottom.union(pins(screws, POST_D, BOTTOM_H, POST_H))
bottom = bottom.cut(pins(screws, SCREW_CLEAR_D, -1, BOTTOM_H + POST_H + 2))
bottom = bottom.cut(countersinks(screws, SCREW_CSK_D, SCREW_CLEAR_D))
bottom = bottom.cut(usb_slot)

#===============================================================================
# Display-Only Parts
# NOT included in the STEP files sent for manufacturing
#===============================================================================

# keycaps (Cherry-ish profile)
keycaps = cq.Workplane("XY")
for x in key_xs:
    cap = (cq.Workplane("XY", origin=(x, KEY_ROW_Y, PLATE_Z + 5.0))
           .rect(KEY_CAP_W, KEY_CAP_W).workplane(offset=8.5)
           .rect(KEY_CAP_W - 4.1, KEY_CAP_W - 5.1).loft().edges().fillet(0.9))
    keycaps = keycaps.union(cap)

# knurled knob: star-shaped profile = knurl ridges, smooth top with indicator line
KNOB_Z = PLATE_Z + 1.0             # knob sits just above the recess floor
r_out, r_in = KNOB_D / 2, KNOB_D / 2 - 0.45
pts = []   # points around the knob, alternating outer/inner radius to make the ridges
for i in range(KNURL_TEETH * 2):
    a = math.pi * i / KNURL_TEETH
    r = r_out if i % 2 == 0 else r_in
    pts.append((KNOB_POS[0] + r * math.cos(a), KNOB_POS[1] + r * math.sin(a)))
knob = cq.Workplane("XY", origin=(0, 0, KNOB_Z)).polyline(pts).close().extrude(KNOB_H - 2.5)
knob = knob.union(cq.Workplane("XY", origin=(*KNOB_POS, KNOB_Z + KNOB_H - 2.5))
                  .circle(r_out - 0.3).extrude(2.5).faces(">Z").edges().chamfer(0.8))
indicator = (cq.Workplane("XY").box(0.7, r_out - 2.5, 1.0)
             .translate((KNOB_POS[0], KNOB_POS[1] + (r_out - 2.5) / 2 + 1.2, KNOB_Z + KNOB_H)))
knob_line = indicator.intersect(cq.Workplane("XY", origin=(*KNOB_POS, KNOB_Z)).circle(r_out).extrude(KNOB_H + 2))

# braided cable: plug boot + swept cable leaving the back
plug_y = CASE_D / 2
plug = (cq.Workplane("XZ", origin=(USB_X, plug_y, USB_Z))
        .rect(USB_SLOT_W - 1, USB_SLOT_H - 0.6).extrude(-16).edges("|Y").fillet(3.0))
path = cq.Workplane("XY").spline(
    [(USB_X, plug_y + 15, USB_Z), (USB_X - 8, plug_y + 45, 4.0),
     (USB_X - 30, plug_y + 90, 2.6), (USB_X - 70, plug_y + 140, 2.6)], includeCurrent=False)
cable = (cq.Workplane("XZ", origin=(USB_X, plug_y + 15, USB_Z))
         .circle(2.6).sweep(path, transition="round"))

desk = cq.Workplane("XY").box(3000, 3000, 2).translate((0, 0, -1))

#===============================================================================
# Export
#===============================================================================

# STEP files for the top shell and base, sent to the shop for CNC machining
cq.exporters.export(top, f"{OUT}/o3c_case_top.step")
cq.exporters.export(bottom, f"{OUT}/o3c_case_bottom.step")

# STL files: top/bottom for 3D-print test fits, all parts are loaded by the render below
parts = {"top": top, "bottom": bottom, "keycaps": keycaps, "knob": knob,
         "knob_line": knob_line, "plug": plug, "cable": cable, "desk": desk}
for name, shape in parts.items():
    cq.exporters.export(shape, f"{OUT}/{name}.stl", tolerance=0.02, angularTolerance=0.08)

#===============================================================================
# Render
# NOT included in the STEP files sent for manufacturing
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
    """Flat rectangle under the screen window, textured with screen.png."""
    plane = vtk.vtkPlaneSource()
    x, y, z = SCREEN_POS[0], SCREEN_POS[1], BOTTOM_H + STACK_H - 0.3   # screen sits in the acrylic, under the roof
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
