## How it works

The design generates standard 640x480 VGA timing (800x525 total, HSYNC low for
96 clocks from pixel 656, VSYNC low for 2 lines from line 490) from a 25.175 MHz
pixel clock. A 128x64 pixel DVD-style mark moves two pixels per frame, both
horizontally and vertically, and reverses at the display edges. Its colour
changes after each bounce. The logo and its lettering are generated directly from
pixel-coordinate comparisons, so no framebuffer or font ROM is required.

`uo_out` uses the TinyVGA PMOD bit order: `HSYNC, B0, G0, R0, VSYNC, B1, G1, R1`.
HSYNC and VSYNC are active low; the RGB channels are two bits each. The
bidirectional pins and `ui_in` are unused.

## How to test

Apply a 25.175 MHz clock to `clk`, hold `rst_n` low for at least one clock, then
release it. A TinyVGA PMOD on the outputs and a VGA monitor will show the logo
bouncing around the screen.

The cocotb tests in `test/test.py` check, using only the project pins:

- the reset state (syncs inactive, RGB black, bidirectional pins unused)
- HSYNC timing over the first lines
- VSYNC window and period, 525 HSYNC pulses per frame, and the logo stepping two
  pixels diagonally per frame (RTL only)
- bouncing and colour change at the right, bottom, left, and top edges (RTL only)

Run them locally with:

```sh
cd test
make
```

## External hardware

A TinyVGA-compatible resistor-DAC PMOD and a VGA monitor are required to view the
output.
