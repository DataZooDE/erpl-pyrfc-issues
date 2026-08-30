<!--
Published copy of the migration guide. The library's source is not public; this
file is, because the blog post and the package metadata both point people here
and a link into a private repository helps nobody.
-->

# Migrating from SAP PyRFC

One page: what runs unchanged, what is deliberately absent, and where behaviour
differs. If your code only opens connections and calls function modules, you can
stop after the first table.

## Supported today

| PyRFC surface | Status |
|---|---|
| `Connection(**params)`, context manager, `close()` | works |
| `conn.call(name, **params)` with dict ↔ structure, `list[dict]` ↔ table | works |
| `conn.ping()`, `conn.alive`, `conn.handle`, `conn.reopen()` | works |
| `conn.get_connection_attributes()` | works |
| `conn.get_function_description(name)` | works, read-only |
| `config={"rstrip", "dtime", "return_import_params", "timeout"}` | works |
| Per-call `options={...}` overriding `config` | works |
| Exception hierarchy and `code`/`key`/`msg_*` attributes | works |
| `ashost`/`sysnr`/`client`/`user`/`passwd`/`lang`/`port` | works |
| `mshost`/`msserv`/`group` (load balancing) | works |
| `saprouter` | works |
| SNC parameter family (`snc_mode`/`snc_qop`/`snc_myname`/`snc_partnername`/`snc_lib`) | works |
| `conn.cancel()` | works — stops the running ABAP, as PyRFC's did |
| **basXML** serialization | works, transparently — nothing to switch on |
| `Throughput` monitoring | works — same seven `stats` keys |
| `pyrfc.Server`: `add_function`, `serve`, `start`/`stop` | works |
| tRFC/qRFC: `initialize_unit`, `fill_and_submit_unit`, `confirm_unit`, `destroy_unit` | works |

## Type mapping

Unchanged from PyRFC:

| ABAP | Python |
|---|---|
| CHAR, NUMC, STRING | `str` |
| BYTE (RAW), XSTRING | `bytes` |
| INT1, INT2, INT4, INT8 | `int` |
| FLOAT | `float` |
| BCD (packed), DECFLOAT16, DECFLOAT34 | `decimal.Decimal` |
| DATE, TIME | `str`, or `datetime.date`/`datetime.time` with `dtime=True` |
| STRUCTURE | `dict` |
| TABLE | `list[dict]` |

On input, numerics also accept `str`, decimals accept `int`/`float`/`str`, and
dates and times accept either the ABAP string form or `datetime` objects. A value
of the wrong type raises `TypeError` naming the parameter, as PyRFC did. A
parameter or structure field the interface does not declare is refused with
`ExternalRuntimeError` rather than silently dropped.

## Serving inbound calls

```python
server = pyrfc.Server({"gwhost": "sap.example.com", "gwserv": "3300",
                       "program_id": "MY_SERVER"}, connection_params)
server.add_function("STFC_CONNECTION", lambda ctx, **kw: {"ECHOTEXT": kw["REQUTEXT"]})
server.start()          # serves on a background thread
...
server.stop()
```

A handler is called as `handler(request_context, **import_parameters)` and
returns a dict of exports. Raising one of this package's exceptions with a `key`
sends ABAP that exception by name; any other exception becomes an error message.
`serve_one(timeout=...)` serves a single call if you want to drive the loop
yourself.

## Units of work

```python
unit = conn.initialize_unit()
conn.fill_and_submit_unit(unit, [("Z_MY_FUNCTION", {"IV_TEXT": "queued"})])
conn.confirm_unit(unit)          # this is what releases the work
```

Pass `queue_names=["MY_QUEUE"]` for qRFC. `destroy_unit(unit)` abandons without
confirming, leaving the TID on the server so the work can be retried.

## Deliberate non-goals

These are not planned. If your code needs one, this package is not a drop-in for
you:

