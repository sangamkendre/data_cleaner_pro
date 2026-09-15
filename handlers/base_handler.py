"""
Base File Handler Interface.
All format-specific file handlers inherit from BaseHandler.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
import pandas as pd


class BaseHandler(ABC):
    @abstractmethod
    def can_handle(self, filename: str) -> bool:
        """Returns True if this handler can process the given file extension/format."""
        pass

    @abstractmethod
    def read(self, file_path: str, **kwargs) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Reads data from file_path into a pandas DataFrame.
        Returns:
            Tuple[pd.DataFrame, Dict[str, Any]]: (dataframe, metadata)
        """
        pass

    def get_sheets(self, file_path: str) -> list[str]:
        """Returns list of sheet or table names if applicable, else empty list."""
        return []
