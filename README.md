# SayoDevice O3C Case

A parametric matte black aluminium case for the SayoDevice O3C macropad, built in Python with [CadQuery](https://cadquery.readthedocs.io/).

![Front view of the O3C case](Rendered-OC3.png)

![Back view showing the USB-C port](o3c_case_render_back.png)

## Design

- Two parts: a top shell and a flat bottom plate held together with M3 screws
- A single key opening with large corner radii, which keeps machining cheap
- A stepped bezel pocket around the 0.96" screen
- Knurled volume knob and a USB-C slot in the back wall

> **Note:** All dimensions are estimates. Measure your O3C's PCB with calipers and edit the parameters at the top of `Sayodevice-case.py` before ordering anything.

## Usage

Install the dependencies (first time only):

```
py -m pip install cadquery pillow
```

Run the script:

```
py Sayodevice-case.py
```

Files are written to `~/Downloads/o3c_case`.

## Output files

| File | Use |
|---|---|
| `o3c_case_top.step`, `o3c_case_bottom.step` | Send to a CNC shop for an aluminium quote |
| `o3c_case_bottom_lasercut.dxf` | 2D outline for laser cutting the bottom plate |
| `top.stl`, `bottom.stl` | 3D print these for a test fit before ordering metal |
| `keycaps`, `knob`, `knob_line`, `plug`, `cable`, `desk` `.stl` | Props for the render only |
| `o3c_case_render.png`, `o3c_case_render_back.png` | Preview renders |
| `screen.png` | Screen texture used in the render |
