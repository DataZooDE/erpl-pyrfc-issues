# Runnable examples

Four examples, all of which really run. `tests/test_examples.py` executes the
Python ones as part of the suite, so a change that breaks one fails the build
rather than being found by a reader.

Everything here uses **stock** ABAP — `STFC_CONNECTION`, `STFC_STRUCTURE`,
`RFC_READ_TABLE`, `RFC_RAISE_ERROR`, `RFC_PING_AND_WAIT` — so you can run them
against any system you can already reach. No fixtures to deploy.

```bash
export SAP_ASHOST=localhost SAP_SYSNR=00 SAP_CLIENT=001
export SAP_USER=DEVELOPER SAP_PASSWD=...
```

| | What it shows |
|---|---|
| `01_the_wall.sh` | what a new machine hits installing SAP's PyRFC today |
| `02_same_script.py` | one script, unchanged, under either library |
| `run_both.sh` | runs `02` under both and diffs the output |
| `03_compatibility_tour.py` | the migration surface, called for real |

## `01_the_wall.sh`

Runs in a throwaway `python:3.12-slim` container so nothing already on the host
can make it look easier than it is. `pip install pyrfc` fails — every release
was yanked when SAP archived the project — and a pinned `pyrfc==3.3.1` gets as
far as trying to compile against the closed-source SAP NW RFC SDK, because
3.3.1 shipped no Linux wheel. Then `pip install erpl-pyrfc` works.

Needs Docker and a network. Not run by the test suite.

## `02_same_script.py` and `run_both.sh`

`02_same_script.py` is ordinary PyRFC code, written without regard to which
implementation answers `import pyrfc`. `run_both.sh` runs it twice — once in a
virtualenv holding SAP's PyRFC 3.3.1, once in one holding `erpl-pyrfc` — and
diffs the two outputs.

```bash
SAPNWRFC_HOME=/path/to/nwrfcsdk ./run_both.sh
```

`SAPNWRFC_HOME` is needed to **build** PyRFC 3.3.1 from its sdist; without it
the script says so and stops rather than quietly comparing one library against
itself. The two libraries never meet: each has its own virtualenv, and only one
is ever on `sys.path`.

The asymmetry is the point. One side needs an SDK download, an S-user account
to get it, and its shared libraries on `LD_LIBRARY_PATH`. The other needs
`pip install`.

## `03_compatibility_tour.py`

The parts of PyRFC's API migrating code actually depends on: connection
identity, interface introspection, `dtime` on and off, per-call options
overriding the connection config, tables in and out, the exception hierarchy,
and a `cancel()` that stops a 20-second call after 3.

## Recordings

`tapes/` holds the [VHS](https://github.com/charmbracelet/vhs) tapes behind the
recordings in
[the write-up](https://erpl.io/blog/drop-in-replacement-for-archived-pyrfc).
Render one from `bindings/pyrfc`:

```bash
vhs examples/tapes/02-side-by-side.tape     # writes into examples/tapes/out/
```

Each tape runs the example for real; nothing on screen is typed in. The
credentials and the SDK path come from a file the tapes source, which is not in
the repository — see the `Hide` block at the top of each one for what it needs.

---

## Where these come from

These are the examples from the `erpl-pyrfc` test suite, published here because
the [blog post](https://erpl.io/blog/drop-in-replacement-for-archived-pyrfc/)
invites you to run them and a link into a private repository would not.

They run against a real SAP system; `run_both.sh` additionally needs the SAP NW
RFC SDK, because it builds SAP's own PyRFC in order to compare the two
libraries side by side. That comparison is the point: it checks *behaviour*,
never source.
