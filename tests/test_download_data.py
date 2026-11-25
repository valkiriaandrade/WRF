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

    with pytest.raises(download_module.DownloadError, match="keeps only recent runs"):
        download_module.fetch("https://x/old.grib2", tmp_path / "old.grib2", opener=opener)


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
