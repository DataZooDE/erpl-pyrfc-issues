"""Connection parameters from the environment, shared by the examples.

Deliberately the same names the test suite uses (`tests/conftest.py`), so one
exported environment runs both. Nothing here is specific to either library: the
examples import this module and hand the result straight to `pyrfc.Connection`,
which is the point — the parameters are part of the compatible surface.
"""

import os
import sys


def params():
    user = os.environ.get("SAP_USER")
    passwd = os.environ.get("SAP_PASSWD")
    if not user or not passwd:
        sys.exit("set SAP_USER and SAP_PASSWD before running this example")
    return {
        "ashost": os.environ.get("SAP_ASHOST", "localhost"),
        "sysnr": os.environ.get("SAP_SYSNR", "00"),
        "client": os.environ.get("SAP_CLIENT", "001"),
        "user": user,
        "passwd": passwd,
        "lang": os.environ.get("SAP_LANG", "EN"),
    }
