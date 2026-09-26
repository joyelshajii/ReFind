import os
import shutil
import tempfile
from pathlib import Path
import pytest
from app.db.base import SessionLocal, init_db
from app.db.models import Document, Chunk
from app.processors.pdf_processor import process_pdf
from app.processors.docx_processor import process_docx
from app.processors.pptx_processor import process_pptx
from app.processors.txt_processor import process_txt
from app.services.chunking_service import chunk_text
from app.services.embedding_service import embed_text, cosine_similarity
from app.services.reranker_service import reranker_service
from app.services.gemini_service import gemini_service
from app.services.query_parser import parse_query, parse_query_local
from app.services.indexer import index_single_file, compute_file_hash
from app.services.hybrid_search import search_documents

@pytest.fixture(scope="module")
def setup_test_env():
    temp_dir = Path(tempfile.mkdtemp(prefix="refind_ai_test_"))
    init_db()
    
    # 1. Create test TXT document
    txt_path = temp_dir / "sustainability_report.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("""Global Sustainability and Renewable Energy Review 2026.
This annual report reviews solar energy adoption, carbon offset methodologies, and corporate sustainability frameworks.
Key goals focus on net-zero emissions and supply chain green logistics.""")

    # 2. Create test DB document
    db_path = temp_dir / "database_architecture.txt"
    with open(db_path, "w", encoding="utf-8") as f:
        f.write("""Modern Distributed Database Systems and PostgreSQL Internals.
Topics covered include write-ahead logging, indexing strategies, vector embeddings with pgvector, and relational schema normalization.
Authored by Alex in March 2026.""")

    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_chunking_service():
    sample_text = ("Paragraph one discusses AI concepts.\n\n" * 10) + ("Paragraph two discusses database indexing.\n\n" * 10)
    chunks = chunk_text(sample_text, chunk_size=300, chunk_overlap=50)
    assert len(chunks) > 1
    assert all(len(c) > 0 for c in chunks)

def test_embedding_generation_and_cosine():
    v1 = embed_text("Machine learning and deep neural networks")
    v2 = embed_text("Deep learning and artificial intelligence algorithms")
    v3 = embed_text("Cooking recipes for Italian pizza and pasta")

    assert len(v1) == 768
    assert len(v2) == 768
    assert len(v3) == 768

    sim_ai = cosine_similarity(v1, v2)
    sim_diff = cosine_similarity(v1, v3)

    assert sim_ai > sim_diff

def test_unchanged_document_caching(setup_test_env):
    temp_dir = setup_test_env
    txt_path = temp_dir / "sustainability_report.txt"
    db = SessionLocal()
    try:
        doc1 = index_single_file(str(txt_path), db)
        assert doc1.file_hash != ""

        # Second indexing call must detect matching hash
        doc2 = index_single_file(str(txt_path), db)
        assert doc1.id == doc2.id
    finally:
        db.close()

def test_gemini_query_parsing_and_fallback():
    # Test natural query parsing
    query = "Find the file containing the word sustainability"
    clues = parse_query(query)
    assert any("sustainability" in k.lower() for k in clues.keywords)

    # Test fallback query parsing
    local_clues = parse_query_local("Find that PDF I downloaded last month about AI ethics.")
    assert local_clues.file_type == "pdf"
    assert "last month" in [t.lower() for t in local_clues.time_clues]

def test_jina_reranker_and_fallback():
    query = "PostgreSQL database architecture"
    docs = [
        "A recipe for chocolate cake with strawberry frosting.",
        "PostgreSQL performance tuning with btree and gin indexes.",
        "A guide to planting flowers in spring."
    ]
    # Reranking live or fallback test
    reranked = reranker_service.rerank(query, docs, top_n=2)
    if reranked is not None:
        assert len(reranked) == 2
        # The database document (index 1) should rank top
        assert reranked[0]["index"] == 1

def test_hybrid_search_scoring_and_explanation(setup_test_env):
    temp_dir = setup_test_env
    db = SessionLocal()
    try:
        # Index both test files
        index_single_file(str(temp_dir / "sustainability_report.txt"), db)
        index_single_file(str(temp_dir / "database_architecture.txt"), db)

        # Test natural language queries specified in requirements:
        # 1. "Find the file containing the word sustainability."
        q1 = "Find the file containing the word sustainability."
        clues1 = parse_query(q1)
        results1 = search_documents(q1, clues1, db, top_k=3)
        assert len(results1) > 0
        assert "sustainability_report.txt" in results1[0].filename

        # 2. "Find that document where I wrote about databases."
        q2 = "Find that document where I wrote about databases."
        clues2 = parse_query(q2)
        results2 = search_documents(q2, clues2, db, top_k=3)
        assert len(results2) > 0
        assert "database_architecture.txt" in results2[0].filename
    finally:
        db.close()
