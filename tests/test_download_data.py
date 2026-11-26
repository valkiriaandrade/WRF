import io
import socket
import urllib.error
from datetime import datetime

import pytest

BASE = "https://ftp.cptec.inpe.br/modelos/tempo/WRF/ams_07km/recortes/regioes"


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def listing(*names):
    return "".join(f'<a href="{n}">{n}</a>' for n in ("?C=N;O=D", "/modelos/", *names))


SERVER = {
    f"{BASE}/": listing("2025/", "2026/"),
    f"{BASE}/2025/": listing("12/"),
    f"{BASE}/2025/12/": listing("31/"),
    f"{BASE}/2025/12/31/": listing("00/"),
    f"{BASE}/2025/12/31/00/": listing("WRF_cpt_07KM_SU_2025123100_2025123100.grib2"),
    f"{BASE}/2026/": listing("11/"),
    f"{BASE}/2026/11/": listing("24/", "25/"),
    f"{BASE}/2026/11/24/": listing("00/", "12/"),
    f"{BASE}/2026/11/24/00/": listing("WRF_cpt_07KM_SU_2026112400_2026112400.grib2"),
    f"{BASE}/2026/11/24/12/": listing("WRF_cpt_07KM_SU_2026112412_2026112412.grib2"),
    f"{BASE}/2026/11/25/": listing("00/"),
    # newest run exists but has no SU files yet
    f"{BASE}/2026/11/25/00/": listing("WRF_cpt_07KM_CO_2026112500_2026112500.grib2"),
}


def test_file_name_and_plan(download_module):
    run = datetime(2024, 8, 21, 12)
    assert download_module.file_name("SU", run, 117) == download_module.SAMPLE
    item = download_module.plan(run, [0])[0]
    assert item.url == f"{BASE}/2024/08/21/12/WRF_cpt_07KM_SU_2024082112_2024082112.grib2"


def test_latest_run_skips_runs_without_the_domain(download_module):
    assert download_module.latest_run("SU", read=SERVER.__getitem__) == datetime(2026, 11, 24, 12)
    runs = download_module.available_runs("SU", read=SERVER.__getitem__)
    assert runs[0] == datetime(2025, 12, 31) and len(runs) == 3
    with pytest.raises(download_module.DownloadError, match="No WRF run"):
        download_module.latest_run("XX", read=SERVER.__getitem__)


def test_fetch_downloads_then_skips(tmp_path, download_module):
    def opener(request, timeout):
        return FakeResponse(b"GRIB")

    dest = tmp_path / "run.grib2"
    assert download_module.fetch("https://x/run.grib2", dest, opener=opener) is True
    assert download_module.fetch("https://x/run.grib2", dest, opener=opener) is False


def test_missing_run_gives_clear_error(tmp_path, download_module):
    def opener(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)

    with pytest.raises(download_module.DownloadError, match="check the run and forecast hour"):
        download_module.fetch("https://x/old.grib2", tmp_path / "old.grib2", opener=opener)


class SizedResponse(FakeResponse):
    """A response that announces ``size`` bytes in Content-Length (whatever it sends)."""

    def __init__(self, body, size):
        super().__init__(body)
        self.headers = {"Content-Length": str(size)}


def test_truncated_download_is_retried_and_never_kept(tmp_path, monkeypatch, download_module):
    monkeypatch.setattr(download_module.time, "sleep", lambda seconds: None)
    answers = [SizedResponse(b"GRIB", 10), SizedResponse(b"GRIB-whole", 10)]
    dest = tmp_path / "run.grib2"
    opener = lambda request, timeout: answers.pop(0)  # noqa: E731
    assert download_module.fetch("https://x/run.grib2", dest, opener=opener) is True
    assert dest.read_bytes() == b"GRIB-whole" and not answers

    always_short = lambda request, timeout: SizedResponse(b"GRIB", 10)  # noqa: E731
    with pytest.raises(download_module.DownloadError, match="received 4 of 10 bytes"):
        download_module.fetch("https://x/b.grib2", tmp_path / "b.grib2", opener=always_short)
    assert list(tmp_path.iterdir()) == [dest]  # no truncated file, no .part left behind


