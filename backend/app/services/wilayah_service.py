"""Wilayah service for loading and querying region data."""

import csv
import os
from pathlib import Path
from typing import Any

from app.models.wilayah import Wilayah, WilayahLevel, WilayahSearchResult


class WilayahService:
    """Service for wilayah (region) data operations.
    
    Loads the Permendagri 72/2019 wilayah data from CSV into memory
    and provides fast lookup by level and search functionality.
    """
    
    def __init__(self):
        """Initialize wilayah service with empty indexes."""
        self._data: dict[str, Wilayah] = {}
        self._by_level: dict[WilayahLevel, list[str]] = {
            WilayahLevel.PROVINCE: [],
            WilayahLevel.DISTRICT: [],
            WilayahLevel.SUBDISTRICT: [],
            WilayahLevel.VILLAGE: [],
        }
        self._loaded = False
    
    def _get_csv_path(self) -> Path:
        """Get path to wilayah CSV file."""
        # Look in app/data first, then fall back to data directory
        paths = [
            Path(__file__).parent.parent / "data" / "wilayah.csv",
            Path(__file__).parent.parent.parent / "data" / "wilayah.csv",
            Path(os.getcwd()) / "app" / "data" / "wilayah.csv",
        ]
        for path in paths:
            if path.exists():
                return path
        raise FileNotFoundError("wilayah.csv not found in expected locations")
    
    def _determine_level(self, code: str) -> WilayahLevel:
        """Determine wilayah level from code format.
        
        Code format (dots separate hierarchy):
        - 2 digits: Province (e.g., "11", "33")
        - 5 chars (2.2): District/Kabupaten (e.g., "11.01", "33.26")
        - 8 chars (2.2.2): Subdistrict/Kecamatan (e.g., "33.26.16")
        - 13 chars (2.2.2.4): Village/Kelurahan (e.g., "33.26.16.1001")
        """
        # Remove dots for length calculation
        clean_code = code.replace(".", "")
        length = len(clean_code)
        
        if length == 2:
            return WilayahLevel.PROVINCE
        elif length == 4:
            return WilayahLevel.DISTRICT
        elif length == 6:
            return WilayahLevel.SUBDISTRICT
        elif length >= 7:  # 7 or more digits (desa/kelurahan can vary)
            return WilayahLevel.VILLAGE
        else:
            raise ValueError(f"Invalid wilayah code format: {code}")
    
    def _get_parent_code(self, code: str, level: WilayahLevel) -> str | None:
        """Get parent wilayah code."""
        if level == WilayahLevel.PROVINCE:
            return None
        
        parts = code.split(".")
        
        if level == WilayahLevel.DISTRICT:
            # Parent is province (first part)
            return parts[0]
        elif level == WilayahLevel.SUBDISTRICT:
            # Parent is district (first two parts)
            return f"{parts[0]}.{parts[1]}"
        elif level == WilayahLevel.VILLAGE:
            # Parent is subdistrict (first three parts)
            return f"{parts[0]}.{parts[1]}.{parts[2]}"
        
        return None
    
    def load_data(self) -> None:
        """Load wilayah data from CSV into memory."""
        if self._loaded:
            return
        
        csv_path = self._get_csv_path()
        
        with open(csv_path, "r", encoding="utf-8") as f:
            # CSV has no header, read directly: code,name
            reader = csv.reader(f)
            for row in reader:
                if len(row) != 2:
                    continue
                code = row[0].strip()
                name = row[1].strip()
                
                level = self._determine_level(code)
                
                wilayah = Wilayah(
                    code=code,
                    name=name,
                    level=level,
                )
                
                self._data[code] = wilayah
                self._by_level[level].append(code)
        
        # Sort codes for consistent ordering
        for level in self._by_level:
            self._by_level[level].sort()
        
        self._loaded = True
    
    def get_provinces(self) -> list[Wilayah]:
        """Get all provinces (34 total)."""
        self.load_data()
        return [self._data[code] for code in self._by_level[WilayahLevel.PROVINCE]]
    
    def get_districts(self, province_code: str) -> list[Wilayah]:
        """Get districts (kabupaten/kota) for a province.
        
        Args:
            province_code: 2-digit province code (e.g., "33")
        
        Returns:
            List of districts in that province.
        """
        self.load_data()
        
        # Normalize code
        province_code = province_code.strip()
        
        result = []
        for code in self._by_level[WilayahLevel.DISTRICT]:
            # District codes start with province code
            if code.startswith(province_code + "."):
                result.append(self._data[code])
        
        return result
    
    def get_subdistricts(self, district_code: str) -> list[Wilayah]:
        """Get subdistricts (kecamatan) for a district.
        
        Args:
            district_code: District code (e.g., "33.26")
        
        Returns:
            List of subdistricts in that district.
        """
        self.load_data()
        
        # Normalize code
        district_code = district_code.strip()
        
        result = []
        for code in self._by_level[WilayahLevel.SUBDISTRICT]:
            # Subdistrict codes start with district code
            if code.startswith(district_code + "."):
                result.append(self._data[code])
        
        return result
    
    def get_villages(self, subdistrict_code: str) -> list[Wilayah]:
        """Get villages (kelurahan/desa) for a subdistrict.
        
        Args:
            subdistrict_code: Subdistrict code (e.g., "33.26.16")
        
        Returns:
            List of villages in that subdistrict.
        """
        self.load_data()
        
        # Normalize code
        subdistrict_code = subdistrict_code.strip()
        
        result = []
        for code in self._by_level[WilayahLevel.VILLAGE]:
            # Village codes start with subdistrict code
            if code.startswith(subdistrict_code + "."):
                result.append(self._data[code])
        
        return result
    
    def _get_full_path(self, code: str, level: WilayahLevel) -> str:
        """Generate full hierarchical path for a wilayah."""
        parts = []
        
        code_parts = code.split(".")
        
        # Province
        province_code = code_parts[0]
        if province_code in self._data:
            parts.append(self._title_case(self._data[province_code].name))
        
        # District (if applicable)
        if level in (WilayahLevel.DISTRICT, WilayahLevel.SUBDISTRICT, WilayahLevel.VILLAGE):
            district_code = f"{code_parts[0]}.{code_parts[1]}"
            if district_code in self._data:
                parts.append(self._title_case(self._data[district_code].name))
        
        # Subdistrict (if applicable)
        if level in (WilayahLevel.SUBDISTRICT, WilayahLevel.VILLAGE):
            subdistrict_code = f"{code_parts[0]}.{code_parts[1]}.{code_parts[2]}"
            if subdistrict_code in self._data:
                parts.append(self._title_case(self._data[subdistrict_code].name))
        
        # Village (if applicable)
        if level == WilayahLevel.VILLAGE:
            if code in self._data:
                parts.append(self._title_case(self._data[code].name))
        
        return " > ".join(parts)
    
    def _title_case(self, name: str) -> str:
        """Convert name to title case for display."""
        # Handle common abbreviations
        words = name.split()
        result = []
        
        for word in words:
            upper_word = word.upper()
            # Keep common Indonesian administrative abbreviations uppercase
            if upper_word in ("KAB.", "KOTA", "KEC.", "DESA", "KEL.", "DUSUN"):
                result.append(upper_word if upper_word.endswith(".") else upper_word.title())
            else:
                result.append(word.title())
        
        return " ".join(result)
    
    def search(self, query: str, limit: int = 50) -> list[WilayahSearchResult]:
        """Search wilayah by name (case-insensitive).
        
        Args:
            query: Search query string
            limit: Maximum results to return (default 50)
        
        Returns:
            List of matching wilayah with full paths.
        """
        self.load_data()
        
        query_lower = query.lower().strip()
        results = []
        
        for code, wilayah in self._data.items():
            if query_lower in wilayah.name.lower():
                parent_code = self._get_parent_code(code, wilayah.level)
                full_path = self._get_full_path(code, wilayah.level)
                
                result = WilayahSearchResult(
                    code=wilayah.code,
                    name=wilayah.name,
                    level=wilayah.level,
                    full_path=full_path,
                    parent_code=parent_code,
                )
                results.append(result)
                
                if len(results) >= limit:
                    break
        
        return results
    
    def get_by_code(self, code: str) -> Wilayah | None:
        """Get a wilayah by its code.
        
        Args:
            code: Wilayah code
        
        Returns:
            Wilayah if found, None otherwise.
        """
        self.load_data()
        return self._data.get(code.strip())
    
    def get_stats(self) -> dict[str, Any]:
        """Get statistics about loaded data."""
        self.load_data()
        return {
            "total": len(self._data),
            "provinces": len(self._by_level[WilayahLevel.PROVINCE]),
            "districts": len(self._by_level[WilayahLevel.DISTRICT]),
            "subdistricts": len(self._by_level[WilayahLevel.SUBDISTRICT]),
            "villages": len(self._by_level[WilayahLevel.VILLAGE]),
        }


# Global service instance
wilayah_service = WilayahService()
