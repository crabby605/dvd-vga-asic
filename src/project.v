// SPDX-FileCopyrightText: © 2026 Vihaan
// SPDX-License-Identifier: Apache-2.0

`default_nettype none

// IO block for tile
module tt_um_crabby605_dvd (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);
    wire       hsync_n;
    wire       vsync_n;
    wire [1:0] red;
    wire [1:0] green;
    wire [1:0] blue;

    dvd_bounce dvd (
        .pixel_clk (clk), .reset_n (rst_n), .hsync_n (hsync_n),
        .vsync_n (vsync_n), .red (red), .green (green), .blue (blue)
    );

    // hsync, B0, G0, R0, vsync, B1, G1, R1
    // VGA out map
    assign uo_out = {hsync_n, blue[0], green[0], red[0],
                     vsync_n, blue[1], green[1], red[1]};
    assign uio_out = 8'h00;
    assign uio_oe  = 8'h00;

    wire _unused = &{ena, ui_in, uio_in, 1'b0};
endmodule

`default_nettype wire
