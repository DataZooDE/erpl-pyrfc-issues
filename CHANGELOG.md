# Changelog

## 2026.11.19

Release gate run on 2026-11-19 against the a4h ABAP Platform Trial (release
816, kernel 9.16): **537 Rust tests and 263 Python tests passed**, with SNC, wsRFC, the async driver and a
message server live. One Rust test fails and fails identically on the previous `main`:
`live_basxml`'s classic-versus-basXML comparison of `BICS_PROV_GET_INITIAL_STATE`
(rows of 734 bytes over basXML against 736 classic: a padding mismatch in the basXML
path, most likely exposed by the system update, and still open. It can affect a
basXML-enabled module whose table row type has trailing alignment padding). Skipped: the three SAProuter tests (no
router running) and the C++ consumer test. erpl's suite through the C-ABI shim: rfc
34/35 (the nwrfc-only backend file skips).

### Changed

- **ABAP errors are classified the way SAP's PyRFC classifies them.** Measured
  field by field on a4h: every `RFC_RAISE_ERROR` method and message type,
  `STFC_SAPGUI`, and this package's own error tests run under SAP's PyRFC.
  *How* a failure was raised decides the class, not the message type:

  | raised by | exception | `code` |
  |---|---|---|
  | a declared exception | `ABAPApplicationError` | 5 |
  | ABAP `MESSAGE` (any type, E included) | `ABAPRuntimeError` | 4 |
  | a short dump | `ABAPRuntimeError` | 3 |

  **If you catch `ABAPApplicationError` for a `MESSAGE`-raised failure, catch
  `ABAPRuntimeError` instead** — as you would with SAP's PyRFC. A declared
  exception with a type-X message is now `ABAPApplicationError`. A message of a
  type ABAP does not have (`RFC_RAISE_ERROR MESSAGETYPE=0`) is a short dump with
  key `MESSAGE_TYPE_UNKNOWN` and no T100 identity, as in SAP's PyRFC.
  `str(error)` is still rendered differently from SAP's PyRFC; that is unchanged.

### Fixed

- **A short dump was raised as `ABAPApplicationError`** since the core stopped
  reporting the dump's `00`/`341` wrapper as a message. `STFC_SAPGUI` is
  `ABAPRuntimeError`, code 3, key `DYNPRO_SEND_IN_BACKGROUND` again — now with
  no placeholder T100 identity, matching SAP's PyRFC exactly.

