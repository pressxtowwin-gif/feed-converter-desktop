from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl")
from openpyxl import load_workbook

from core.excel_table import create_excel_from_feed_rows, update_excel_from_feed_rows


def _feed_rows(count: int = 5) -> list[dict[str, str]]:
    return [
        {
            "ID квартиры": str(idx),
            "Номер квартиры": f"{100 + idx}",
            "Цена": str(idx * 1000),
            "Описание": f"description {idx}",
            "Планировка": f"plan-{idx}",
            "Пользовательское": f"manual {idx}",
        }
        for idx in range(1, count + 1)
    ]


def _columns() -> list[str]:
    return ["ID квартиры", "Номер квартиры", "Цена", "Описание", "Планировка", "Пользовательское"]


def test_update_counts_restored_feed_controlled_cells(tmp_path: Path) -> None:
    columns = ["ID квартиры", "Номер квартиры", "Цена", "Описание", "Планировка", "Пользовательское"]
    original_rows = [
        {
            "ID квартиры": "1",
            "Номер квартиры": "101",
            "Цена": "1000",
            "Описание": "old description",
            "Планировка": "plan-a",
            "Пользовательское": "manual note",
        },
        {
            "ID квартиры": "2",
            "Номер квартиры": "102",
            "Цена": "2000",
            "Описание": "description 2",
            "Планировка": "plan-b",
            "Пользовательское": "manual note 2",
        },
    ]
    excel_path = tmp_path / "lots.xlsx"
    create_excel_from_feed_rows(original_rows, columns, excel_path)

    wb = load_workbook(excel_path)
    ws = wb.active
    # Existing row 1: clear/change dynamic feed-controlled cells.
    ws["C2"] = None
    ws["D2"] = "user changed dynamic description"
    # Existing row 2: clear a manual/static field. It is restored only because it is blank.
    ws["B3"] = None
    # Manual custom field must stay untouched and not be counted.
    ws["F3"] = "edited manual note"
    wb.save(excel_path)

    feed_rows = [
        {
            "ID квартиры": "1",
            "Номер квартиры": "101",
            "Цена": "1000",
            "Описание": "old description",
            "Планировка": "plan-a",
            "Пользовательское": "manual note",
        },
        {
            "ID квартиры": "2",
            "Номер квартиры": "102",
            "Цена": "2000",
            "Описание": "description 2",
            "Планировка": "plan-b",
            "Пользовательское": "manual note 2",
        },
    ]
    output_path = tmp_path / "updated.xlsx"

    result = update_excel_from_feed_rows(feed_rows, columns, excel_path, output_path)

    assert result["updated_cells"] == 3
    assert result["updated_apartments"] == 2
    assert result["added"] == 0
    assert result["deleted"] == 0
    assert result["excel_rows_before"] == 2
    assert result["excel_rows_after"] == 2

    updated = load_workbook(output_path).active
    assert updated["C2"].value == "1000"
    assert updated["D2"].value == "old description"
    assert updated["B3"].value == "102"
    assert updated["F3"].value == "edited manual note"


def test_update_does_not_count_unchanged_existing_rows(tmp_path: Path) -> None:
    columns = ["ID квартиры", "Цена", "Описание"]
    rows = [{"ID квартиры": "1", "Цена": "1000", "Описание": "same"}]
    excel_path = tmp_path / "lots.xlsx"
    output_path = tmp_path / "updated.xlsx"
    create_excel_from_feed_rows(rows, columns, excel_path)

    result = update_excel_from_feed_rows(rows, columns, excel_path, output_path)

    assert result["updated_cells"] == 0
    assert result["updated_apartments"] == 0
    assert result["added"] == 0
    assert result["deleted"] == 0


def test_clearing_cells_in_existing_rows_counts_updated_apartments_not_added(tmp_path: Path) -> None:
    columns = _columns()
    rows = _feed_rows(5)
    excel_path = tmp_path / "lots.xlsx"
    output_path = tmp_path / "updated.xlsx"
    create_excel_from_feed_rows(rows, columns, excel_path)

    wb = load_workbook(excel_path)
    ws = wb.active
    ws["C2"] = None
    ws["D3"] = None
    ws["E4"] = "changed plan"
    wb.save(excel_path)

    result = update_excel_from_feed_rows(rows, columns, excel_path, output_path)

    assert result["updated_apartments"] == 3
    assert result["updated_cells"] == 3
    assert result["added"] == 0
    assert result["deleted"] == 0
    assert result["feed_rows"] == 5
    assert result["excel_rows_before"] == 5
    assert result["excel_rows_after"] == 5


def test_deleting_full_rows_by_apartment_id_counts_as_added_back(tmp_path: Path) -> None:
    columns = _columns()
    rows = _feed_rows(5)
    excel_path = tmp_path / "lots.xlsx"
    output_path = tmp_path / "updated.xlsx"
    create_excel_from_feed_rows(rows, columns, excel_path)

    wb = load_workbook(excel_path)
    ws = wb.active
    ws.delete_rows(3, 2)
    wb.save(excel_path)

    result = update_excel_from_feed_rows(rows, columns, excel_path, output_path)

    assert result["added"] == 2
    assert result["added_ids"] == ["2", "3"]
    assert result["deleted"] == 0
    assert result["excel_rows_before"] == 3
    assert result["excel_rows_after"] == 5


def test_changing_price_counts_price_changes_and_updated_apartments(tmp_path: Path) -> None:
    columns = _columns()
    rows = _feed_rows(4)
    excel_path = tmp_path / "lots.xlsx"
    output_path = tmp_path / "updated.xlsx"
    create_excel_from_feed_rows(rows, columns, excel_path)

    wb = load_workbook(excel_path)
    ws = wb.active
    ws["C2"] = "999"
    ws["C4"] = "2999"
    wb.save(excel_path)

    result = update_excel_from_feed_rows(rows, columns, excel_path, output_path)

    assert result["prices_changed"] == 2
    assert len(result["price_changes"]) == 2
    assert result["updated_apartments"] >= 2
    assert result["updated_cells"] >= 2
    assert result["added"] == 0


def test_unchanged_file_counts_no_updates_or_additions(tmp_path: Path) -> None:
    columns = _columns()
    rows = _feed_rows(4)
    excel_path = tmp_path / "lots.xlsx"
    output_path = tmp_path / "updated.xlsx"
    create_excel_from_feed_rows(rows, columns, excel_path)

    result = update_excel_from_feed_rows(rows, columns, excel_path, output_path)

    assert result["updated_apartments"] == 0
    assert result["updated_cells"] == 0
    assert result["added"] == 0
    assert result["deleted"] == 0
