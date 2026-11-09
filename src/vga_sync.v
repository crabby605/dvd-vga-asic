// VGA timing and raster coordinate generator
`default_nettype none

// VGA Sync IO
module vga_sync (
    input  wire       pixel_clk,
    input  wire       reset_n,
    output reg        hsync_n,
    output reg        vsync_n,
    output reg        video_active,
    output wire [9:0] pixel_x,
    output wire [9:0] pixel_y
);

    localparam H_VISIBLE     = 640,
               H_FRONT_PORCH = 16,
               H_SYNC_PULSE  = 96,
               H_TOTAL       = 800,
               H_SYNC_START  = H_VISIBLE + H_FRONT_PORCH,
               H_SYNC_END    = H_SYNC_START + H_SYNC_PULSE;

    localparam V_VISIBLE     = 480,
               V_FRONT_PORCH = 10,
               V_SYNC_PULSE  = 2,
               V_TOTAL       = 525,
               V_SYNC_START  = V_VISIBLE + V_FRONT_PORCH,
               V_SYNC_END    = V_SYNC_START + V_SYNC_PULSE;

    reg [9:0] horizontal_count;
    reg [9:0] vertical_count;

    assign pixel_x = horizontal_count;
    assign pixel_y = vertical_count;

    wire last_pixel_in_line = (horizontal_count == H_TOTAL - 1);
    wire last_line_in_frame = (vertical_count == V_TOTAL - 1);

    always @(posedge pixel_clk) begin
        if (!reset_n) begin
            horizontal_count <= 0;
            vertical_count   <= 0;
        end else if (last_pixel_in_line) begin
            horizontal_count <= 0;
            vertical_count   <= last_line_in_frame ? 0 : vertical_count + 1'b1;
        end else begin
            horizontal_count <= horizontal_count + 1'b1;
        end
    end

    always @(posedge pixel_clk) begin
        if (!reset_n) begin
            hsync_n      <= 1;
            vsync_n      <= 1;
            video_active <= 0;
        end else begin
            hsync_n <= !((horizontal_count >= H_SYNC_START) &&
                         (horizontal_count < H_SYNC_END));

            vsync_n <= !((vertical_count >= V_SYNC_START) &&
                         (vertical_count < V_SYNC_END));

            video_active <= (horizontal_count < H_VISIBLE) &&
                            (vertical_count < V_VISIBLE);
        end
    end

endmodule

`default_nettype wire