def test_incomplete_chunked_response_is_retried(tmp_path, monkeypatch, download_module):
    import http.client

    monkeypatch.setattr(download_module.time, "sleep", lambda seconds: None)

    class Broken(FakeResponse):
        def read(self, *args):
            raise http.client.IncompleteRead(b"GR", 8)

    answers = [Broken(b""), FakeResponse(b"GRIB")]
    dest = tmp_path / "run.grib2"
    assert (
        download_module.fetch("https://x/run.grib2", dest, opener=lambda r, timeout: answers.pop(0))
        is True
    )
    assert dest.read_bytes() == b"GRIB"


RUN_FOLDER = listing(
    *(
        f"WRF_cpt_07KM_SU_2026112400_202611{d:02d}{h:02d}.grib2"
        for d, h in [(24, 0), (24, 3), (25, 0)]
    ),
    "WRF_cpt_07KM_NE_2026112400_2026112400.grib2",
)


def test_missing_forecast_hours_are_reported_with_the_available_ones(download_module):
    run = datetime(2026, 11, 24)
    items = download_module.plan(run, [0, 3, 25])
    read = {download_module.run_url(run): RUN_FOLDER}.__getitem__
    [message] = download_module.missing_from_run(run, items, read)
    assert "_2026112500.grib2" not in message and "2026112501" in message
    assert "hours available: 0 to 24 h, 3 files" in message
    assert download_module.missing_from_run(run, download_module.plan(run, [0], "CO"), read) == [
        "WRF_cpt_07KM_CO_2026112400_2026112400.grib2 is not in run 2026112400 "
        "(hours available: none yet)"
    ]


def test_missing_run_folder_is_reported(download_module):
    def read(url):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    run = datetime(2024, 8, 21, 12)
    with pytest.raises(download_module.DownloadError, match="Run 2024082112 is not on the server"):
        download_module.missing_from_run(run, download_module.plan(run, [0]), read)


def test_main_stops_before_downloading_missing_hours(tmp_path, monkeypatch, download_module):
    monkeypatch.setattr(download_module, "missing_from_run", lambda run, items: ["not there"])
    monkeypatch.setattr(download_module, "download", lambda *a, **k: pytest.fail("downloaded"))
    argv = ["--run", "2026112400", "--leads", "25", "--data-dir", str(tmp_path)]
    assert download_module.main(argv) == 1


@pytest.mark.parametrize("value", ["S", "SUL", "s1", "../x"])
def test_domain_must_be_two_letters(value, download_module):
    with pytest.raises(download_module.argparse.ArgumentTypeError):
        download_module.parse_domain(value)
    assert download_module.parse_domain(" ne ") == "NE"


def test_negative_or_non_integer_leads_rejected(download_module):
    for value in ("-3", "1.5", "x"):
        with pytest.raises(download_module.argparse.ArgumentTypeError):
            download_module.parse_lead(value)


def test_sample_warning_only_for_the_repository_data_folder(tmp_path, caplog, download_module):
    with caplog.at_level("WARNING"):
        download_module.main(["--run", "2026112400", "--dry-run", "--data-dir", str(tmp_path)])
    assert "is missing" not in caplog.text


def test_main_dry_run_with_explicit_run(capsys, download_module):
    assert download_module.main(["--run", "2026112400", "--leads", "0", "24", "--dry-run"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert len(out) == 2 and out[1].split(" -> ")[0].endswith("_2026112400_2026112500.grib2")
    assert download_module.main(["--run", "26-11-2026", "--dry-run"]) == 1


def test_sample_is_committed(download_module):
    from conftest import ROOT

    assert (ROOT / "data" / download_module.SAMPLE).exists()


def test_network_is_blocked_in_tests():
    with pytest.raises(RuntimeError, match="must not use the network"):
        socket.create_connection(("ftp.cptec.inpe.br", 443))
