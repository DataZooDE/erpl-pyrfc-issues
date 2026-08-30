"""The migration surface, exercised against a live system.

Example 02 shows that the same script runs under either library. This one goes
wider: the parts of PyRFC's API that migrating code actually depends on, each
one called for real and printed with what came back.

Everything here is stock ABAP — `STFC_STRUCTURE`, `RFC_READ_TABLE`,
`RFC_RAISE_ERROR`, `RFC_PING_AND_WAIT` — so you can run it against any system
you can already reach.
"""

import datetime
import threading
import time

import pyrfc

from _params import params


def section(title):
    print(f"\n\033[1m== {title} ==\033[0m")


def show(label, value):
    print(f"  {label:<22} {value!r}")


connection_params = params()

section("connection identity and liveness")
conn = pyrfc.Connection(config={"rstrip": True}, **connection_params)
show("alive", conn.alive)
show("handle", conn.handle)
show("ping()", conn.ping())
show("sysId", conn.get_connection_attributes()["sysId"])

section("introspecting an interface")
description = conn.get_function_description("STFC_STRUCTURE")
show("name", description["name"])
for parameter in description["parameters"]:
    show(parameter["name"], (parameter["direction"], parameter["parameter_type"]))

section("dtime=False: dates and times as ABAP strings")
sent = {"RFCDATE": "20260823", "RFCTIME": "113456", "RFCINT4": 345}
got = conn.call("STFC_STRUCTURE", IMPORTSTRUCT=sent)["ECHOSTRUCT"]
show("RFCDATE", got["RFCDATE"])
show("RFCTIME", got["RFCTIME"])

section("dtime=True: the same fields as datetime objects")
with pyrfc.Connection(config={"rstrip": True, "dtime": True}, **connection_params) as typed:
    got = typed.call("STFC_STRUCTURE", IMPORTSTRUCT=sent)["ECHOSTRUCT"]
    show("RFCDATE", got["RFCDATE"])
    show("RFCTIME", got["RFCTIME"])
    assert isinstance(got["RFCDATE"], datetime.date)
    assert isinstance(got["RFCTIME"], datetime.time)

section("per-call options override the connection config")
# `rstrip` is on for this connection; one call opts out of it and keeps ABAP's
# trailing blanks, which is how PyRFC let you mix the two.
padded = conn.call("STFC_CONNECTION", REQUTEXT="trailing blanks kept",
                   options={"rstrip": False})["ECHOTEXT"]
show("rstrip=False", padded[:40] + "...")
show("rstrip=True", conn.call("STFC_CONNECTION", REQUTEXT="trailing blanks kept")["ECHOTEXT"])

section("tables in and out")
result = conn.call(
    "RFC_READ_TABLE",
    QUERY_TABLE="T000",
    DELIMITER="|",
    FIELDS=[{"FIELDNAME": "MANDT"}, {"FIELDNAME": "MTEXT"}, {"FIELDNAME": "ORT01"}],
    ROWCOUNT=3,
)
show("FIELDS", [f["FIELDNAME"] for f in result["FIELDS"]])
for row in result["DATA"]:
    show("row", row["WA"])

section("the exception hierarchy")
# A declared exception: the business case said no. The name arrives in `key`.
try:
    conn.call("RFC_READ_TABLE", QUERY_TABLE="NO_SUCH_TABLE_HERE")
except pyrfc.ABAPApplicationError as error:
    show("class", type(error).__name__)
    show("code / key", (error.code, error.key))

# A MESSAGE-raised failure: no key, but a T100 message identity.
try:
    conn.call("RFC_RAISE_ERROR", MESSAGETYPE="E")
except pyrfc.ABAPApplicationError as error:
    show("class", type(error).__name__)
    show("msg_class/number", (error.msg_class, error.msg_number))

# Type A ends the ABAP program outright, so it is a runtime error, not a
# declared one -- the distinction migrating code switches on.
try:
    conn.call("RFC_RAISE_ERROR", MESSAGETYPE="A")
except pyrfc.ABAPRuntimeError as error:
    show("class", type(error).__name__)
    show("code / msg_type", (error.code, error.msg_type))

show("still alive", conn.alive)

section("cancelling a call in flight")
# RFC_PING_AND_WAIT sits in the server for as long as it is told to, so a call
# that returns early can only have been cut short.
threading.Thread(target=lambda: (time.sleep(3), conn.cancel())).start()
started = time.monotonic()
try:
    conn.call("RFC_PING_AND_WAIT", SECONDS=20)
except pyrfc.CommunicationError as error:
    show("after", f"{time.monotonic() - started:.1f}s of a 20s call")
    show("code / key", (error.code, error.key))

show("usable again", conn.call("STFC_CONNECTION", REQUTEXT="after cancel")["ECHOTEXT"])
conn.close()
show("alive after close", conn.alive)

print("\nOK")
