import os
import shutil
import tempfile
from pathlib import Path
import pytest
from app.demo_data.generate_demo_data import generate_demo_files
from app.processors.factory import process_file, get_file_type
from app.services.query_parser import parse_query
from app.services.indexer import index_folder_background, indexing_status
from app.services.hybrid_search import search_documents
from app.db.base import SessionLocal, init_db
from app.db.models import Document, Chunk

@pytest.fixture(scope="session")
def setup_demo():
    temp_dir = tempfile.mkdtemp(prefix="refind_test_")
    generate_demo_files(temp_dir)
    init_db()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_processors(setup_demo):
    demo_dir = Path(setup_demo)
    
    # PDF
    pdf_res = process_file(str(demo_dir / "final2.pdf"))
    assert "BLE" in pdf_res["extracted_text"]
    assert "PostgreSQL" in pdf_res["extracted_text"]
    assert len(pdf_res["chunks"]) >= 2
    assert pdf_res["chunks"][0]["page_number"] == 1

    # DOCX
    docx_res = process_file(str(demo_dir / "report_v1.docx"))
    assert "Security" in docx_res["extracted_text"]
    assert len(docx_res["chunks"]) >= 1

    # PPTX
    pptx_res = process_file(str(demo_dir / "presentation2.pptx"))
    assert "Sensor" in pptx_res["extracted_text"]
    assert len(pptx_res["chunks"]) >= 1

    # PNG with companion metadata / OCR
    png_res = process_file(str(demo_dir / "IMG_2384.png"))
    assert "PostgreSQL" in png_res["extracted_text"] or "BLE" in png_res["extracted_text"]
    assert "Rahul" in png_res["extracted_text"]
    assert "February" in png_res["extracted_text"]

def test_query_parser():
    query = "Find the architecture PDF Rahul sent me around February. It had PostgreSQL and BLE."
    clues = parse_query(query)
    
    assert clues.file_type == "pdf"
    assert "Rahul" in clues.people
    assert "February" in clues.time_clues
    assert any("PostgreSQL" in t for t in clues.technologies)
    assert any("BLE" in t for t in clues.technologies)
    assert any("Architecture" in top for top in clues.topics)

    image_clues = parse_query("Find a screenshot related to PostgreSQL")
    assert image_clues.file_type == "image"
    assert "PostgreSQL" in image_clues.technologies

    name_clues = parse_query("Find the file that contains the name Eren")
    assert name_clues.keywords == ["Eren"]

def test_indexing_and_canonical_search(setup_demo):
    demo_dir = setup_demo
    
    # Run synchronous indexing of the test directory
    index_folder_background(demo_dir)
    assert indexing_status.processed_files >= 6

    db = SessionLocal()
    try:
        query = "Find the architecture PDF Rahul sent me around February. It had PostgreSQL and BLE."
        clues = parse_query(query)
        results = search_documents(query, clues, db, top_k=5)

        assert len(results) > 0
        top_result = results[0]
        
        # Verify final2.pdf is #1 best match
        assert "final2.pdf" in top_result.filename
        assert top_result.score >= 0.70
        assert top_result.score_label == "Strong match"
        
        # Verify matching clues contains the key memory clues
        clues_str = " ".join(top_result.matching_clues)
        assert "PDF" in clues_str
        assert "Rahul" in clues_str
        assert "February" in clues_str
        assert "PostgreSQL" in clues_str
        assert "BLE" in clues_str
        assert top_result.evidence
        assert any("PostgreSQL" in evidence.matched_text for evidence in top_result.evidence)

        image_results = search_documents(
            "Find a screenshot related to PostgreSQL",
            parse_query("Find a screenshot related to PostgreSQL"),
            db,
            top_k=5,
        )
        assert image_results
        assert image_results[0].file_type in {"png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff"}
        assert any(
            evidence.clue_name == "PostgreSQL" and "PostgreSQL" in evidence.matched_text
            for evidence in image_results[0].evidence
        )

        unrelated_image_results = search_documents(
            "Find a screenshot about a completely nonexistent subject",
            parse_query("Find a screenshot about a completely nonexistent subject"),
            db,
            top_k=5,
        )
        assert unrelated_image_results == []

        presentation_results = search_documents(
            "Find the presentation about sensors",
            parse_query("Find the presentation about sensors"),
            db,
            top_k=5,
        )
        assert presentation_results
        assert presentation_results[0].file_type == "pptx"

        filename_results = search_documents(
            "Find the presentation2 file",
            parse_query("Find the presentation2 file"),
            db,
            top_k=5,
        )
        # Filenames are metadata only; a filename-only query must not create
        # a content match or fabricated filename evidence.
        assert filename_results == []
    finally:
        db.close()
