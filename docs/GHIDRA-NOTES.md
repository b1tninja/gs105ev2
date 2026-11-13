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

## Round 2 — full linear disassembly + decompiler sanity check

Ran `disassemble_bytes` across the entire mapped `CODE:0000`-`CODE:fffe`
range (not just following call/jump flow), then `run_analysis` again: the
function count went from 5 (manually seeded) to **347**. This is a coarse
linear sweep, not a flow-accurate one — some of those 347 "functions" are
almost certainly disassembler noise where embedded data was decoded as
instructions — but it's a reasonable corpus to spot-check.

**Decompiler sanity check:** `decompile_function` on `FUN_CODE_1009`
(a caller of `main_init`, found via `get_function_callers(1190)`) produces
clean, plausible pseudocode:

```c
void FUN_CODE_1009(void)
{
  main_init(0x9b3e);
  return;
}
```

A working decompiler output (not garbage) from a raw disassembly is further
independent evidence the 8051 processor/endianness choice is correct — a
wrong guess tends to produce decompiler output that's visibly nonsensical
(wrong-size operands, impossible control flow), not clean single-call
functions like this.

**String cross-references did not resolve — an informative negative
result, not a success.** Located the `RTL8367N` string directly in the
mapped region at `CODE:55e2`/`CODE:55f1` (confirmed by byte-pattern search
on the ASCII bytes, so the address is right), and the TCP-state and
DHCP-dump debug strings cited in `FIRMWARE-FORMAT.md`
(`CODE:5672` "LISTEN", `CODE:f0eb` "-- [DHCP HDR dump] --", etc.). But:

- `get_xrefs_to` found **no references** to any of them.
- A byte-pattern search for the literal-load instruction encoding
  (`MOV DPTR,#addr` = `90 <hi> <lo>`, e.g. `90 55 E2`) found **no matches**
  anywhere in the mapped 64 KiB.
- A byte-pattern search for just the raw 2-byte address (in case it's
  stored in a pointer table rather than as an instruction operand, e.g.
  `56 72` for the "LISTEN" string) also found **no matches**.

Two explanations, not distinguished this pass: (a) this particular 8051
Sleigh module doesn't synthesize xrefs for `MOV DPTR,#imm16` operands (a
known limitation in some third-party 8051 Ghidra modules — DPTR is used
for both code and external-data access, and the semantics may not be
annotated for automatic reference creation), so the *real* call sites exist
in the disassembly but aren't being surfaced as xrefs or found by the
literal-byte searches because the compiler used some addressing form other
than a flat 16-bit immediate; or (b) these are debug-only strings
(`"buffer too small"`, `"nic rec rx err"`, the printf-style DHCP dump) that
are compiled into the image but never actually called from the live code
path — plausible "debug build bloat" that ships in firmware without
being reachable. Telling these apart needs either manually walking the
linear disassembly near each string by hand, or finding the right analyzer
option for this Sleigh module — not done this pass.

## Round 3 — xref gap resolved (tooling), and the firmware's 64 KiB split

