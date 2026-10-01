import os
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import sleep
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

if __package__:
    from investments.ibkr_parser import (
        MAX_IBKR_REPORT_BYTES,
        parse_flex_xml,
        parse_ibkr_xml,
    )
else:
    from ibkr_parser import MAX_IBKR_REPORT_BYTES, parse_flex_xml, parse_ibkr_xml

FLEX_URL = "https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService"
RETRYABLE_CODES = {"1009", "1018", "1019", "1021"}


def _request_flex(endpoint: str, token: str, query: str) -> bytes:
    params = urlencode({"t": token, "q": query, "v": 3})
    request = Request(f"{FLEX_URL}/{endpoint}?{params}")
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read(MAX_IBKR_REPORT_BYTES + 1)
    except URLError, TimeoutError, OSError:
        raise RuntimeError("Could not connect to IBKR; check your network") from None
    if len(payload) > MAX_IBKR_REPORT_BYTES:
        raise ValueError("IBKR report exceeds 10 MB")
    return payload


def download_ibkr_report(token: str, query_id: str) -> bytes:
    token = token.strip()
    query_id = query_id.strip()
    if not token or not query_id:
        raise ValueError("Set IBKR_FLEX_TOKEN and IBKR_FLEX_QUERY_ID in .env")

    response = parse_flex_xml(BytesIO(_request_flex("SendRequest", token, query_id)))
    if (
        response.tag != "FlexStatementResponse"
        or response.findtext("Status") != "Success"
    ):
        raise RuntimeError(
            "IBKR report generation failed; check your token and query ID"
        )
    reference_code = response.findtext("ReferenceCode", "").strip()
    if not reference_code:
        raise RuntimeError("IBKR did not return a report reference code")

    for _ in range(6):
        sleep(10)
        payload = _request_flex("GetStatement", token, reference_code)
        response = parse_flex_xml(BytesIO(payload))
        if response.tag == "FlexQueryResponse":
            parse_ibkr_xml(BytesIO(payload))
            return payload
        if (
            response.tag != "FlexStatementResponse"
            or response.findtext("Status") != "Fail"
            or response.findtext("ErrorCode") not in RETRYABLE_CODES
        ):
            raise RuntimeError(
                "IBKR report retrieval failed; check your query settings"
            )

    raise RuntimeError("IBKR report is still unavailable; try again later")


def main() -> None:
    temporary_path: Path | None = None
    try:
        payload = download_ibkr_report(
            os.getenv("IBKR_FLEX_TOKEN", ""), os.getenv("IBKR_FLEX_QUERY_ID", "")
        )
        output = Path("ibkr_report.xml")
        with NamedTemporaryFile(
            dir=output.parent, prefix=".ibkr-report-", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(payload)
        temporary_path.replace(output)
    except (RuntimeError, ValueError) as error:
        raise SystemExit(str(error)) from None
    except OSError:
        raise SystemExit("Could not save the IBKR report locally") from None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    print("IBKR report downloaded to ibkr_report.xml")


if __name__ == "__main__":
    main()
