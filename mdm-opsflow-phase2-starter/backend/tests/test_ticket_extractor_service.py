from app.services.ticket_extractor import extract_ticket_candidates, extract_ticket_preview


def test_extract_ticket_candidates_parses_haul_slip_style_fields() -> None:
    raw_text = (
        "M&J TWINS HAULING\n"
        "DATE: 6-16-26\n"
        "TRUCK# MJ11\n"
        "JOB: Harvest District\n"
        "COMPANY HAULING FOR: Wellons\n"
        "START TIME: 7:00 AM\n"
        "FINISH TIME: 6:00 PM\n"
        "PRODUCT: DIRT\n"
        "Foreman's signature: 3 loads\n"
    )

    candidates = extract_ticket_candidates(raw_text, original_filename="haul_slip.pdf")

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate["date"] == "6-16-26"
    assert candidate["truck"].startswith("MJ11")
    assert candidate["job"].lower().startswith("harvest")
    assert candidate["company_hauling_for"].lower().startswith("wellons")
    assert candidate["start_time"].lower().startswith("7:00")
    assert candidate["finish_time"].lower().startswith("6:00")
    assert candidate["material"].lower().startswith("dirt")
    assert candidate["number_of_loads"] == "3"


def test_extract_ticket_candidates_splits_repeated_date_blocks() -> None:
    raw_text = (
        "DATE: 6/16/26\nTRUCK# MJ11\nJOB: Harvest District\nForeman signature: 3 loads\n"
        "DATE: 6/16/26\nTRUCK# MJ08\nJOB: Harvest Dist\nForeman signature: 13 loads\n"
    )

    candidates = extract_ticket_candidates(raw_text, original_filename="multi_slip.jpg")

    assert len(candidates) >= 2
    load_values = {candidate.get("number_of_loads", "") for candidate in candidates}
    assert "3" in load_values
    assert "13" in load_values


def test_extract_ticket_preview_returns_summary_for_haul_slip() -> None:
    raw_text = "DATE: 6-16-26\nTRUCK# MJ11\nPRODUCT: DIRT\nForeman signature: 3 loads\n"

    entities, summary, confidence = extract_ticket_preview(raw_text, original_filename="ticket_hauling.jpg")

    assert entities.get("truck", "").startswith("MJ11")
    assert entities.get("material", "").lower().startswith("dirt")
    assert entities.get("number_of_loads") == "3"
    assert confidence > 0
    assert summary
