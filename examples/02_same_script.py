"""The same script, under SAP's PyRFC and under erpl-pyrfc.

This file is the whole argument. It is ordinary PyRFC code — `import pyrfc`,
open a connection, call function modules — written without regard to which
implementation answers the import. `run_both.sh` runs it twice against the same
ABAP system, once under each library, and diffs the two outputs.

Everything it touches is stock: `STFC_CONNECTION`, `STFC_STRUCTURE` and
`RFC_READ_TABLE` exist on every ABAP system, so there is no fixture to deploy
and nothing here that only our own system would answer.

Output is formatted field by field rather than by printing dicts, because a
dict's repr depends on insertion order. Two libraries that both return the
right values could still print them in a different sequence, and that would
show up in the diff as a difference that is not one.
"""

import pyrfc

from _params import params


def show(label, value):
    print(f"{label:<24} {value!r}")


with pyrfc.Connection(config={"rstrip": True}, **params()) as conn:
    print("== connection ==")
    attributes = conn.get_connection_attributes()
    for key in ("sysId", "client", "user", "language"):
        show(key, attributes[key])
    show("alive", conn.alive)

    print("\n== STFC_CONNECTION ==")
    echo = conn.call("STFC_CONNECTION", REQUTEXT="the same script, either library")
    show("ECHOTEXT", echo["ECHOTEXT"])

    print("\n== STFC_STRUCTURE: a structure round trip ==")
    sent = {
        "RFCFLOAT": 1.23456789,
        "RFCCHAR1": "A",
        "RFCCHAR2": "BC",
        "RFCCHAR4": "DEFG",
        "RFCINT1": 1,
        "RFCINT2": 2,
        "RFCINT4": 345,
        "RFCHEX3": b"\x01\x02\x03",
        "RFCDATE": "20260823",
        "RFCTIME": "113456",
    }
    got = conn.call("STFC_STRUCTURE", IMPORTSTRUCT=sent)["ECHOSTRUCT"]
    for field in sorted(sent):
        show(field, got[field])

    print("\n== RFC_READ_TABLE: a table read ==")
    table = conn.call(
        "RFC_READ_TABLE",
        QUERY_TABLE="T000",
        DELIMITER="|",
        FIELDS=[{"FIELDNAME": "MANDT"}, {"FIELDNAME": "MTEXT"}],
        OPTIONS=[{"TEXT": "MANDT = '001'"}],
    )
    show("FIELDS", [f["FIELDNAME"] for f in table["FIELDS"]])
    show("DATA", [row["WA"] for row in table["DATA"]])

    print("\n== a declared ABAP exception ==")
    try:
        conn.call("RFC_READ_TABLE", QUERY_TABLE="NO_SUCH_TABLE_HERE")
    except pyrfc.ABAPApplicationError as error:
        show("type", type(error).__name__)
        show("code", error.code)
        show("key", error.key)
        show("msg_class", error.msg_class)

print("\nOK")
