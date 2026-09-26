import re
import logging
from typing import List, Optional
from app.schemas.search import QueryClues
from app.core.config import settings

logger = logging.getLogger("refind.services.query_parser")

# Predefined common dictionaries for high-precision entity extraction
KNOWN_FILE_TYPES = {
    "pdf": "pdf",
    # "document" is generic and must not force PDF-only results.
    "docx": "docx",
    "doc": "docx",
    "word": "docx",
    "pptx": "pptx",
    "ppt": "pptx",
    "slides": "pptx",
    "presentation": "pptx",
    "deck": "pptx",
    "txt": "txt",
    "text": "txt",
    "notes": "txt",
    "image": "png",
    "photo": "png",
    "picture": "png",
    "screenshot": "png",
    "png": "png",
    "jpg": "jpg",
    "jpeg": "jpeg",
    "webp": "webp",
    "gif": "gif",
    "bmp": "bmp",
    "tiff": "tiff",
    "heic": "heic",
    "heif": "heif",
}

MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec"
]

COMMON_TECH = [
    "postgresql", "postgres", "ble", "bluetooth", "bluetooth low energy",
    "python", "fastapi", "react", "next.js", "nextjs", "docker", "redis",
    "mysql", "sqlite", "graphql", "rest", "api", "aws", "azure", "iot",
    "zigbee", "wi-fi", "wifi", "kafka", "mongodb", "tailwind", "typescript",
    "hadoop", "hdfs", "mapreduce", "hive", "pig", "machine learning", "deep learning",
    "artificial intelligence", "database", "databases"
]

COMMON_TOPICS = [
    "architecture", "system design", "diagram", "schematic", "marketing",
    "financial", "budget", "meeting notes", "minutes", "roadmap", "proposal",
    "security", "audit", "pitch", "specification", "spec", "overview", "sprint",
    "ethics", "ai ethics", "sustainability", "renewable energy", "analytics"
]

STOPWORDS = {
    "find", "the", "me", "a", "an", "around", "in", "on", "at", "about",
    "sent", "shared", "gave", "show", "get", "with", "it", "had", "have",
    "has", "that", "this", "which", "and", "or", "from", "to", "by", "of",
    "for", "some", "my", "our", "their", "where", "what", "who", "when",
    "related", "thing", "things", "one", "screenshot", "image", "photo", "picture",
    "file", "pdf", "docx", "doc", "pptx", "ppt", "txt",
    "presentation", "slides", "deck", "document", "report", "word",
    "contains", "contain", "name",
    "i", "you", "we", "he", "she", "they", "wrote", "written",
    "containing", "used", "college", "downloaded"
}

def parse_query_local(query: str) -> QueryClues:
    """
    100% deterministic, instant, local natural-language query parser.
    Extracts structured memory clues, file types, entities, topics, and keywords
    without external API latency, rate limits, or network failures.
    """
    clean_q = query.strip()
    words = re.findall(r"[A-Za-z0-9]+", clean_q)
    lower_q = clean_q.lower()

    detected_file_type: Optional[str] = None
    detected_topics: List[str] = []
    detected_people: List[str] = []
    detected_technologies: List[str] = []
    detected_time_clues: List[str] = []
    detected_keywords: List[str] = []

    # 1. Detect file type. Natural image descriptions mean any supported
    # image format, not only PNG.
    if re.search(r"\b(?:image|photo|picture|screenshot)\b", lower_q):
        detected_file_type = "image"

    for token, ftype in KNOWN_FILE_TYPES.items():
        pattern = r"\b" + re.escape(token) + r"\b"
        if re.search(pattern, lower_q):
            if detected_file_type != "image" or ftype not in {"png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff", "heic", "heif"}:
                detected_file_type = ftype
            break

    # 2. Detect technologies
    for tech in COMMON_TECH:
        pattern = r"\b" + re.escape(tech) + r"\b"
        if re.search(pattern, lower_q):
            if tech in ("postgresql", "postgres"):
                detected_technologies.append("PostgreSQL")
            elif tech in ("ble", "bluetooth low energy"):
                detected_technologies.append("BLE")
            elif tech in ("next.js", "nextjs"):
                detected_technologies.append("Next.js")
            elif tech in ("database", "databases"):
                detected_technologies.append("Database")
            elif tech in ("machine learning",):
                detected_technologies.append("Machine Learning")
            elif tech in ("artificial intelligence",):
                detected_technologies.append("Artificial Intelligence")
            else:
                detected_technologies.append(tech.title())

    # 3. Detect topics
    for topic in COMMON_TOPICS:
        pattern = r"\b" + re.escape(topic) + r"\b"
        if re.search(pattern, lower_q):
            detected_topics.append(topic.title())

    # 4. Detect time clues (months, years, relative times)
    for month in MONTHS:
        pattern = r"\b" + re.escape(month) + r"\b"
        if re.search(pattern, lower_q):
            detected_time_clues.append(month.title())

    year_match = re.findall(r"\b(20[2-3][0-9])\b", clean_q)
    for y in year_match:
        detected_time_clues.append(y)

    for rel in ["yesterday", "last week", "last month", "recently"]:
        if rel in lower_q:
            detected_time_clues.append(rel.title())

    # 5. Detect people
    name_patterns = [
        r"\b(?:sent\s+by|from|with|to)\s+([A-Z][a-z]+)\b",
        r"\b([A-Z][a-z]+)\s+sent\s+me\b",
        r"\b([A-Z][a-z]+)\s+shared\b",
    ]
    for np in name_patterns:
        matches = re.findall(np, clean_q)
        for m in matches:
            if m.lower() not in STOPWORDS and m.lower() not in MONTHS:
                if m not in detected_people:
                    detected_people.append(m)

    if not detected_people:
        for w in words:
            if len(w) > 1 and w[0].isupper() and w.lower() not in STOPWORDS and w.lower() not in MONTHS:
                if w.lower() not in [t.lower() for t in detected_technologies] and w.lower() not in [top.lower() for top in detected_topics]:
                    if w not in ["Find", "The", "Show", "Search", "Where"]:
                        detected_people.append(w)

    # 6. Extract meaningful subject keywords
    for w in words:
        wl = w.lower()
        if wl not in STOPWORDS and wl not in KNOWN_FILE_TYPES and len(wl) > 2:
            if wl not in [k.lower() for k in detected_keywords]:
                detected_keywords.append(w)

    # If all tokens were filtered out, preserve non-empty terms from query
    if not detected_keywords:
        for w in words:
            if len(w) > 1 and w.lower() not in {"the", "a", "an", "in", "on", "at"}:
                detected_keywords.append(w)

    return QueryClues(
        raw_query=clean_q,
        intent="find_content",
        file_type=detected_file_type,
        topics=list(dict.fromkeys(detected_topics)),
        people=list(dict.fromkeys(detected_people)),
        technologies=list(dict.fromkeys(detected_technologies)),
        time_clues=list(dict.fromkeys(detected_time_clues)),
        keywords=list(dict.fromkeys(detected_keywords)),
    )

def parse_query(query: str) -> QueryClues:
    """
    Main entry point for query understanding.
    Runs 100% locally by default: completely deterministic, instantaneous,
    and 100% immune to external API timeouts, disconnections, or 404 model errors.
    """
    return parse_query_local(query)
