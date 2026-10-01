from io import BytesIO
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request

import pytest

from investments import ibkr_importer

GENERATION = (
    b"<FlexStatementResponse><Status>Success</Status>"
    b"<ReferenceCode>REFERENCE123</ReferenceCode>"
    b"<url>https://untrusted.example/report</url></FlexStatementResponse>"
)
PENDING = (
    b"<FlexStatementResponse><Status>Fail</Status>"
    b"<ErrorCode>1019</ErrorCode></FlexStatementResponse>"
)
REPORT = (
    b'<FlexQueryResponse><Trade accountId="TEST_ACCOUNT" tradeID="123" '
    b'assetCategory="STK" quantity="1" tradePrice="10" fxRateToBase="1" '
    b'buySell="BUY" netCash="-11" dateTime="20260929;120000" '
    b'symbol="TEST" currency="USD" /></FlexQueryResponse>'
)


def _fake_http(
    monkeypatch: pytest.MonkeyPatch, responses: list[bytes]
) -> tuple[list[str], list[int]]:
    payloads = iter(responses)
    urls: list[str] = []
    delays: list[int] = []

    def fake_urlopen(request: Request, *, timeout: int) -> BytesIO:
        assert timeout == 30
        urls.append(request.full_url)
        return BytesIO(next(payloads))

    monkeypatch.setattr(ibkr_importer, "urlopen", fake_urlopen)
    monkeypatch.setattr(ibkr_importer, "sleep", delays.append)
    return urls, delays


@pytest.mark.parametrize("pending_count", [0, 1])
def test_download_uses_reference_code_and_waits_for_report(
    monkeypatch: pytest.MonkeyPatch, pending_count: int
) -> None:
    urls, delays = _fake_http(
        monkeypatch, [GENERATION, *([PENDING] * pending_count), REPORT]
    )

    assert ibkr_importer.download_ibkr_report("FAKE_TOKEN", "QUERY123") == REPORT
    assert parse_qs(urlparse(urls[0]).query)["q"] == ["QUERY123"]
    for url in urls[1:]:
        assert urlparse(url).hostname == "ndcdyn.interactivebrokers.com"
        assert parse_qs(urlparse(url).query)["q"] == ["REFERENCE123"]
    assert delays == [10] * (pending_count + 1)


def test_download_stops_after_bounded_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    urls, delays = _fake_http(monkeypatch, [GENERATION, *([PENDING] * 6)])

    with pytest.raises(RuntimeError, match="still unavailable"):
        ibkr_importer.download_ibkr_report("FAKE_TOKEN", "QUERY123")

    assert len(urls) == 7
    assert delays == [10] * 6


def test_download_rejects_generation_failure_without_echoing_provider_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_http(
        monkeypatch,
        [
            (
                b"<FlexStatementResponse><Status>Fail</Status>"
                b"<ErrorMessage>FAKE_SECRET</ErrorMessage></FlexStatementResponse>"
            )
        ],
    )
    with pytest.raises(RuntimeError, match="generation failed") as error:
        ibkr_importer.download_ibkr_report("FAKE_TOKEN", "QUERY123")
    assert "FAKE_SECRET" not in str(error.value)


@pytest.mark.parametrize(
    "response",
    [
        b"<FlexStatementResponse><Status>Success</Status></FlexStatementResponse>",
        (
            b"<FlexStatementResponse><Status>Success</Status>"
            b"<ReferenceCode> </ReferenceCode></FlexStatementResponse>"
        ),
    ],
)
def test_download_requires_reference_code(
    monkeypatch: pytest.MonkeyPatch, response: bytes
) -> None:
    _fake_http(monkeypatch, [response])
    with pytest.raises(RuntimeError, match="reference code"):
        ibkr_importer.download_ibkr_report("FAKE_TOKEN", "QUERY123")


def test_network_errors_do_not_expose_request_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_request(request: Request, *, timeout: int) -> BytesIO:
        raise URLError(request.full_url)

    monkeypatch.setattr(ibkr_importer, "urlopen", fail_request)
    with pytest.raises(RuntimeError, match="Could not connect") as error:
        ibkr_importer.download_ibkr_report("FAKE_SECRET", "QUERY123")
    assert "FAKE_SECRET" not in str(error.value)
    assert error.value.__suppress_context__


@pytest.mark.parametrize("token,query_id", [("", "123"), ("123", " ")])
def test_download_requires_credentials(token: str, query_id: str) -> None:
    with pytest.raises(ValueError, match="Set IBKR_FLEX_TOKEN"):
        ibkr_importer.download_ibkr_report(token, query_id)


@pytest.mark.parametrize(
    "response",
    [
        (
            b"<FlexStatementResponse><Status>Fail</Status>"
            b"<ErrorCode>1015</ErrorCode></FlexStatementResponse>"
        ),
        b"not XML",
        REPORT.replace(b'quantity="1"', b'quantity="abc"'),
    ],
)
def test_failed_download_preserves_existing_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, response: bytes
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("IBKR_FLEX_TOKEN", "FAKE_TOKEN")
    monkeypatch.setenv("IBKR_FLEX_QUERY_ID", "QUERY123")
    _fake_http(monkeypatch, [GENERATION, response])
    output = tmp_path / "ibkr_report.xml"
    output.write_bytes(b"existing report")

    with pytest.raises(SystemExit):
        ibkr_importer.main()

    assert output.read_bytes() == b"existing report"
    assert not list(tmp_path.glob(".ibkr-report-*"))


def test_successful_download_writes_private_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("IBKR_FLEX_TOKEN", "FAKE_TOKEN")
    monkeypatch.setenv("IBKR_FLEX_QUERY_ID", "QUERY123")
    _fake_http(monkeypatch, [GENERATION, REPORT])

    ibkr_importer.main()

    output = tmp_path / "ibkr_report.xml"
    assert output.read_bytes() == REPORT
    assert output.stat().st_mode & 0o777 == 0o600
    assert not list(tmp_path.glob(".ibkr-report-*"))


def test_download_rejects_oversized_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ibkr_importer, "MAX_IBKR_REPORT_BYTES", 64)
    _fake_http(monkeypatch, [b" " * 65])
    with pytest.raises(ValueError, match="exceeds 10 MB"):
        ibkr_importer.download_ibkr_report("FAKE_TOKEN", "QUERY123")
