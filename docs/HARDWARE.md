# Hardware — what the GS105Ev2 silicon is, and how to get at it

Groundwork for a future physical teardown. Nothing here was observed on a
physical board: the project has not opened the case. Every claim is labelled
**[sourced]** (with a link), **[firmware]** (established by this project's own
firmware analysis), or **[inferred]** (reasoned from the class of device).
Treat [inferred] items as a checklist of things to verify with a multimeter and
a camera, not as findings.

The chipset-confirmation story (the `RTL8367N` string in the firmware, the
5-port distributor description) is in [`research.md`](research.md) and
[`FIRMWARE-FORMAT.md`](FIRMWARE-FORMAT.md); it is not repeated here. The
Ghidra disassembly that identified the 8051 core is in
[`GHIDRA-NOTES.md`](GHIDRA-NOTES.md).

## Primary source and its limits

Most of the chip detail below comes from one document: Realtek's
**RTL8367N-VB-CG datasheet, "Rev. Pre-0.9", 20 February 2014**, marked
"CONFIDENTIAL: Development Partners Only", mirrored on a distributor site
([chipdip.ru copy](https://static.chipdip.ru/lib/629/DOC041629854.pdf), 61
pages; text extracted locally with `pdftotext`). Caveats:

- It is an early draft, and it is for the **-VB** revision. The firmware says
  `RTL8367N`; whether the GS105Ev2 carries a -VB part is **[inferred]**.
  Distributor listings such as
  [LCSC](https://lcsc.com/product-detail/Ethernet-ICs_Realtek-Semicon-RTL8367N-VB-CG_C2760851.html)
  only show the -VB-CG variant, so it is the most likely one.
- It is a leaked/non-public document. This repository does not redistribute it
  (see [`../LEGAL.md`](../LEGAL.md)); only short facts are summarized here.
- Section 9.17 (embedded 8051) is only a few lines long, and the memory
  figures were not cross-checked against a second source.

## The 8051 is on-die — there is no separate management MCU

**[sourced]** The datasheet lists an "Integrated 8051 microprocessor" in the
feature list and describes it in section 9.17 ("Embedded 8051"). Per that
section, the 8051:

- can access all of the switch's registers over an internal bus;
- reaches the switch core through the on-chip NIC, so it can send and receive
  Ethernet frames itself — this is how a management stack (here, the "lwps"
  TCP/IP code and httpd found in the firmware) gets onto the wire without a
  separate MAC;
- has 256 bytes of fast internal RAM, **16 KB of on-chip code memory**, **48 KB
  of on-chip data memory**, a 12 KB NIC buffer, and supports **code banking**.

This resolves the open question in the task: the "management CPU" the firmware
targets is the 8051 inside the RTL8367N, not a second chip. The earlier
firmware conclusion (8051-family, reset vector `LJMP 0x1016`) is consistent
with it.

**What this changes about the firmware picture [inferred]:** 16 KB of on-chip
code memory is much smaller than the ~64 KiB code space Ghidra mapped, and far
smaller than the 683 KB image. The reconciliation that fits the datasheet is
that the on-chip code memory is an *instruction memory that gets loaded at
reset* (see the strap table below), and that the 8051 runs a banked or
overlaid program out of it. How banking maps the image's 64 KiB "code" region
and the data region beyond it onto 16 KB of RAM is not documented in the
sources read; it is a real open question for the Ghidra work (a bank-switch
register write in the code would be the thing to look for). The 683 KB image
is evidently stored in the external flash described below, not on-die.

## Other chip facts from the datasheet

| Item | Value | Status |
| --- | --- | --- |
| Package | QFN-88, 10 x 10 mm, exposed pad | [sourced] datasheet table 29; [LCSC](https://lcsc.com/product-detail/Ethernet-ICs_Realtek-Semicon-RTL8367N-VB-CG_C2760851.html) says MQFN-88-EP |
| PHYs | Five 10/100/1000BASE-T PHYs **integrated** on the same die; no external PHY chips | [sourced] |
| Clock | 25 MHz crystal (+/-50 ppm) or a 3.3 V oscillator on XTALI | [sourced] |
| Supplies | 3.3 V (DVDDIO, AVDDH) and 1.1 V (DVDDL, AVDDL, PLLVDDL) | [sourced] table 28 |
| Ambient temperature | 0 to 70 C | [sourced] |
| Packet buffering | "SRAM for packet buffering" on-die; size not stated in the text read | [sourced] |
| MAC table | **2K-entry**, 4-way hash | [sourced] |
| Jumbo frames | 9216 bytes | [sourced] |
| Other | 802.1Q/802.1ad VLAN, 802.1X, IGMP/MLD snooping, 802.1w/s, EEE, Green Ethernet, RTCT cable test, two LAG groups | [sourced] |

**Discrepancy to keep visible:** [`research.md`](research.md) records a retailer
spec for the GS105Ev2 of an 8K MAC table and 2 MB packet buffer. This draft
datasheet says 2K entries. The two are not reconciled: the retailer figure may
be NETGEAR marketing, a different chip revision, or a count that includes
something else; the datasheet is a Pre-0.9 draft. Neither is verified.

## Management and boot interfaces

All of the following are **[sourced]** from the datasheet's pin descriptions
(sections 7.3-7.4, 10) unless marked otherwise.

- **"EEPROM SMI" bus (SCK pin 81 / SDA pin 82).** A two-wire, I2C-like serial
  bus, not standard IEEE MDIO. At power-up the chip is the *host* on this bus
  and reads a 24Cxx-style EEPROM (up to 256 Kbit; the `EEPROM_MOD` strap picks
  between 24C02-24C16 and 24C32-24C256 addressing). After autoload the chip
  becomes a *slave* on the same two wires and an external CPU can read and write
  its registers (device address `0x4`). The same pins can alternatively be
  strapped (`SMI_SEL`) to act as an MII-management (MDC/MDIO) slave.
- **Linux/OpenWrt view of the same thing.** The mainline
  [`rtl8365mb` DSA driver](https://kernelsources.org/source/xref/linux/drivers/net/dsa/realtek/rtl8365mb_main.c)
  and its `realtek-smi` front-end drive this bus either bit-banged ("SMI",
  which only borrows the MDC/MDIO signal lines and is not MDIO) or over real
  MDIO. Its header comment says the chip reads initial register values from an
  I2C EEPROM at reset and that the EEPROM may be omitted. A
  [Turing Pi forum post](https://forum.turingpi.com/t/13131301/on-the-turing-pi-there-is-according-to-the-docs-a-switch-rea)
  notes the consequence: an EEPROM on the same wires is cut off from the host
  if SMI is bit-banged. Those drivers target the RTL8365MB/RTL8367 family
  generically; they are evidence for the bus protocol and register model, not
  proof about this specific board.
- **SPI flash interface.** Pins `SPIF_CLK` (56), `SPIF_D0` (57), `SPIF_D1`
  (58), `SPIF_CS` (59) form a SPI master port ("Flash Interface"), enabled by
  the `EN_SPIF` strap (pin 68, pulled up = enabled).
- **UART.** `UART_RX` (54) and `UART_TX` (55) exist as multiplexed GPIO pins,
  so the chip has a UART in silicon. Whether the GS105Ev2 firmware or board
  uses it is unknown (see teardown plan).
- **JTAG.** No JTAG pin appears in the pin-name search of the datasheet text.
  The only test pin documented is `RTT1` ("Reserved for Internal Use. Must be
  left floating"). Do not expect a documented JTAG port.

### The boot-source strap table

The three straps `DISAUTOLOAD`, `DIS_8051` and `EN_SPIF` (sampled at power-on
or reset) decide what is loaded where **[sourced]**, datasheet table 5:

| DISAUTOLOAD | DIS_8051 | EN_SPIF | Loaded from -> to |
| --- | --- | --- | --- |
| 0 | 0 | 0 | EEPROM -> embedded 8051 instruction memory |
| 0 | 0 | 1 | **SPI flash -> embedded 8051 instruction memory** |
| 0 | 1 | 0 | EEPROM -> switch registers only (8051 off) |
| 1 | any | any | nothing loaded |

(The extracted table's row alignment is imperfect; the second row's
"FLASH -> 8051 instruction memory" is the one that matters here, and the
datasheet text for `DISAUTOLOAD` independently says that with `DIS_8051 = 0`
and `DISAUTOLOAD = 0` the EEPROM/flash data is loaded into 8051 instruction
memory.) All three pins have internal pull-ups and must be left floating or
set with 4.7 k resistors, so their board state is directly readable.

## Where the 683 KB firmware lives

**[inferred], with one weak external data point.**

The firmware is far too large for EEPROM-class parts (the datasheet's EEPROM
limit is 32 KB, and 24Cxx parts top out at 256 Kbit) and far too large for the
16 KB of on-chip code memory. The only boot source in the datasheet that fits
is the **SPI flash on the SPIF pins, loaded into 8051 instruction memory**
(`EN_SPIF = 1`). So a GS105Ev2 board should carry a small SPI NOR flash
wired to pins 56-59 and the `EN_SPIF` strap pulled up.

Part size: a 683 KB image exceeds a 4 Mbit (512 KB) part, so the flash needs
at least 8 Mbit (1 MB); 16 Mbit (2 MB) is a common cheap choice. A
[NETGEAR community thread about a GS105E v2 bricked by a firmware update](https://community.netgear.com/discussions/business-managed-switches/netgear-prosafe-gs105e-v2-managed-switch-bricked-after-firmware-update/2306512/replies/2306954)
was surfaced by a search as saying the user could program the board's
**Winbond 25Q16DVSIG** (a 16 Mbit SOIC-8 SPI NOR). That page returned HTTP 403
when fetched directly, so the part number comes from a search-result summary
only and has not been checked against the post itself. Treat it as a plausible
lead, not a confirmed BOM entry. Note also that the post concerns a flash
that must be re-programmed, i.e. the flash holds the firmware image, which
agrees with the reasoning above.

Whether the flash holds the 20-byte-header image
([`FIRMWARE-FORMAT.md`](FIRMWARE-FORMAT.md)) byte-for-byte, or the vendor
loader unpacks the download into a different on-flash layout, is unknown. A
dump would settle it. The web UI strings describe a separate bootloader
("`GS105Ev2_loader_*`"), so the flash probably also contains a loader region
that no public download supplies.

What an EEPROM might hold on this board is separate: a small 24Cxx part, if
fitted, would carry register initialization or (with `DIS_8051 = 0`,
`EN_SPIF = 0`) 8051 code. Which of the two applies is again a strap-pin
observation on the real board. A configuration EEPROM or the flash also
likely stores settings (password, VLANs); that is **[inferred]**.

## Likely board contents

For a 5-port gigabit smart switch built around a one-chip switch+PHY, expect
the following. All **[inferred]** unless a source is given.

- **RTL8367N** (QFN-88) — switch, PHYs, 8051 management core, SRAM.
- **25 MHz crystal** near the switch (the D-Link teardown below noted it can
  sit surprisingly far away).
- **SPI NOR flash**, SOIC-8 or similar, 1-2 MB, near the switch's SPIF pins
  (candidate: Winbond 25Q16, unconfirmed as above).
- **Possibly a 24Cxx EEPROM**, SOIC-8 / TSSOP-8, sharing the SCK/SDA pins.
- **Five RJ45 jacks with integrated magnetics** (a single-chip switch needs
  magnetics on each port, but not separate PHYs).
- **Power:** the spec is a 12 V / 1 A-class DC input (per the task brief). The
  chip needs 3.3 V and 1.1 V, so expect one or two small DC-DC buck converters
  (and/or an LDO) from the input. Sibling hobbyist teardowns of RTL8367
  switches show exactly this pattern: the
  [Inside Gadgets teardown of a D-Link DGS-1005D](https://www.insidegadgets.com/?p=9430)
  reports an RTL8367, an 8-pin EEPROM-like part, a 25 MHz crystal and two DC-DC
  converters including a Richtek RT8282A (from a page summary; the author
  himself did not confirm the 8-pin part's function).
- **LEDs** driven from the per-port `LED0`/`LED1` pins.
- Status/jumper pads for strapping, and unpopulated headers, are common but
  unpredictable.

Related RTL8367 devices with public hobbyist work, for reference rather than
as evidence about the GS105Ev2:

- [RTL8XXX-Switch](https://github.com/tomazas/RTL8XXX-Switch): a TP-Link
  TL-SG105 with an RTL8367 and an **M24C08 EEPROM** read/written with a Bus
  Pirate over SDA/SCL. It documents the register-initialization format
  (first two bytes give an end address, then 16-bit register/value pairs), which
  shows that an EEPROM can be pure register configuration. That is the
  `DIS_8051 = 1` case, a different boot mode from what a firmware-image
  switch like the GS105Ev2 needs.
- Hackaday logs on [NETGEAR GS208 and Cisco SG110D-08](https://hackaday.io/project/170181/log/175870-04112020)
  already cited in [`research.md`](research.md): RTL8370N-class boards.

No FCC internal photos exist for this model (see [`research.md`](research.md)):
the device is a radio-less Part 15 Subpart B unintentional radiator and likely
relies on SDoC, so there is no grant to publish.

## Realistic teardown and debug plan

Ordered cheapest and least invasive first. Nothing here has been attempted.

1. **Open and photograph.** Per a
   [blog on the GS105E](https://www-yhi-moe.pages.dev/blog/en/netgear-prosafe-gs105e-ethernet-switch-review)
   found in search (not read in depth), two screws on the underside release the
   cover. Photograph both sides of the board; record the markings on every
   QFN/SOIC part, the crystal, and the DC input. The RTL8367N top marking
   should show `RTL8367N` plus a version letter; check for -VB / -VC.
2. **Identify the flash and any EEPROM.** Read the 8-pin SOIC markings. A
   Winbond 25Qxx means SPI NOR; an Atmel/ST `24Cxx` means I2C EEPROM. Confirm
   against the switch's pins 56-59 (SPIF) and 81/82 (SCK/SDA) with a continuity
   check, and read the `EN_SPIF` / `DIS_8051` / `DISAUTOLOAD` strap resistors
   (pins 68-70) to determine the boot source from the table above.
3. **Dump the SPI flash.** Required: an SPI programmer
   (CH341A, or better a Raspberry Pi / FT232H running `flashrom`), a SOIC-8
   test clip (Pomona 5250-style) and a 3.3 V logic level. Risk: in-circuit reads
   can fail because the switch also drives the SPI bus, or because the board
   backfeeds power through the clip. Mitigation: hold the switch in reset (pull
   `nRESET`, pin 80, low) so the master tristates, power the flash from the
   programmer only, and read twice, comparing hashes. Dump before any other
   probing. If an in-circuit read is unreliable, hot-air or desolder the flash.
   (Reasoning here is standard in-circuit-flash practice, not specific to this
   switch.)
4. **Compare the dump to the download.** Check whether the flash contents
   contain the 20-byte-header image unchanged, and look for the loader
   region (the `GS105Ev2_loader_*` string) and any stored configuration
   (the config region should reveal how passwords, VLANs and the "Web browser
   only" management mode are persisted — relevant to
   [`WEBUI-AUTH.md`](WEBUI-AUTH.md) and [`VLAN-PLAN.md`](VLAN-PLAN.md)).
5. **UART.** The chip has `UART_TX`/`UART_RX` pins (54/55), but they are
   multiplexed GPIOs. Look for a 3-4 pad unpopulated header or test pads on
   the traces from those pins, then probe with a 3.3 V USB-serial adapter
   (receive-only first, so as not to fight the chip; the baud rate is unknown,
   115200 is the usual guess). Whether the firmware enables it at all is
   unknown. Consumer builds of this class often leave it silent; a silent
   port is a plausible outcome.
6. **JTAG.** None is documented (see above). A classic 8051 core has no
   standard JTAG, and no JTAG signals appear in the datasheet text read, so
   a hardware debugger should be considered unlikely. Realistic substitutes:
   the SPI flash (read, and re-flash to test modified images), and the I2C-like
   EEPROM SMI slave port, which lets an external host read and write the
   switch's registers (including MIB counters and the lookup table) with just
   two wires, as the Linux driver does.
7. **Using the SMI slave as an analysis tool.** If SCK/SDA are reachable and
   the datasheet's device address `0x4` holds, a host can enumerate registers
   on the live switch. That gives a ground-truth register map to compare with
   the firmware's register writes in Ghidra. Do this with care: writes can
   disrupt a running switch, and the same bus may be in use by the 8051's own
   EEPROM access.

## Open questions

- Exact RTL8367N revision on the board (-VB vs another).
- Which of {SPI flash, EEPROM, both} is populated, and the flash part and size.
- How the 8051's code banking maps the 64 KiB code region and the data region
  beyond it into 16 KB of on-chip code memory plus 48 KB of data memory.
- Whether any UART or debug port is wired out.
- 2K (datasheet) vs 8K (retailer) MAC-table size, and 2 MB packet buffer.

## Sources

- Realtek, [RTL8367N-VB-CG datasheet, Rev. Pre-0.9](https://static.chipdip.ru/lib/629/DOC041629854.pdf) (2014-02-20, confidential draft; basis for pin, strap, 8051, EEPROM and flash claims)
- [LCSC RTL8367N-VB-CG listing](https://lcsc.com/product-detail/Ethernet-ICs_Realtek-Semicon-RTL8367N-VB-CG_C2760851.html); [Octopart](https://octopart.com/part/realtek/RTL8367N-VB-CG)
- Linux [`rtl8365mb` DSA driver](https://kernelsources.org/source/xref/linux/drivers/net/dsa/realtek/rtl8365mb_main.c) and [`realtek-smi`](https://codebrowser.dev/linux/linux/drivers/net/dsa/realtek/realtek-smi.c.html) (bus protocol, EEPROM-at-reset behaviour)
- [Turing Pi forum, SMI vs EEPROM on one bus](https://forum.turingpi.com/t/13131301/on-the-turing-pi-there-is-according-to-the-docs-a-switch-rea)
- [tomazas/RTL8XXX-Switch](https://github.com/tomazas/RTL8XXX-Switch) (RTL8367 EEPROM register format, TL-SG105)
- [Inside Gadgets D-Link DGS-1005D teardown](https://www.insidegadgets.com/?p=9430) (RTL8367 sibling board)
- [NETGEAR community: GS105E v2 bricked after firmware update](https://community.netgear.com/discussions/business-managed-switches/netgear-prosafe-gs105e-v2-managed-switch-bricked-after-firmware-update/2306512/replies/2306954) (flash part mention; unverified, page not fetchable)
- Project docs: [`research.md`](research.md), [`FIRMWARE-FORMAT.md`](FIRMWARE-FORMAT.md), [`GHIDRA-NOTES.md`](GHIDRA-NOTES.md), [`GS105Ev2.md`](GS105Ev2.md), [`NSDP-PROTOCOL.md`](NSDP-PROTOCOL.md)