- **Any instance number other than 00 was routed to instance 00**
  ([erpl-pyrfc-issues#3](https://github.com/DataZooDE/erpl-pyrfc-issues/issues/3),
  very probably [#1](https://github.com/DataZooDE/erpl-pyrfc-issues/issues/1)).
  The connection handshake announced `localhost` and `sapdp00` whatever
  `ashost` and `sysnr` were given, and the gateway routes to what the client
  announces. Depending on the host, that failed as `partner ... not reached`
  or reached a different instance and was refused logon. The handshake now
  announces the caller's `ashost` and `sapdp<sysnr>`, byte for byte as SAP's
  library does. Every test system so far was instance 00 on one host, where
  the old values happened to be right.
- **A gateway refusal surfaced as `RFC_PRO field at offset 0 is truncated`.**
  The gateway reports an unreachable partner inside the Allocate reply, which
  was not read. It is now raised at `Connection(...)` as `CommunicationError`
  (`RFC_COMMUNICATION_FAILURE`) with the gateway's own text, as SAP's PyRFC
  raises it.
- **A malformed `sysnr` connected to instance 00.** Anything but exactly two
  digits now raises `ExternalRuntimeError` (`RFC_INVALID_PARAMETER`, "Invalid
  SYSNR format") before connecting, as SAP's PyRFC does. That includes `"0"`,
  which SAP's library does not zero-pad.
- The handshake no longer carries the host name, program name and OS user of
  the machine its template was recorded on. It sends the caller's own, as SAP's
  library does, so a gateway log names the real client.

## 2026.9.3

Release gate run on 2026-09-03 against the a4h ABAP Platform Trial (kernel
7.58): **509 Rust tests and 263 Python tests, no failures and no skips**, with SNC, wsRFC, the async driver and a SAProuter all live. erpl's own suites through the C-ABI shim: rfc 31/32 (the
nwrfc-only backend file skips), bics 45/45.

### Fixed

Found by a six-persona review of the released #61 implementation, before any
report from the field:

- **A hostile row width could allocate gigabytes.** The reply's `TableHeader`
  row width is the server's to choose and every row was padded to it; a 4 GiB
  width over a 2-byte row allocated 4 GiB per row. The width is now capped at
  the layouts' limit before any row is stored.
- **A row handle could alias another row after 4,096 replacements** of the
  same table's rows, because the twelve-bit generation wrapped. It no longer
  wraps: past the last generation the table refuses to issue row handles
  (`RFC_TABLE_UNADDRESSABLE`) until the function is recreated.
- **A truncated chunked table stream was returned as a smaller table** when
  its length happened to divide evenly by the row width; it is reported as
  undecodable.
- The layout-less `WA` read allocated on every call; it no longer does.

## 2026.9.2.1

Release gate run on 2026-09-02 against the a4h ABAP Platform Trial (kernel
7.58): **506 Rust tests and 263 Python tests, no failures and no skips**, with
SNC, wsRFC and the async driver all enabled. erpl's own suites through the
C-ABI shim: rfc 31/32 (the nwrfc-only backend file skips), odp 24/25 (a delta
cursor the server refuses to close on SAP's library too), bics 45/45.

### Changed

- **A reply table is one image, and rows are views into it** (erpl-proto#61).
  `Table::rows` is now a `Rows` view over the inflated stream — `len()`,
  `get(i)`, `iter()`, indexing — instead of a `Vec<Vec<u8>>` cut out of it
  one allocation per row while the stream was still alive. Decoding 32,768
  rows of `RFC_READ_TABLE` went from 32,786 allocations to under 64. Rows
  shorter than the declared width are padded to it on receipt (spec TBL-1)
  and a wider row is refused rather than cut. Rust callers that held
  `&[Vec<u8>]` use `rows()` the same way; `to_vec()` gives the old shape.
- **The C-ABI shim no longer builds a container per row.** The reply's
  image is moved into the table container, a row handle is packed into the
  pointer (spec ABI-21), `RfcGetChars` copies UTF-16 straight into the
  caller's buffer with blank padding, and a held row handle is reported
  `RFC_INVALID_HANDLE` once the rows are replaced or the function destroyed.
  Measured through the ABI on a4h with eight concurrent readers of
  `REPOSRC`: process high-water mark 669 MB → 268 MB, 75 MB → 33 MB per
  reader for a 32 MB batch (the reference: 36), registry entries per batch
  229,000 → 26.
- **Less work per call and per row elsewhere.** The function interface is no
  longer cloned on every call, the deep XML section is parsed once, a
  received record's payload is no longer copied out of its frame, and
  `StructureMeta::decode_ref` decodes a row without copying every field name
  — which is what the Python binding now uses per row.

### Fixed

- **A basXML reply carrying a deep parameter was refused** (erpl-proto#60).
  A deep structure, or a table outside the TABLES position, arrives in a
  basXML reply with its members nested — a row's member may itself be a table
  (`TTYP`) or a structure (`STRU`) — and the decoder imaged every parameter
  flat, refusing the first nested table it met with *"a Table cannot be
  rendered from a structured value"*, naming a member no function declares.
  Every BICS metadata module is basXML-flagged, so erpl's BICS suite went
  from 45/45 to 23/45 on 2026.9.2. Such a parameter is now delivered as the
  classic encoding delivers it, a `DeepElement` tree in `deep_tree`/`deep`,
  and the two encodings are asserted identical on a live BICS flow (spec
  BXML-14). One visible shift for the Rust API: a basXML deep-structure export
  whose members happen to be flat now lands in `deep_tree` rather than in
  `values` as bytes — which is where the classic reply already put it.
- **A basXML structure image carried its alignment padding** where a classic
  one does not (spec TBL-1); rebuilt images are now sized to the fields' extent.
- Nested `STRU` members of imaged structures and rows are rebuilt from their
  own layouts, and on the request side expanded, with a nested `TTYP` member
  sent empty; previously either was refused.

## 2026.9.2

Release gate run on 2026-09-01 against the a4h ABAP Platform Trial (kernel
7.58): **463 Rust tests and 263 Python tests, no failures and no skips**, with
SNC, wsRFC and the async driver all enabled.

### Fixed

Six defects, all in code that shipped in 2026.9.1. Every one of them either
succeeded on the classic encoding or failed with a message naming nothing,
which is how they reached a release.

- **ODP replication was broken** (erpl-proto#53). `RODPS_REPL_ODP_FETCH_XML`
  answered every call with an ABAP short dump. Three defects, each alone
  sufficient, found by capturing SAP's own library making the same call and
  diffing the request:

  - A name XML reserves must be escaped. XML forbids any name beginning with
    `xml`, and asXML inserts a hyphen after the first character, so the field
    `XML_FORMAT` goes on the wire as `X-ML_FORMAT`.
  - A packed decimal must carry its declared scale: a nine-decimal element is
    `0.000000000`, not `0`. The scale lives in the DDIC element rather than
    the interface, and the renderer was ignoring the one it already had, so
    structure fields were affected too.
  - Every table the function declares appears in the request, in metadata
    order, empty if unsupplied — including one that only carries results back.

  With all three, the request is byte-identical to the reference's.

- **A `CHANGING` parameter typed `Table` was dropped** (erpl-proto#57). A table
  says so either by its direction or by its own type, and only the first was
  honoured. basXML then refused the call locally; the classic encoding sent it
  and ABAP short-dumped.

- **A table row arriving without its alignment padding was refused**
  (erpl-proto#54). The declared width is the row padded to its alignment and
  the server sends the fields without it, so a 32-byte row arrives as 29.

`ERPL_DUMP_BASXML=1` prints a basXML request document, as `ERPL_DUMP_FIELDS`
prints a reply's fields. Every ODP defect above was read off that dump.

## 2026.9.1

Release gate run on 2026-08-31 against the a4h ABAP Platform Trial (kernel
7.58): **453 Rust tests and 263 Python tests, no failures and no skips**, with
SNC, wsRFC and the async driver all enabled.

### Fixed

- **The package's own links no longer 404.** `Homepage` and `Issues` pointed at
  a repository that is not public, so every reader following them -- including
  from the "Issues" link on the PyPI page, which is where a bug report starts --
  got GitHub's 404. They now point at
  [erpl-pyrfc-issues](https://github.com/DataZooDE/erpl-pyrfc-issues), which
  carries the tracker, the migration guide, this changelog and the runnable
  examples.

### Added

- **The rest of PyRFC's module surface** — 17 names that were missing, so that
  `from pyrfc import ...` works for everything the reference exported.
  `pyrfc.cancel_connection(conn)` in particular was an `AttributeError` where
  PyRFC has a working function; the capability existed as `conn.cancel()` but
  under a name PyRFC callers do not use.

  The enums (`RfcFieldType`, `RfcParameterDirection`, `RCStatus`, `UnitState`,
  `UnitCallType`) carry the SDK's own numeric values, read off the reference
  rather than chosen, because callers store and compare them.

  The ISO/SAP language table was derived by asking the reference for all 676
  two-letter combinations and keeping the 40 that answered with a printable
  character *and* round-tripped. Unmapped codes do not fail there — they return
  an arbitrary character — so round-tripping is what separates a mapping from
  noise. Here an unmapped code raises instead, since a caller cannot otherwise
  tell a real key from a wrong one.

  `set_ini_file_directory`, `reload_ini_file` and `set_cryptolib_path` raise
  `NotImplementedError`: they configure the SDK, and a connection that silently
  did not use the destination you configured is worse than one that says so.


## 2026.8.31

Release gate run on 2026-08-30 against the a4h ABAP Platform Trial (kernel
7.58): **437 Rust tests and 208 Python tests, no failures and no skips**, with
SNC, wsRFC and the async driver all enabled.

### Added

- **`Throughput` monitoring.** The same class PyRFC had, with the same seven
  `stats` keys, the same attach/detach methods, and the same details a caller
  could depend on — one monitor summing several connections, metadata lookups
  counting as calls, `getFromConnection` preserving object identity, `reset`
  zeroing without detaching.

  Verified side by side against the real PyRFC 3.3.1 on an identical call:
  `numberOfCalls` and `receivedBytes` match exactly. `sentBytes` is lower
  because SAP's client sends a session preamble on its first call that this one
  omits — the basis is the same, there is simply less traffic.

  `stats_ns` is an addition with no PyRFC equivalent: the same counters
  unrounded, plus `networkWriteTime` and `replyWaitTime`. Times in `stats` are
  milliseconds, so `serializationTime` reads 0 for ordinary calls, exactly as
  the reference reports it.

  Nothing is measured until a monitor is attached — the connection checks
  before it reads a clock, and a test asserts that an unattached call takes
  zero timestamps.

  Previously a documented non-goal on the grounds that these were
  "SDK-internal counters that do not exist here". That was wrong: they are
  ordinary measurements at a client's own API boundary. Only `serverTime` needs
  the backend to report it, and PyRFC never exposed that one.

### Fixed

- **`ABAP object/class types` was never a real non-goal**, and no longer
  appears as one. Listing it implied PyRFC could pass an ABAP object where this
  package could not; neither can. PyRFC re-exports the SDK's
  `RfcFieldType.RFCTYPE_ABAPOBJECT` constant and offers no API around it, and
  the ABAP kernel refuses an object reference in an RFC interface at all —
  FL393, *"You can only use LIKE and TYPE to specify types in RFC"*. Measured
  on kernel 7.58 by every route the interface tables allow, with the same
  parameter accepted the moment the RFC flag is off; 5,916 object-reference
  parameters exist there and none is on any of the 22,931 RFC-enabled modules.

  Recorded as spec META-7 and re-measured on every test run by the
  `Z_ERPL_OBJ_TRIPWIRE` fixture, so a kernel that relaxes the rule is reported
  rather than assumed away.

## 2026.8.30

Release gate run on 2026-08-30 against the a4h ABAP Platform Trial (kernel
7.58): **414 Rust tests and 190 Python tests, no failures and no skips**, with
SNC, wsRFC and the async driver all enabled.

### Added

- **basXML serialization, transparently.** SAP marks some function modules as
  basXML-serialized (`TFDIR-FMODE = 'X'`) and the SDK uses that encoding for
  them without being asked, which is why PyRFC exposes no API for it. Calls to
  such a module now work here too, and return what the classic encoding would
  have returned — same values, same types, same padding. Previously they were
  a documented non-goal.

  `basxml=False` in the connection parameters forces the classic encoding
  everywhere. It is an escape hatch, not a feature: the server chooses, and a
  client can decline but not impose.

### Fixed

- **BASXML is no longer a non-goal**, and the entries saying so in
  `MIGRATION.md` and `OPEN_POINTS.md` are retracted. (This entry also called
  `ABAP object/class types` a non-goal; that was wrong and is corrected in
  the next release — see below.)

## 2026.8.29.1

Two compatibility fixes, both found by running the same script under SAP's
PyRFC 3.3.1 and under this package and diffing the output — see
`examples/run_both.sh`, which is that comparison as a script anyone can run.

Release gate run on 2026-08-29 against the a4h ABAP Platform Trial (kernel
7.58): **378 Rust tests and 182 Python tests, no failures and no skips**, with
SNC, wsRFC and the async driver all enabled.

### Fixed

- **`get_connection_attributes()["language"]` reported the caller's `EN` rather
  than the `E` that was logged on with.** SAP maps a language to its
  one-character code before sending it, and its own client reports that form
  here. This was the only field the two libraries disagreed on.

- **A connection was left permanently broken after a `MESSAGE`-raised failure
  when the metadata cache was cold.** ABAP drops the conversation after such a
  failure and the gateway reports it on the *next* call, which the binding
  recovers from by reopening and re-issuing. But when that next call also had
  to fetch the function's interface, the dead conversation was found by the
  metadata round trip, whose failure returned directly and skipped the recovery
  — so every later call on that connection failed too.

  The suite could not see it: the metadata cache is shared by the whole
  process, so any earlier call on the same function left it warm and moved the
  failure onto the call, which did recover. The regression test for it now runs
  in a subprocess, which is the only place the cold path is real.

### Added

- `examples/`, four runnable examples exercised by the suite rather than only
  shipped: the install wall a new machine hits, the side-by-side against real
  PyRFC 3.3.1, and a tour of the migration surface.

## 2026.8.29

First release. Release gate run on 2026-08-29 against the a4h ABAP Platform
Trial (kernel 7.58): **378 Rust tests and 176 Python tests, no failures and no
skips**, with SNC, wsRFC and the async driver all enabled. A PyRFC-compatible SAP RFC client over a pure-Rust protocol
core, with no SAP NW RFC SDK and no ICU.

Versions are calendar dates, `YYYY.M.D`, as the erpl projects use. An earlier
plan to start at `4.0.0` — on the grounds that SAP's PyRFC ended at 3.x — was
dropped: the two distributions are separately named, so nothing ever compares
one version to the other.

Not yet used in anger by anyone but us.

### Works

Connections (direct, load-balanced, saprouter), `call()` with full dict and
table marshalling, the exception hierarchy with `code`/`key`/`msg_*`, the
config options (`rstrip`, `dtime`, `return_import_params`, `timeout`),
`get_connection_attributes`, `get_function_description`, the inbound `Server`,
and classic tRFC/qRFC units. Every ABAP scalar round-trips exactly, including
INT8 past 2^53, DECFLOAT34 at 34 digits, and UTCLONG.

**SNC** through the `snc_*` parameter family. **`cancel()`** stops the running
ABAP, and `timeout` cancels rather than abandoning the conversation while the
function runs on.

**wsRFC** is an extension beyond PyRFC: X.509 client-certificate sign-on over a
WebSocket. It is X.509-only, because every other wsRFC client credential
funnels through a proprietary assertion that cannot be reproduced outside
SAP's own crypto library.

Anything that cannot be honoured is refused rather than quietly downgraded —
an incomplete SNC configuration, a certificate without its key, SNC asked for
on a WebSocket, two routes at once.

### Differences from PyRFC

`MIGRATION.md` is the contract. The short version: bgRFC units, throughput
monitoring, ABAP object types and BASXML are deliberate non-goals and fail
loudly; `handle` is a counter rather than an SDK pointer; and a connection may
be handed to another thread to `cancel()` it, though calls still serialise.

*(Three of those four did not survive. BASXML shipped in 2026.8.30, throughput
monitoring and the correction to the ABAP-object claim are in the entry at the
top of this file. `MIGRATION.md` remains the contract; this paragraph is what
was true at this release.)*
