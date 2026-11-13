# DMCA & GitHub — project guide

**Not legal advice.** Before sending or responding to any DMCA notice, talk to
a lawyer. False statements under penalty of perjury are a federal crime.

This file is for maintainers and contributors. It covers (1) how this project
is designed to stay out of infringement territory, and (2) what GitHub's DMCA
process actually requires if a notice arrives.

## 1. Preventive posture (what we ship)

Keep the repository aligned with [`LEGAL.md`](LEGAL.md) and `.gitignore`:

| Do ship | Do not ship |
| --- | --- |
| Original Python probe/discovery tooling | NETGEAR firmware `.zip`/binary images |
| Factual protocol notes (NSDP header/TLV layout) | NETGEAR configuration-utility installers |
| MIT-licensed tests & docs we wrote | Manuals, PDFs, branded assets |
| Links and citations to public vendor pages and prior research | Decompiled vendor source dumps |
| Hashes and source URLs for vendor downloads | Packet captures with copyrighted payloads |

If a takedown targets **redistributed firmware or copied vendor code**, the
right fix is usually to **remove that material**, not to fight over it. This
project's design goal is that such material never lands in git history.

If a takedown targets **independently written interoperability tooling** or
**uncopyrightable interface facts**, maintainers may evaluate a counter notice
with counsel.

## 2. What a rights-holder's GitHub takedown notice must include

Summarized from GitHub's
[Guide to Submitting a DMCA Takedown Notice](https://docs.github.com/en/site-policy/content-removal-policies/guide-to-submitting-a-dmca-takedown-notice):

1. Statement that they have read and understand GitHub's DMCA guide.
2. Identification of the **copyrighted work** allegedly infringed.
3. Identification of the **allegedly infringing material** (URLs; specific
   files/lines if not the whole repo).
4. What the user must do to **remedy** the claim.
5. Contact information for the complainant.
6. Contact information for the alleged infringer (if known).
7. Good-faith belief statement; accuracy / perjury statement; signature.

For **anti-circumvention** (17 U.S.C. § 1201) claims, GitHub additionally
expects detail on the technical protection measure and how the project
allegedly circumvents it. See GitHub's
[DMCA Takedown Policy](https://docs.github.com/en/site-policy/content-removal-policies/dmca-takedown-policy).

GitHub publishes processed notices (redacted) at
https://github.com/github/dmca .

## 3. What a GitHub **counter notice** must include

Summarized from GitHub's
[Guide to Submitting a DMCA Counter Notice](https://docs.github.com/en/site-policy/content-removal-policies/guide-to-submitting-a-dmca-counter-notice):

1. Statement: *"I have read and understand GitHub's Guide to Filing a DMCA
   Counter Notice."*
2. Identification of the **disabled content** and the **URL** where it
   appeared.
3. Your **contact information** (email, name, phone, physical address).
4. Perjury statement of **good-faith belief** that removal was due to mistake
   or misidentification (you may explain why — e.g. fair use,
   interoperability under § 1201(f), security research under § 1201(j),
   original authorship, no redistributed firmware in the repo).
5. Consent to **federal court jurisdiction** (your district if in the U.S.,
   otherwise N.D. Cal.) and acceptance of **service of process** from the
   complainant.
6. Physical or electronic **signature**.

Submit via GitHub's copyright claims form or `copyright@github.com`. After a
valid counter notice, GitHub typically waits **10-14 days** then restores
content unless the complainant files suit. **You may get sued.** Counter
notices are legal statements and are published (PII redacted).

## 4. Suggested talking points for counsel (this project)

If evaluating a response, facts typically relevant here include:

- Repository contains **original** probe/documentation code under MIT, not a
  copy of any NETGEAR utility or firmware.
- **No firmware images or vendor installers** are hosted in the repository;
  `downloads/` is `.gitignore`d except for provenance notes and hashes.
- The discovery probe speaks the device's **broadcast NSDP query** the same
  way NETGEAR's own Discovery Tool and third-party tools (`ProSafeLinux`,
  `ngadmin`) do, built from independently written code plus well-cited prior
  public research into the protocol.
- Intended legal theories (depending on facts): original authorship; lack of
  substantial similarity to protected expression; uncopyrightable interface
  facts; fair use (§ 107); interoperability exception (§ 1201(f)); good-faith
  security-testing exception (§ 1201(j)) where a circumvention claim is
  raised.

Do **not** file a counter notice casually. Investigate first; get counsel.

## 5. External resources

- EFF — [Reverse Engineering FAQ](https://www.eff.org/issues/coders/reverse-engineering-faq)
- GitHub — [DMCA Takedown Policy](https://docs.github.com/en/site-policy/content-removal-policies/dmca-takedown-policy)
- U.S. Copyright Office — DMCA overview
- Software Freedom Law Center — open-source legal help
