# DVD Bounce VGA ASIC

My ASIC recreates the classic bouncing DVD logo screensaver over VGA. It draws
the logo pixel by pixel, moves it around a 640x480 display, reverses it at the
edges, and changes colour after each bounce.

The design is written in Verilog for a one-tile Tiny Tapeout GF180 submission.
It uses a 25.175 MHz pixel clock and does not need a framebuffer or font ROM.

Read the full project write-up: [Making a DVD Bounce VGA ASIC](https://crabby605.vercel.app/writing/dvd-bounce-vga.html)

## Repository layout

- `src/` — synthesizable Verilog and LibreLane configuration
- `test/` — cocotb RTL tests
- `.github/workflows/` — test, GDS, documentation, and FPGA CI workflows
- `docs/info.md` — Tiny Tapeout datasheet text

## Local test

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r test/requirements.txt
make test
```
