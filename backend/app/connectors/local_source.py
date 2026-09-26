import os
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.connectors.base import BaseDataSource
from app.processors.factory import SUPPORTED_EXTENSIONS

logger = logging.getLogger("refind.connectors.local_source")

class LocalFileSource(BaseDataSource):
    """
    Ingests and monitors local filesystem directories and uploaded files.
    """

    def get_source_name(self) -> str:
        return "Local Files"

    def is_configured(self) -> bool:
        return True

    def scan(self, target: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Recursively scans target directory for supported file types.
        """
        if not target:
            return []

        folder = Path(target)
        if not folder.exists() or not folder.is_dir():
            return []

        discovered: List[Dict[str, Any]] = []

        for root, _, files in os.walk(folder):
            for file in files:
                p = Path(root) / file
                ext = p.suffix.lower()
                if ext in SUPPORTED_EXTENSIONS:
                    try:
                        stat = p.stat()
                        discovered.append({
                            "filename": p.name,
                            "filepath": str(p.resolve()),
                            "file_type": SUPPORTED_EXTENSIONS[ext],
                            "file_size": stat.st_size,
                            "created_at": datetime.fromtimestamp(stat.st_ctime),
                            "modified_at": datetime.fromtimestamp(stat.st_mtime),
                            "source": "local"
                        })
                    except OSError as error:
                        logger.warning("Unable to read file metadata for %s: %s", p, error)
                        continue

        return discovered
