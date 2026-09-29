import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

token = os.environ["IBKR_FLEX_TOKEN"]
query_id = os.environ["IBKR_FLEX_QUERY_ID"]

request_params = urlencode(
    {
        "t": token,
        "q": query_id,
        "v": 3,
    }
)
request = Request(
    "https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService/SendRequest?"
    + request_params
)

with urlopen(request, timeout=30) as response:
    generation_response = ElementTree.fromstring(response.read())

if generation_response.findtext("Status") != "Success":
    message = generation_response.findtext("ErrorMessage", "Unknown IBKR error")
    raise RuntimeError(f"IBKR report generation failed: {message}")

reference_code = generation_response.findtext("ReferenceCode")
if not reference_code:
    raise RuntimeError("IBKR did not return a report reference code")

download_params = urlencode(
    {
        "t": token,
        "q": reference_code,
        "v": 3,
    }
)
download_request = Request(
    "https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService/GetStatement?"
    + download_params
)

with urlopen(download_request, timeout=30) as response:
    Path("ibkr_report.xml").write_bytes(response.read())

print("IBKR report downloaded to ibkr_report.xml")
