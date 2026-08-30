"""Throughput counters, printed field by field.

Run under SAP's PyRFC and under ours and diff the two, the same way
`run_both.sh` compares a call: identical script, identical system, one
library swapped.

Some numbers legitimately differ. The call count depends on which metadata
function modules a library uses, and byte counts depend on where each draws
the line between payload and framing. Printing them side by side is how those
differences become known rather than assumed.
"""

import pyrfc

from _params import params


def show(label, value):
    print(f"{label:<24} {value!r}")


with pyrfc.Connection(config={"rstrip": True}, **params()) as conn:
    monitor = pyrfc.Throughput([conn])

    print("== a fresh monitor ==")
    for key, value in monitor.stats.items():
        show(key, value)

    print("\n== after one STFC_CONNECTION ==")
    conn.call("STFC_CONNECTION", REQUTEXT="throughput")
    stats = monitor.stats
    # Printed key by key, in the library's own order: dumping the dict would
    # compare insertion order too, and show a difference that is not one.
    for key in stats:
        show(key, stats[key])

    print("\n== shape ==")
    show("keys", list(stats))
    show("connections is a set", isinstance(monitor.connections, set))
    show("getFromConnection", pyrfc.Throughput.getFromConnection(conn) is monitor)

    print("\n== after reset ==")
    monitor.reset()
    show("numberOfCalls", monitor.stats["numberOfCalls"])
    show("sentBytes", monitor.stats["sentBytes"])

print("\nOK")
