# SPDX-FileCopyrightText: (c) 2026 Vihaan
# SPDX-License-Identifier: Apache-2.0


import os
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, ReadOnly, RisingEdge, Timer
from cocotb.utils import get_sim_time

PERIOD_PS = 39722  # 25.175 MHz pixel clock
H_TOTAL = 800
V_TOTAL = 525
FRAME_CYCLES = H_TOTAL * V_TOTAL
H_VISIBLE = 640
V_VISIBLE = 480

HSYNC_BIT = 7
VSYNC_BIT = 3
IDLE_VALUE = 0x88  # both syncs inactive (high), RGB black
RGB_MASK = 0x77    # R1 G1 B1 (bits 0-2) and R0 G0 B0 (bits 4-6)

# Lit logo pixels, relative to the top-left of the 128x64 box (2x scaled art).
LOGO_X_MIN, LOGO_X_MAX = 8, 121
LOGO_Y_MIN, LOGO_Y_MAX = 4, 49

START_X, START_Y = 256, 208  # box position after reset
STEP = 2                     # pixels moved per frame
MAX_BOX_X = 640 - 128
MAX_BOX_Y = 480 - 64

# Full frames are too slow at gate level; the GL job sets GATES=yes.
GATE_LEVEL = os.getenv('GATES') == 'yes'


class OutputMonitor:
    '''Records every change of uo_out so frames can be checked without polling.'''

    def __init__(self, dut):
        self.dut = dut
        self.raw = []
        cocotb.start_soon(self._watch())

    async def _watch(self):
        while True:
            await self.dut.uo_out.value_change
            value = self.dut.uo_out.value
            if value.is_resolvable:
                self.raw.append((get_sim_time('ps'), int(value)))

    def changes(self, t0):
        '''Return [(cycle, value)] for cycle >= 0: one entry per cycle, changes only.'''
        last = {}
        for time_ps, value in self.raw:
            # several partial updates can land in one cycle; the last one wins
            last[round((time_ps - t0) / PERIOD_PS)] = value
        out = []
        prev = IDLE_VALUE
        for cycle in sorted(last):
            if cycle < 0:
                prev = last[cycle]
            elif last[cycle] != prev:
                out.append((cycle, last[cycle]))
                prev = last[cycle]
        return out


async def start_and_reset(dut):
    '''Start the clock, reset, and return (monitor, time of the first non-reset edge).'''
    cocotb.start_soon(Clock(dut.clk, PERIOD_PS, unit='ps').start())
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    monitor = OutputMonitor(dut)
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    return monitor, get_sim_time('ps')