- **bgRFC units** (`RfcCreateUnit`/`SubmitUnit` and the background unit API).
  `initialize_unit(background=True)` raises `NotImplementedError`. Classic tRFC
  and qRFC are in scope; bgRFC is not.

  This one is a real difference, and it is worth being precise about it, since
  PyRFC's own docstring says *"The background protocol (bgRFC) is not working in
  the current version"*. **That warning is stale** — measured against a live
  system, PyRFC 3.3.1 creates a unit, ships it, sees it reach `committed` and
  confirms it, both plain and queued. So code that relies on bgRFC does work
  today and will not work here.

  Three consequences beyond the protocol itself:

  - `get_unit_state` does not exist here at all. In PyRFC it is bgRFC-only —
    asking it about a classic unit is refused with *"No state check possible of
    non-bgRFC units"* — so it is only useful once bgRFC is.
  - `attributes` is rejected, and `queue_names` accepts exactly one name where
    a bgRFC unit may carry several.
  - **The default differs.** PyRFC's `initialize_unit()` defaults to
    `background=True`; this one defaults to `False`. A caller who wrote
    `initialize_unit()` and meant bgRFC gets a classic tRFC unit here, silently.
    Pass `background=` explicitly if it matters.

  What the protocol looks like on the wire is recorded in
  `docs/spec/20-bgrfc.md`.
- `reset_server_context()`, `free()` — each raises `NotImplementedError`
  pointing here rather than pretending to work.

**ABAP object/class types are not on this list, and were removed from it.**
Earlier versions of this guide named them, which implied PyRFC could pass an
ABAP object and we could not. Neither library can. PyRFC re-exports the SDK's
`RfcFieldType.RFCTYPE_ABAPOBJECT` constant and stops there — there is no API to
create, read or write one. And no function module can declare such a parameter
in the first place: the ABAP kernel refuses an object reference in an RFC
interface with FL393, *"You can only use LIKE and TYPE to specify types in
RFC"*. Measured on kernel 7.58, where 5,916 object-reference parameters exist
system-wide and none of them is on any of the 22,931 RFC-enabled function
modules. See spec META-7; the refusal is re-measured on every test run by
the project's live test suite.

## SNC

The `snc_*` family works: `snc_mode`, `snc_qop`, `snc_myname`,
`snc_partnername`, `snc_lib`. `snc_mode="0"` turns it off while leaving the
rest of the configuration in place, as PyRFC allowed. `snc_qop` takes 1
(authentication), 2 (integrity), 3 (privacy); 8 and 9 — "default" and
"maximum" — both resolve to privacy, the strongest level implemented. `snc_lib`
falls back to the `SNC_LIB` environment variable, and `snc_myname` may be
omitted to let the credential in the PSE decide.

An SNC configuration that cannot be honoured is an **error, never a plaintext
connection**: no library, no partner name, an unusable library, or an
unrecognised `snc_qop` all raise. A security parameter that is quietly ignored
is worse than one that is rejected, because it looks like success.

`SECUDIR` must point at the directory holding the client PSE, or
CommonCryptoLib cannot find its credentials and every attempt fails as a
defective token — which reads like a framing bug and is not one.

## Cancelling a call

`conn.cancel()` stops the running ABAP, as PyRFC's did. Call it from another
thread while a call is blocked; that thread raises `CommunicationError` with
`code == 7` and `key == "RFC_CANCELED"`.

`config={"timeout": n}` now cancels too, rather than abandoning the
conversation while the function runs on. Expensive ABAP really stops.

A cancel ends the conversation — that is the protocol, not a choice here — so a
fresh one is opened underneath and the handle stays usable. **Session state does
not survive it**: anything a stateful function group was holding is gone.

## Behavioural differences

**Connections are shareable enough to cancel.** `cancel()` is meant to be
called from another thread while a call is in flight — that is the only way it
can do anything — so a `Connection` may be handed to a second thread for that
purpose. Calls themselves still serialise: the connection is locked for the
duration of one, so two threads calling `call()` take turns rather than
interleaving. One connection per worker remains the sane arrangement; this is
about `cancel()`, not about sharing a connection for ordinary work.

**`handle` is a counter, not an SDK pointer.** It is unique and stable per
connection, which is all PyRFC documented it to be, but it does not correspond to
any address.

**Connections are single-threaded for calls.** As in PyRFC, a connection
belongs to the thread that opened it. Use one connection per thread; network
I/O releases the GIL, so threads do run concurrently. The exception is
`cancel()`, which exists precisely to be called from elsewhere while a call is
blocked.

