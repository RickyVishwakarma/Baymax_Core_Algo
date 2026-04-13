from __future__ import annotations

import csv
import logging
import os
from pathlib import Path
from urllib import request

logger = logging.getLogger(__name__)

class DhanInstrumentManager:
    """Manages the Dhan Scrip Master for symbol to SecurityId mapping."""
    
    SCRIP_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"
    CACHE_FILE = "dhan_scrip_master.csv"

    def __init__(self, cache_dir: str = ".data"):
        self.cache_path = Path(cache_dir) / self.CACHE_FILE
        self.cache_dir = Path(cache_dir)
        self._mapping: dict[str, str] = {}
        self._initialized = False

    def ensure_ready(self, force_download: bool = False) -> None:
        """Downloads the scrip master if missing or forced."""
        if self._initialized and not force_download:
            return

        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True)

        if not self.cache_path.exists() or force_download:
            logger.info("Downloading Dhan Scrip Master from %s ...", self.SCRIP_MASTER_URL)
            try:
                request.urlretrieve(self.SCRIP_MASTER_URL, self.cache_path)
                logger.info("Dhan Scrip Master downloaded successfully.")
            except Exception as e:
                logger.error("Failed to download Dhan Scrip Master: %s", e)
                raise RuntimeError(f"Could not download Dhan instrumentation data: {e}") from e

        self._load_mapping()
        self._initialized = True

    def _load_mapping(self) -> None:
        """Parses the CSV into a lookup dictionary."""
        logger.info("Loading Dhan symbol mapping into memory...")
        mapping = {}
        try:
            with open(self.cache_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    exch = row.get("SEM_EXM_EXCH_ID", "").upper()
                    symbol = row.get("SEM_TRADING_SYMBOL", "")
                    sec_id = row.get("SEM_SMST_SECURITY_ID", "")
                    instrument_type = row.get("SEM_INSTRUMENT_NAME", "")
                    
                    if exch and symbol and sec_id:
                        key = f"{exch}:{symbol}"
                        # Map internal "NSE" to Dhan order-friendly "NSE_EQ" etc.
                        segment = f"{exch}_EQ" if instrument_type == "EQUITY" else f"{exch}_FNO"
                        # Fallback for complex segments or if SEM_INSTRUMENT_NAME varies
                        if exch == "NSE" and instrument_type == "EQUITY": segment = "NSE_EQ"
                        elif exch == "BSE" and instrument_type == "EQUITY": segment = "BSE_EQ"

                        mapping[key] = {
                            "security_id": sec_id,
                            "segment": segment
                        }
        except Exception as e:
            logger.error("Failed to parse Dhan Scrip Master: %s", e)
            raise RuntimeError(f"Failed to load Dhan instrumentation: {e}") from e

        self._mapping = mapping
        logger.info("Loaded %d Dhan instruments.", len(self._mapping))

    def get_security_id(self, exchange: str, symbol: str) -> str:
        """Returns the SecurityId for a given exchange and symbol."""
        data = self.get_instrument_metadata(exchange, symbol)
        return data["security_id"]

    def get_instrument_metadata(self, exchange: str, symbol: str) -> dict[str, str]:
        """Returns metadata (security_id, segment) for a given symbol."""
        self.ensure_ready()
        key = f"{exchange.upper()}:{symbol.upper()}"
        data = self._mapping.get(key)
        if not data:
            raise KeyError(f"Symbol {key} not found in Dhan Scrip Master.")
        return data
