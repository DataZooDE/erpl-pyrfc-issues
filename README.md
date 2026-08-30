# erpl-pyrfc — a drop-in PyRFC replacement for SAP RFC in Python, with no SAP NW RFC SDK

[![PyPI](https://img.shields.io/pypi/v/erpl-pyrfc)](https://pypi.org/project/erpl-pyrfc/)
[![Python](https://img.shields.io/pypi/pyversions/erpl-pyrfc)](https://pypi.org/project/erpl-pyrfc/)
[![Wheels](https://img.shields.io/badge/wheels-linux%20%C2%B7%20macOS%20%C2%B7%20windows%20%C2%B7%20musl-informational)](https://pypi.org/project/erpl-pyrfc/#files)
[![License](https://img.shields.io/badge/license-BUSL--1.1-blue)](https://spdx.org/licenses/BUSL-1.1.html)

**This repository is the public issue tracker for [`erpl-pyrfc`](https://pypi.org/project/erpl-pyrfc/).** The source is not
public; the bug tracker is. [Open an issue →](../../issues/new/choose)

```bash
pip install erpl-pyrfc
```

```python
import pyrfc  # the same import, unchanged

conn = pyrfc.Connection(ashost="…", sysnr="00", client="001", user="…", passwd="…")
print(conn.call("STFC_CONNECTION", REQUTEXT="hello")["ECHOTEXT"])
```

---

## Why this exists

SAP archived [PyRFC](https://github.com/SAP-archive/PyRFC) in 2024. The wheels were yanked, the repository is read-only, and
the last release does not build against current Python. Anyone still calling SAP RFC from Python was left with three bad
options: pin an old Python, build a C extension against the **SAP NW RFC SDK** by hand, or rewrite.

`erpl-pyrfc` is the fourth option. It claims the `pyrfc` import namespace and implements the RFC protocol in **pure Rust**,
so the SDK is not needed at all.

| | SAP PyRFC 3.3.1 | erpl-pyrfc |
|---|---|---|
| SAP NW RFC SDK required | yes — S-user download, manual install | **no** |
| ICU 50 shared libraries | yes | **no** |
| Install | build from source | `pip install`, prebuilt wheels |
| Python | ≤ 3.12 in practice | **3.9 – 3.13+** |
| Platforms | whatever you build | manylinux · musllinux · macOS (x86-64, arm64) · Windows |
| Maintained | archived 2024 | actively developed |
| `import pyrfc` | ✔ | ✔ same namespace |

**No SAP S-user account, no `nwrfcsdk` tarball, no `LD_LIBRARY_PATH`, no ICU.** One wheel, one `pip install`.

## What works

Everything the archived library did, verified by running the same script under both and diffing the output:

- **Client calls** — `call()`, typed and untyped, structures, tables, deep and nested structures
- **All ABAP scalar types** — including `DECFLOAT16`/`34`, `INT8`, `UTCLONG`, packed decimals at full precision
- **Server mode** — register as an RFC destination and receive calls from ABAP
- **tRFC and qRFC** — transactional and queued units of work
- **SNC** — Secure Network Communications, `snc_qop` 1–9
- **`Throughput`** — the same seven `stats` keys, attach/detach, monitors summing several connections
- **basXML** — SAP's binary serialization, chosen per function module by the server, handled transparently
- **Connection pooling**, cancellation, error taxonomy and codes

Two things go **beyond** PyRFC:

- **wsRFC** — RFC over a WebSocket with X.509 client-certificate sign-on
- **`mshost_override`** — for a message server that reports an address only resolvable inside its own network

Deliberately absent: **bgRFC background units**. Everything else PyRFC exposed is here, including the module-level surface
(`cancel_connection`, `RfcFieldType`, `RfcParameterDirection`, `RCStatus`, `UnitState`, `UnitCallType`,
`TypeDescription`, `FunctionDescription`, `ConnectionParameters`, `language_iso_to_sap`, …).

## How it is built

The protocol was reverse-engineered **clean-room**, from packet captures of SAP's own library talking to a real ABAP system
— never by reading another implementation's source. Every rule in the specification is evidenced by a capture, and every
capture is committed next to the rule it proves.

Read the story:

- **[A drop-in replacement for the archived PyRFC](https://erpl.io/blog/drop-in-replacement-for-archived-pyrfc/)** — what
  broke, and the migration
- **[The SAP RFC protocol, byte by byte](https://erpl.io/blog/sap-rfc-protocol-byte-by-byte/)** — NI framing, APPC, the
  RFC_PRO field sequence
- **[SAP RFC over WebSockets](https://erpl.io/blog/sap-rfc-over-websockets/)** — wsRFC and certificate sign-on
- **[Faster SAP ingest without the SDK](https://erpl.io/blog/erpl-rev-faster-ingest-no-sdk/)**
- **[10M BSEG rows a minute](https://erpl.io/blog/erpl-rev-10m-bseg-rows-a-minute/)**

## Reporting a bug

Open an issue here. What helps most:

1. **The function module and its interface** — `RFC_GET_FUNCTION_INTERFACE` output, or the SE37 screenshot
2. **A minimal script** that reproduces it
3. **Versions** — `pyrfc.__version__`, Python, OS, and the SAP kernel release
4. **What SAP PyRFC did**, if you can still run it — a behavioural difference is the most actionable report there is

Please do not paste credentials, hostnames or business data. A redacted trace is worth more than none.

## Other SAP tooling from DataZoo

`erpl-pyrfc` is one piece of a wider set of SAP integration tools:

| Project | What it does |
|---|---|
| **[erpl](https://github.com/DataZooDE/erpl)** | DuckDB extension connecting SAP RFC, ODP and BW to your analytics stack |
| **[erpl-web](https://github.com/DataZooDE/erpl-web)** | DuckDB extension for OData, GraphQL and REST — SAP ERP, Ariba, C4C, Dynamics |
| **[erpl-rev](https://github.com/DataZooDE/erpl-rev)** | SAP RFC server bridging ABAP into DuckDB — the inverse direction |
| **[erpl-adt](https://github.com/DataZooDE/erpl-adt)** | CLI and MCP server for the SAP ADT REST API — no Eclipse, no JVM |
| **[erpl-tunnel](https://github.com/DataZooDE/erpl-tunnel)** | Tunnel SAP RFC and HTTP over SSH, Tailscale or NetBird |
| **[flapi](https://github.com/DataZooDE/flapi)** | Build APIs on DuckDB for data apps and AI agents |

More at **[erpl.io](https://erpl.io)**.

## Let's talk

Building on SAP RFC, migrating off PyRFC, or solving this differently? I would genuinely like to compare notes —
especially on how people test SAP integrations without a spare system to break.

**[Connect with me on LinkedIn →](https://www.linkedin.com/in/joachim-rosskopf/)**

---

<sub>Keywords: PyRFC alternative · PyRFC replacement · PyRFC archived · SAP RFC Python · SAP RFC without NW RFC SDK ·
sapnwrfc · nwrfcsdk · pyrfc Python 3.13 · SAP RFC client library · ABAP RFC from Python · SAP NetWeaver RFC ·
tRFC qRFC Python · SNC RFC Python · wsRFC · SAP integration Python · pure Rust SAP RFC</sub>
