from pathlib import Path

import pytest

from app.config import settings
from tests.conftest import make_token, upload

DATA_DIR = Path(__file__).resolve().parents[2] / "Tests data files"
HEADER = "Date;ExecutionTime;Value\n"


def upload_sample(client, name: str):
    return client.post("/Upload_file", files={"file": (name, (DATA_DIR / name).read_bytes(), "text/csv")})


def test_upload_and_aggregates(client):
    r = upload_sample(client, "Text Document _1.csv")
    assert r.status_code == 200
    assert r.text == "Data successful upload from Text Document _1.csv"

    values = client.get("/Get_data_from_table_Value").json()
    assert len(values) == 8
    assert set(values[0]) == {"id", "date", "executionTime", "value", "fileName"}

    [res] = client.get("/Get_data_from_table_Result").json()
    assert res["fileName"] == "Text Document _1.csv"
    assert res["startDate"].startswith("2025-08-02T10:15:30")
    assert res["timeDeltaSec"] == pytest.approx(90005.6)
    assert res["avgExecutionTime"] == 2.4125
    assert res["avgValue"] == 45.7
    assert res["medianValue"] == 45.4
    assert res["maxValue"] == 48.0
    assert res["minValue"] == 44.9


def test_reupload_replaces_data(client):
    upload_sample(client, "Text Document _1.csv")
    upload_sample(client, "Text Document _1.csv")
    assert len(client.get("/Get_data_from_table_Value").json()) == 8
    assert len(client.get("/Get_data_from_table_Result").json()) == 1


@pytest.mark.parametrize("name, body, fragment", [
    ("a.txt", HEADER + "2020-01-01T00:00:00Z;1;1\n2020-01-02T00:00:00Z;1;1", "Only files"),
    ("a.csv", "", "File is not selected"),
    ("a.csv", HEADER + "2020-01-01T00:00:00Z;1;1", "Error validation"),                     # 1 строка
    ("a.csv", HEADER + "bad;1;1\n2020-01-02T00:00:00Z;1;1", "Error validation"),            # дата
    ("a.csv", HEADER + "1999-12-31T00:00:00Z;1;1\n2020-01-02T00:00:00Z;1;1", "Error validation"),
    ("a.csv", HEADER + "2999-01-01T00:00:00Z;1;1\n2020-01-02T00:00:00Z;1;1", "Error validation"),
    ("a.csv", HEADER + "2020-01-01T00:00:00Z;x;1\n2020-01-02T00:00:00Z;1;1", "Error validation"),
    ("a.csv", HEADER + "2020-01-01T00:00:00Z;-1;1\n2020-01-02T00:00:00Z;1;1", "Error validation"),
    ("a.csv", HEADER + "2020-01-01T00:00:00Z;1\n2020-01-02T00:00:00Z;1;1", "Error validation"),
])
def test_upload_rejects_invalid(client, name, body, fragment):
    r = upload(client, name, body)
    assert r.status_code == 400
    assert fragment in r.text
    assert client.get("/Get_data_from_table_Value").json() == []


def test_upload_rejects_10000_rows(client):
    rows = "".join(f"2020-01-01T00:00:{i % 60:02d}Z;1;1\n" for i in range(10000))
    assert upload(client, "big.csv", HEADER + rows).status_code == 400


def test_filters(client):
    for n in range(1, 6):
        upload_sample(client, f"Text Document _{n}.csv")

    by_name = client.get("/Sort_by_filename", params={"name": "_3"}).json()
    assert [r["fileName"] for r in by_name] == ["Text Document _3.csv"]

    by_date = client.get("/Sort_by_StartDate", params={"startdate": "2025-08-02", "enddate": "2025-08-02"}).json()
    assert sorted(r["fileName"] for r in by_date) == ["Text Document _1.csv", "Text Document _2.csv"]

    by_avg = client.get("/Sort_by_avg-Value", params={"startValue": 45.7, "endValue": 45.7}).json()
    assert sorted(r["fileName"] for r in by_avg) == [
        "Text Document _1.csv", "Text Document _2.csv", "Text Document _4.csv", "Text Document _5.csv"]

    by_time = client.get("/Sort_by_avg-ExecutionTime", params={"startValue": 2.4, "endValue": 2.45}).json()
    assert sorted(r["fileName"] for r in by_time) == [
        "Text Document _1.csv", "Text Document _4.csv", "Text Document _5.csv"]


def test_last_ten_sorted_by_start_date(client):
    for n in range(1, 6):
        upload_sample(client, f"Text Document _{n}.csv")
    res = client.get("/Get_last_10_values_filter_from_filename", params={"Full_filename": "Text Document"}).json()
    assert len(res) == 5
    dates = [r["startDate"] for r in res]
    assert dates == sorted(dates)


def test_clear_resets_ids(client):
    upload_sample(client, "Text Document _2.csv")
    assert client.delete("/api/Table_actions/clear_table_Value").text == "All records deleted."
    assert client.delete("/api/Table_actions/clear_table_Result").text == "All records deleted."
    assert client.get("/Get_data_from_table_Value").json() == []
    upload_sample(client, "Text Document _2.csv")
    assert client.get("/Get_data_from_table_Value").json()[0]["id"] == 1
    assert client.get("/Get_data_from_table_Result").json()[0]["id"] == 1


def test_requires_valid_access_token(client):
    auth = client.headers.pop(settings.access_header_token_name)
    try:
        paths = ["/Get_data_from_table_Value", "/Get_data_from_table_Result", "/Sort_by_filename?name=a",
                 "/Get_last_10_values_filter_from_filename?Full_filename=a"]
        for p in paths:
            assert client.get(p).status_code == 401
        assert client.post("/Upload_file").status_code == 401
        assert client.delete("/api/Table_actions/clear_table_Value").status_code == 401
        for bad in (make_token("refresh"), make_token(secret="x" * 40), make_token(exp_delta=-10), "garbage"):
            assert client.get(paths[0], headers={settings.access_header_token_name: bad}).status_code == 401
        assert client.get("/health").status_code == 200
    finally:
        client.headers[settings.access_header_token_name] = auth
