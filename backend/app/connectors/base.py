from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseDataSource(ABC):
    """
    Abstract interface for all ReFind data connectors.
    Enables future integrations (Gmail, Google Drive, OneDrive, Browser History)
    to plug directly into the indexing and retrieval pipeline.
    """

    @abstractmethod
    def get_source_name(self) -> str:
        """Returns the human-readable identifier of the data source."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Checks if required permissions/tokens are available."""
        pass

    @abstractmethod
    def scan(self, target: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discovers indexable items from this data source."""
        pass