This pass set out to (1) trace the app path, (2) resolve the Round 2
string-xref gap, (3) find the NSDP handler, (4) find the httpd/switch-driver
code. Scripts were **disabled** on this bridge
(`run_script_inline` → "Script execution disabled. Set
`GHIDRA_MCP_ALLOW_SCRIPTS=1`"), so everything below is from the read-only
query tools, not a custom analysis script.

### The xref gap is a tooling/analysis limitation, not dead strings

Round 2 left two explanations open (Sleigh doesn't synthesize the ref vs.
the strings are dead debug data). Round 3 lands firmly on **tooling**:

- The **"Scalar Operand References" analyzer is disabled** (confirmed via
  `list_analyzers`: `{"name":"Scalar Operand References","enabled":false}`).
  That is exactly the analyzer that turns an immediate operand like
  `#0x5672` into a data reference, so with it off Ghidra records no data
  xrefs from code regardless of what the code does.
- More decisively, the xref database is sparse **even for code→code
  calls**. `FUN_CODE_1009` decompiles to `main_init(0x9b3e);` — a real
  call — yet `get_xrefs_from(0x1009)` returns *no references* and
  `get_function_callees(main_init)` returns *none*. So `get_xrefs_to` /
  `get_xrefs_from` / the call-graph tools are **unreliable on this program**
  as a whole; their emptiness is not evidence of absence.
- The TCP-state strings (`LISTEN`/`SYN-SENT`/`ESTABLISHED`/…) are a
  textbook state-name lookup table, and the lwps TCP stack that would use it
  is present in this same region (source-path strings
  `..\..\common\src\lwps\tcp.c`, `...\icmp.c`). They are almost certainly
  **live**, just not surfaced by the incomplete analysis.

What I still **could not** do: name the exact instruction that loads the
table. A byte search for a flat `MOV DPTR,#imm16` load (`90 56 72`) found
nothing, and a search for a consecutive Keil-style code-pointer table
(`56 72 56 82 56 92`, the string addresses back-to-back) also found nothing.
That is consistent with the access being *computed* — **and, per the banking
model below, the flat file offset `0x5672` is very likely not the *live
logical address* the code ever loads** (that string sits in a banked region;
the code that uses it addresses it through the bank window at a different
logical address). So the disabled analyzer is real but secondary: the deeper
reason cross-region xrefs don't exist is that the flat 64 KiB map
concatenates banks that never share one live address space.

### The firmware is a BANKED SPI image, not a flat 64 KiB (datasheet, via the hardware agent)

**Key reframing from the RTL8367N-VB-CG datasheet** (relayed by the sibling
hardware-research agent, 2026-11-13): the on-die 8051 has only **16 KB code
memory + 48 KB data RAM**, and uses **code banking**, booting by loading from
the external **SPI flash** (our 683 KB image). So the 64 KiB Ghidra `CODE`
space is the 8051's *logical* address window, and banking swaps different
flash regions into it — **the 683 KB image is not linearly the 64 KiB that
got mapped.** This neatly explains both earlier puzzles:

- The "64 KiB ceiling" is not a generic 8051 flat-code limit (as the
  "code is capped at 64 KiB" section above framed it — treat that section's
  *reasoning* as superseded, though its observation that assets live past
  `0x10000` still holds). It's the logical window size of a banked SoC.
- The unresolved string/code "references" past the code-window size are
  expected: a flat concatenation of banks puts data at file offsets that
  are **not** the live logical addresses any single bank's code sees, so no
  flat xref can exist even in principle.

**What this doesn't yet pin down:** the exact code-window size and split
(16 KB code + 48 KB data *per the datasheet* implies the code window may be
only ~16 KB, not 64 KiB — which would mean much of what the flat import
disassembled above the window is actually a *different bank or data RAM*,
not contiguous code), and the **bank-select mechanism** (an SFR/port/latch
write the boot/dispatch code does before a far call or table access). I did
not locate the bank-select write this pass — with the xref/call database
broken (above) and scripts disabled, hunting one SFR write by hand wasn't
tractable in budget. That is the first task for Round 4.

### Strings/constants present vs. absent in the mapped window (byte-search-backed)

Byte/string searches are reliable for *presence*, and they draw a clear line
(read now through the banking lens — "mapped window" = whatever bank(s) the
flat first-64 KiB import happens to show):

- **In the mapped first 64 KiB (bank 0):** boot/common 8051 code; the
  low-level network stack (`lwps` ICMP/TCP, the TCP state table ~`0x5672`,
  DHCP header-dump debug ~`0xf0eb`); VLAN/IGMP code — the **only** string
  Ghidra has *defined* in the whole mapped region is `_igmpVlan %u` at
  `CODE:0xfdcf`; the `RTL8367N`/`RTL8367B` version strings (~`0x55e2`); and,
  right after them (~`0x5600`), a tagged binary table (`41 58 8C`, `41 58
  8D`, `44 58 …`, `46 55 …` = "AX"/"DX"/"FU" tags + values) that looks like
  **switch-chip register-init data**, not code or text.
- **Absent from the mapped 64 KiB:** the literal `NSDP` signature
  (`4E 53 44 50`), the UDP port constants (`63321`–`63324` =
  `F7 59`…`F7 5C`, searched both as given), and **all** of the httpd / HTML /
  `login` / web-UI strings that the earlier full-image `fw_inspect`/binwalk
  pass found at file offsets past `0x10000`.

So the **NSDP packet parser and the web-UI/httpd handlers are not in the
mapped bank** — they live in the region past `0x10000` that the raw 8051
import does not map (the data/resource region, and/or additional
bank-switched code; see `FIRMWARE-FORMAT.md`). The absent `NSDP` literal also
hints the signature may be matched **byte-by-byte** (`CJNE` against
`'N','S','D','P'`) rather than stored as a contiguous string. Either way,
tasks 3 and 4 (NSDP handler, httpd handler) **cannot be done against the
current single-bank mapping** — they need the >64 KiB region mapped as 8051
overlay bank(s) first.

### App-path trace (task 1): blocked by the same incompleteness

With the call-graph/xref tools returning empty on a known-good call, walking
the app from `main_init` isn't possible this pass. The reset chain
(`0x0000 LJMP 0x1016` → delay `DJNZ` loops → `LJMP 0x1190`) and
`FUN_CODE_1009 → main_init(0x9b3e)` are the only concrete links; `0x9b3e` is
the argument main_init is handed, a reasonable next thing to examine once
analysis is complete.

### Recommended setup for a Round 4 that can actually get there

Order matters — get the memory model right *first*, or every later step
inherits the flat-mapping error:

1. **Re-import with the banked memory model**, not a flat 64 KiB blob. Using
   the datasheet's 16 KB-code / 48 KB-data split, define the common/low code
   region and model the banked window as Ghidra **overlay blocks**, mapping
   each flash bank from its real file offset to the shared logical window.
   The bank size and window base come from the datasheet; the bank *count*
   is `683 KB / bank_size`.
2. **Find the bank-select write.** Look for an SFR/port/latch write
   (`MOV <sfr>,#n` or `MOVX @DPTR` to a control register) that the dispatch
   code performs just before a far call/jump or a cross-bank table access.
   That identifies which SFR selects banks and lets each overlay be tied to
   a bank index.
3. Enable the **Scalar Operand References** analyzer, then `reanalyze` —
   only meaningful *after* the banks are mapped, so operands resolve to live
   logical addresses.
4. If possible, run the bridge with `GHIDRA_MCP_ALLOW_SCRIPTS=1` so a script
   can rebuild references and scan operands/`MOVX` (external-register)
   accesses directly — `MOVX @DPTR` sites are the likely RTL8367N register
   interface and the fast path to the switch driver.

Only once 1–2 are done can the NSDP parser and httpd handler (which live in
banks the flat import didn't show) actually be reached.

## Next steps (not done this pass)

- Trace from `CODE:0x1190` onward to find the real application entry point
  and the NSDP-handling / httpd-handling routines (would corroborate
  `docs/NSDP-PROTOCOL.md` and `docs/WEBUI-AUTH.md` against actual code) —
  **blocked** until Round 4's setup (overlay banks + refs) is in place.
- Resolve why string xrefs aren't resolving (round 2, above) — check this
  8051 Sleigh module's analyzer options for a constant-reference/DPTR pass,
  or manually walk the disassembly near `CODE:55e2` and `CODE:5672` by hand
  to find (or rule out) their real callers.
- Cross-reference the `RTL8367N`/`RTL8367B` string locations found earlier
  with their callers, to find the switch-register-access driver code —
  blocked on the xref issue above.
- Decide whether the firmware's `0x08`/`0x0C` header fields (still
  unidentified per `FIRMWARE-FORMAT.md`) are validated by a bootloader —
  would need the (not publicly distributed) bootloader image to check.
- Sanity-check how much of the 347-function linear-sweep corpus is real
  code vs. disassembler noise over embedded data (expected, since the sweep
  was byte-linear, not flow-accurate).

## Round 4 — attempt, and the two concrete blockers

Retried the deeper trace with the banking model in hand. Confirmed the
blocker firsthand rather than getting past it, and it is environmental, not
analytical:

- **Only the first 64 KiB is in Ghidra.** `list_open_programs` reports
  `memory_size` 66176 bytes for a 682,856-byte payload. The banked code
  where the NSDP parser and httpd live (strings absent from this window per
  round 3) is **not imported at all** — there is nothing to decompile yet.
- **The flat 64 KiB view is unreliable past the common boot code.** The
  reset target disassembles to `CODE:1016: DJNZ R5,0x101c` (R5 uninitialized
  — nonsensical as a first instruction), and `FUN_CODE_1009` "calls"
  `main_init(0x9b3e)` where `main_init` (`CODE:1190`) is a 2-byte `MOV R3,A;
  RET` stub. These are the decompiler misreading banked/data bytes as code —
  exactly the symptom banking predicts.

What actually unblocks Round 4 (both need setup this session can't do from
the MCP side):

1. **Enable scripts on the ghidra-mcp bridge** (`GHIDRA_MCP_ALLOW_SCRIPTS`
   is unset, so `run_script_inline`/`run_ghidra_script` are refused). With
   scripts, the bank-select SFR can be found programmatically and per-bank
   overlays scripted.
2. **Re-import the full 682 KB image with per-bank overlay blocks** at the
   banked window, instead of the first-64 KiB flat load. This needs the bank
   window size + the bank-select mechanism, which lives in the common boot
   code and is the first thing to recover once (1) is available.

Until then, the switch-register driver, NSDP handler, and httpd handler
cannot be reached — not a dead end, but blocked on bridge setup.

## Round 5 — scripts enabled; vector table + bank-loader candidate

Blocker (1) is now cleared. `GHIDRA_MCP_ALLOW_SCRIPTS` turned out to be
discarded by Ghidra's own launcher: `support\launch.bat` starts the JVM with
**`start /I`**, which forces the *original* environment cmd.exe was created
with and drops anything `set` inside the batch. The variable therefore has to
be in the environment of the process that **launches** Ghidra (persist it with
`setx`, or export it in the launching shell), not set inside `ghidraRun.bat`.
With it exported in the launcher's environment, `run_script_inline` /
`run_ghidra_script` work (`System.getenv("GHIDRA_MCP_ALLOW_SCRIPTS")` → `1`),
and `GHIDRA_MCP_FILE_ROOT` is unset (no import path restriction).

First scripted findings against the first-64 KiB image:

- **Interrupt vector table (anchored, reliable).** `RESET @0x0000 → LJMP
  0x1016`; `IE0 @0x0003 → LJMP 0x1009`; `TF0 @0x000b → LJMP 0x2ec9`; `IE1
  @0x0013 → LJMP 0x30f7`; `int10 @0x0053 → LJMP 0x0408`. The other vector
  slots are not `LJMP` — the firmware uses reset + a few interrupts and packs
  code/data over the unused vector space.
- **Bank/overlay loader candidate at `CODE:0x119c`.** A tight
  `MOVX @DPTR,A; INC DPTR; DJNZ R7,…; DJNZ R6,…` block-copy loop — the shape
  of a routine that copies a region (a bank) into external/code memory. The
  dispatcher stubs around `0x1190`/`0x119c` are the targets of a table of
  `{2-byte key, LJMP 0x1190}` entries packed from ~`0x1010` onward, i.e. a
  banked-call / overlay dispatch table rather than real inline code (which is
  why a flat disassembly there looked like nonsense).

Still open (the substantial part): recover the exact bank-select write and
the bank window size from the loader at `0x119c`/dispatcher, then script the
per-bank overlay import so the banked NSDP/httpd code becomes analyzable. This
is real reverse-engineering effort, not a quick step — the loader's addressing
(MOVX target = which register/SFR latches the bank) has to be read out
carefully, and the 682 KB flash image's bank layout confirmed against it.

## Round 6 — bank layout confirmed (32 KiB banks), and NSDP is gone

Rather than reverse the hardware bank-select first, confirmed the bank
**layout** empirically by carving and re-importing. Result: the image uses the
classic 8051 scheme — **lower 32 KiB common, upper 32 KiB banked**:

- common = file `0x00000`-`0x07fff` → logical `0x0000`-`0x7fff` (always mapped),
- bank *N* = file `0x08000 + N*0x8000` (size `0x8000`) → logical `0x8000`-`0xffff`.

Method (reproducible): build a synthetic 64 KiB image = `common ++ bank_N` and
import it as `8051:BE:16:default` at base `0x0000`; logical addresses then
resolve correctly for that bank's code and data.

**Evidence it's right (bank 2 = file `0x18000`-`0x1ffff`):** the web strings
land exactly where the model predicts — `login.cgi` at logical `0xc9bd`,
`httpd.c` at `0xd2e0` — and, decisively, **common code references them at those
logical addresses**: the C-startup sequence at `CODE:0x0301`
(`MOV DPTR,#0xc8cb; LJMP 0x1100`, where `0x1100` is a `MOV A,@R1; MOVX @DPTR,A;
INC DPTR; DJNZ R7` copy loop) copies bank-2 initialized data into RAM. 2626
`MOV DPTR,#imm16` loads total; 52 target the bank-2 string region. The copy
helpers at `0x1100`/`0x119c` are C-runtime init, not the HW bank-select.

**NSDP is removed in 1.6.0.25.** A scan of the whole 682 KiB image finds the
ASCII signature `"NSDP"` **0 times** — direct confirmation of NETGEAR's
"NSDP discovery removed on firmware 1.6.0.15+" note (this project's own
hardware-independent corroboration). The NSDP UDP port constants
(`0xf759`-`0xf75c` = 63321-63324) still appear around file `0x57000`-`0x6a000`,
likely residual or management-mode strings, not an active discovery responder.

**Map of the flash (file offsets):** web-management **code** strings
(`httpd`, `login.cgi`, `switch_info`) cluster at `0x1c000`-`0x1d500` (bank 2);
web **assets** (HTML pages, PNGs, gzip'd JS/CSS) run from `~0x57000` onward.

Remaining (deeper still): trace the actual httpd request dispatcher / CGI
handler code — identify which bank holds the handler bodies and the
common-side bank-switch call helper, then follow a request end to end. The
bank-carve method above makes any single bank analyzable; wiring the
cross-bank call graph together is the next large piece.

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
