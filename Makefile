.PHONY: test lint

# Cocotb RTL tests. Needs iverilog and `pip install -r test/requirements.txt`.
test:
	$(MAKE) -C test

# Verilator lint of the synthesizable sources.
lint:
	verilator --lint-only -Wall -Wno-fatal src/project.v src/dvd_bounce.v src/vga_sync.v