async def run_frames(dut, frames, setup=None):
    '''Reset, optionally poke internal state, run N frames, return the output changes.'''
    monitor, t0 = await start_and_reset(dut)
    if setup is not None:
        setup(dut.user_project.dvd)
    await Timer(frames * FRAME_CYCLES * PERIOD_PS + PERIOD_PS // 2, unit='ps')
    return monitor.changes(t0)


def edges_of(changes, bit):
    '''Return [(cycle, new_level)] for every transition of one output bit.'''
    out = []
    prev = IDLE_VALUE
    for cycle, value in changes:
        if ((value ^ prev) >> bit) & 1:
            out.append((cycle, (value >> bit) & 1))
        prev = value
    return out


def pixel_of(cycle):
    frame, n = divmod(cycle, FRAME_CYCLES)
    y, x = divmod(n, H_TOTAL)
    return frame, x, y


def lit_spans(changes, end_cycle):
    '''Return [(first_cycle, end_cycle_exclusive, colour)] for each non-black run.'''
    spans = []
    start = colour = None
    for cycle, value in changes:
        now = value & RGB_MASK
        if start is not None and now != colour:
            spans.append((start, cycle, colour))
            start = None
        if now and start is None:
            start, colour = cycle, now
    if start is not None:
        spans.append((start, end_cycle, colour))
    return spans


def frame_boxes(changes, frames):
    '''Return {frame: (box_x, box_y, colours)} recovered from the lit pixels.'''
    bounds = {}
    for first, end, colour in lit_spans(changes, frames * FRAME_CYCLES):
        frame, x0, y0 = pixel_of(first)
        last_frame, x1, y1 = pixel_of(end - 1)
        assert (frame, y0) == (last_frame, y1), 'a lit run must stay on one line'
        b = bounds.setdefault(frame, {'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1, 'colours': set()})
        b['x0'], b['y0'] = min(b['x0'], x0), min(b['y0'], y0)
        b['x1'], b['y1'] = max(b['x1'], x1), max(b['y1'], y1)
        b['colours'].add(colour)

    boxes = {}
    for frame, b in bounds.items():
        assert b['x1'] < H_VISIBLE and b['y1'] < V_VISIBLE, f'frame {frame}: pixels lit in blanking'
        assert b['x1'] - b['x0'] == LOGO_X_MAX - LOGO_X_MIN, f'frame {frame}: logo width {b}'
        assert b['y1'] - b['y0'] == LOGO_Y_MAX - LOGO_Y_MIN, f'frame {frame}: logo height {b}'
        boxes[frame] = (b['x0'] - LOGO_X_MIN, b['y0'] - LOGO_Y_MIN, b['colours'])
    return boxes


def single_colour(colours):
    assert len(colours) == 1, f'expected one logo colour, saw {colours}'
    return next(iter(colours))


@cocotb.test()
async def test_reset_state_and_unused_pins(dut):
    '''After reset: syncs inactive, RGB black, bidirectional pins unused.'''
    await start_and_reset(dut)
    await ReadOnly()
    assert int(dut.uo_out.value) == IDLE_VALUE, f'uo_out after reset = {int(dut.uo_out.value):#04x}'
    assert int(dut.uio_oe.value) == 0, 'all bidirectional pins must be inputs'
    assert int(dut.uio_out.value) == 0, 'bidirectional outputs must be zero'


@cocotb.test()
async def test_hsync_timing(dut):
    '''HSYNC is low for 96 of every 800 clocks, from 656 to 751, and nothing else moves.'''
    monitor, t0 = await start_and_reset(dut)
    await Timer(3 * H_TOTAL * PERIOD_PS + PERIOD_PS // 2, unit='ps')

    prev = IDLE_VALUE
    for cycle, value in monitor.changes(t0):
        assert ((value ^ prev) & ~(1 << HSYNC_BIT) & 0xFF) == 0, f'only HSYNC may change in lines 0-2 (cycle {cycle})'
        prev = value
    edges = edges_of(monitor.changes(t0), HSYNC_BIT)
    expected = [(656, 0), (752, 1), (1456, 0), (1552, 1), (2256, 0), (2352, 1)]
    assert edges == expected, f'HSYNC edges {edges}'


@cocotb.test(skip=GATE_LEVEL)
async def test_frame_timing_and_logo_motion(dut):
    '''Three full frames: VSYNC window and period, 525 lines, logo steps 2 px diagonally.'''
    frames = 3
    changes = await run_frames(dut, frames)

    vsync = edges_of(changes, VSYNC_BIT)
    expected_vsync = []
    for f in range(frames):
        expected_vsync += [(f * FRAME_CYCLES + 490 * H_TOTAL, 0), (f * FRAME_CYCLES + 492 * H_TOTAL, 1)]
    assert vsync == expected_vsync, f'VSYNC edges {vsync}'

    hsync = edges_of(changes, HSYNC_BIT)
    falls = [c for c, level in hsync if level == 0]
    rises = [c for c, level in hsync if level == 1]
    assert len(falls) == len(rises) == frames * V_TOTAL, f'{len(falls)} HSYNC pulses in {frames} frames'
    assert all(c % H_TOTAL == 656 for c in falls), 'HSYNC must fall at pixel 656'
    assert all(c % H_TOTAL == 752 for c in rises), 'HSYNC must rise at pixel 752'

    boxes = frame_boxes(changes, frames)
    assert sorted(boxes) == list(range(frames)), f'frames with a logo: {sorted(boxes)}'
    colours = set()
    for f in range(frames):
        x, y, frame_colours = boxes[f]
        assert (x, y) == (START_X + STEP * f, START_Y + STEP * f), f'frame {f}: box at {(x, y)}'
        colours.add(single_colour(frame_colours))
    assert len(colours) == 1, 'colour must not change without a bounce'


@cocotb.test(skip=GATE_LEVEL)
async def test_bounce_off_right_and_bottom_edges(dut):
    '''Box starting 2 px short of the right and bottom limits bounces and changes colour.'''
    def setup(dvd):
        dvd.box_x.value = MAX_BOX_X - STEP
        dvd.box_y.value = MAX_BOX_Y - STEP

    frames = 3
    boxes = frame_boxes(await run_frames(dut, frames, setup), frames)
    positions = [boxes[f][:2] for f in range(frames)]
    assert positions == [(510, 414), (512, 416), (510, 414)], f'positions {positions}'
    c0, c1, c2 = (single_colour(boxes[f][2]) for f in range(frames))
    assert c1 != c0, 'colour must change on the bounce'
    assert c2 == c1, 'colour must hold when there is no bounce'


@cocotb.test(skip=GATE_LEVEL)
async def test_bounce_off_left_and_top_edges(dut):
    '''Box heading up-left bounces at the origin and changes colour once.'''
    def setup(dvd):
        dvd.box_x.value = 2 * STEP
        dvd.box_y.value = 2 * STEP
        dvd.moving_right.value = 0
        dvd.moving_down.value = 0

    frames = 4
    boxes = frame_boxes(await run_frames(dut, frames, setup), frames)
    positions = [boxes[f][:2] for f in range(frames)]
    assert positions == [(4, 4), (2, 2), (0, 0), (2, 2)], f'positions {positions}'
    c = [single_colour(boxes[f][2]) for f in range(frames)]
    assert c[1] == c[0], 'no bounce yet'
    assert c[2] != c[1], 'colour must change on the bounce'
    assert c[3] == c[2], 'colour must hold when there is no bounce'