**`Throughput` counts what it can honestly count.** `Throughput`,
`setOnConnection`, `getFromConnection`, `removeFromConnection`, `reset`,
`connections` and `stats` all behave as PyRFC's did, including the details a
caller might depend on: one monitor sums several connections, metadata lookups
count as calls, `getFromConnection` returns the object you attached rather than
a copy, and `reset` zeroes without detaching.

Two differences, both measured against the reference rather than assumed:

- **`sentBytes` is slightly lower than SAP's.** The counting basis is the same
  — `receivedBytes` matches to the byte on an identical call — but SAP's client
  sends a session preamble on its first call that this one omits, so it puts
  fewer bytes on the wire. The number is right; there is simply less of it.
- **`numberOfCalls` can differ** on the same code, because it counts metadata
  round trips and the two libraries do not fetch metadata with the same set of
  function modules. Both count them; neither count is wrong.

`applicationTime` is 0, as it is under PyRFC: it measures time spent *being* a
function module, which only a server does, and PyRFC exposes no way to attach a
monitor to a server.

Times are milliseconds, so `serializationTime` reads 0 for ordinary calls —
that is what the reference reports too, for the same reason, and reproducing it
is deliberate. `stats_ns` is an erpl addition giving the same counters
unrounded, plus `networkWriteTime` and `replyWaitTime`. `serverTime` is offered
by neither: ABAP reports it inside the reply and nothing here parses that
field, so there is no honest number to give.

**basXML happens to you, not by you.** SAP marks some function modules as
basXML-serialized (`TFDIR-FMODE = 'X'`), and the SDK uses that encoding for
them without being asked — which is why PyRFC exposes no API for it and needs
none. This package does the same: a call to such a module is serialized as
basXML and its reply read back from the document, and the values a caller sees
are the values the classic encoding would have given, padding included. If it
ever renders something wrongly, `basxml=False` in the connection parameters
forces the classic encoding everywhere without having to downgrade.

**Licence.** BUSL-1.1, not Apache-2.0. See the README.

**Every scalar type round-trips exactly**, including UTCLONG, INT8 beyond 2^53
and DECFLOAT34 at full 34-digit precision. A UTCLONG is text, in ABAP's own
`YYYY-MM-DD HH:MM:SS.fffffff` rendering; an initial one is the empty string,
because that is what ABAP renders it as, and giving it a date would be
inventing a value nobody set.

**A `MESSAGE`-raised failure costs the session, transparently.** A function
that fails through ABAP `MESSAGE` (as `RFC_RAISE_ERROR` does) makes ABAP drop
the conversation, and nothing on the wire says so. The exception is reported
normally; the *next* call then finds the conversation gone, and because the
gateway refused to route that call — so it never reached ABAP — the binding
reopens and re-issues it. The connection stays usable, as it did under PyRFC.
What does not survive is session state: anything set on that connection
(a stateful function group's globals, an open unit of work) is gone. A
*declared* exception is unaffected and leaves the session entirely intact.

## Extensions beyond PyRFC

- **wsRFC** — RFC over a WebSocket, which PyRFC had no equivalent for. Pass
  `wshost`, `wsport`, `tls_client_cert` and `tls_client_key` (optionally
  `ws_path`). The certificate **is** the credential: `user` and `passwd` play
  no part.

  X.509 is the only client credential this can present. Every password-,
  ticket- or bearer-based wsRFC method funnels through SAP's proprietary
  `sap-r3auth` assertion, which is CommonCryptoLib output and not reproducible
  outside it (spec WS-10) — so those are absent rather than half-working.

  The certificate and key are **DER**; a PEM file is refused with the `openssl`
  command that converts it. A half-configured credential (a certificate with no
  key, or `wshost` with no certificate) is an error, never a silent fall back
  to a classic connection.

  Two things about the server side, neither of them a limit of this transport:
  the certificate must be trusted by the ICM and mapped to a user
  (`SUSR_CERT_ASSIGN`), and **UCON applies to wsRFC where it does not apply to
  classic RFC** — a stock system allows the basis modules and rejects
  application ones with `UCON RFC Rejected` until they are released.

  `cancel()` is not available on a wsRFC connection: the cancel record is part
  of the classic conversation protocol. It reports that rather than doing
  nothing.


- `mshost_override`: where to actually dial the application server when the
  message server reports an address that only resolves inside the system's own
  network — a containerised system, typically. PyRFC had no equivalent because it
  had no way to express it.
