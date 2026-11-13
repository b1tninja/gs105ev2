# Ghidra pass — confirms the 8051 CPU hypothesis

Connected to a running Ghidra instance via `ghidra-mcp` (TCP bridge on
`127.0.0.1:8089`; connect with `connect_instance(project=...)`, any project
name works for the TCP fallback). This is **not scripted/reproducible from
this repo yet** — it was done interactively against a live Ghidra session
the user already had open; see "Reproducing this" below for the exact
steps if picked back up later.

## Setup

1. Took `GS105Ev2_V1.6.0.25.bin` (see `../downloads/firmware/`), stripped the
   20-byte container header (see [`FIRMWARE-FORMAT.md`](FIRMWARE-FORMAT.md))
   to get a raw payload file.
2. Imported the raw payload with `import_file(language="8051:BE:16:default")`
   — Ghidra's bundled 8051/MCS-51 processor module, big-endian, 16-bit
   addressing. This is a guess informed by the boot-stub byte pattern
   (heavy `0x75` density) noted in `FIRMWARE-FORMAT.md`; it loaded and
   disassembled cleanly, which is itself evidence for the guess (a wrong
   processor/endianness choice produces instructions that don't cohere,
   e.g. operand bytes decoding into operators that never form a connected,
   self-consistent trace).

## 8051 confirmed by direct disassembly

The reset vector at `CODE:0000` disassembles to a single clean instruction:

```
CODE:0000: LJMP 0x1016
```

A 3-byte `LJMP` at address 0 is the standard 8051 reset vector pattern.
Following it to `0x1016`:

```
CODE:1016: DJNZ R5,0x101c
CODE:1018: LJMP 0x1190
CODE:101c: DJNZ R5,0x0ffb
CODE:101e: LJMP 0x1190
```

Every instruction here decodes self-consistently: operand lengths and
relative-branch targets line up exactly with where the next instruction
starts (double-checked by hand against the raw hex — `DD 04` at `0x1016`
is `DJNZ R5` with relative offset `+4` from `0x1018`, landing exactly on
`0x101c`; `DD DD` at `0x101c` is `DJNZ R5` with relative offset `-35` from
`0x101e`, landing exactly on `0x0ffb`). A wrong processor/endian guess
essentially never produces this kind of coherent, self-validating chain by
accident. **This resolves the "8051 hypothesis" from
[`FIRMWARE-FORMAT.md`](FIRMWARE-FORMAT.md) to a confirmed fact**: the
GS105Ev2's management CPU core is 8051-family, not MIPS.

`LJMP 0x1190` leads to a 2-instruction stub (`MOV R3,A; RET`) — likely one
small helper in a longer call chain, not the real application entry; tracing
the real startup/main loop further is future work, not attempted this pass.

## A real structural finding: code is capped at 64 KiB, assets live beyond it

Ghidra's 8051 memory map uses a native 64 KiB `CODE` address space
(`CODE:0000`-`CODE:ffff`), matching the 8051 ISA's 16-bit code addressing.
The raw import therefore only maps the **first 64 KiB of the 682,856-byte
payload** — everything from `0x10000` onward (where the PNG icons and the
11 gzip-compressed web-UI assets found via binwalk all live, per
`FIRMWARE-FORMAT.md`) is **not present in this Ghidra project at all**.

This is a coherent reading of the firmware layout, not a limitation to
paper over: a plain 8051 core only executes code from its own 64 KiB code
space, so **executable code is confined to the first 64 KiB of the
payload**, and everything beyond that is a **data/resource region** (web
assets, strings, possibly configuration defaults) that application code
reads via some data-fetch mechanism rather than executing directly. This
matches the earlier, independent finding (`FIRMWARE-FORMAT.md`) that all of
the binwalk-identified PNGs and gzip blobs sit well past offset `0x10000`.

**Open question for later work:** if the real firmware image is larger
than 64 KiB of *code* (not just data) — i.e. if there's 8051 bank-switched
code beyond the first 64 KiB — that would need the bank-select SFR/scheme
identified and modeled in Ghidra (a memory-map overlay), which was not
investigated this pass. Nothing found so far indicates this is the case;
the data past `0x10000` looks like resources, not more code.

## Next steps (not done this pass)

- Trace from `CODE:0x1190` onward to find the real application entry point
  and the NSDP-handling / httpd-handling routines (would corroborate
  `docs/NSDP-PROTOCOL.md` and `docs/WEBUI-AUTH.md` against actual code).
- Cross-reference the `RTL8367N`/`RTL8367B` string locations found earlier
  with their callers, to find the switch-register-access driver code.
- Decide whether the firmware's `0x08`/`0x0C` header fields (still
  unidentified per `FIRMWARE-FORMAT.md`) are validated by a bootloader —
  would need the (not publicly distributed) bootloader image to check.

## Reproducing this

```powershell
# 1. Strip the 20-byte header (see tools/fw_header.py for the format)
python -c "d=open('GS105Ev2_V1.6.0.25.bin','rb').read(); open('payload.bin','wb').write(d[20:])"

# 2. With a Ghidra instance running its MCP bridge (ghidra-mcp, default
#    port 8089), from an MCP-enabled client:
#    connect_instance(project=<any running project name>)
#    import_file(file_path=<...payload.bin>, language="8051:BE:16:default")
#    create_function(address="0000")   # reset vector
#    disassemble_function(address="0000")
```
