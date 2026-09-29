"""Excel parser for XLSX files."""

import os
from typing import Dict, Any
from datetime import datetime, timezone
import pandas as pd
from loguru import logger

from parsers.base_parser import BaseParser
from models import ParsedDocument


class ExcelParser(BaseParser):
    """Parser for Excel spreadsheets."""
    
    def __init__(self):
        super().__init__()
        self.supported_extensions = {'.xlsx', 'xlsx', '.xls', 'xls', '.csv', 'csv'}
        self.max_rows_per_sheet = 10000
    
    async def parse(
        self, 
        file_path: str,
        sheet_names: list = None,
        **kwargs
    ) -> ParsedDocument:
        """
        Parse Excel/CSV file.
        
        Args:
            file_path: Path to Excel/CSV file
            sheet_names: Specific sheets to parse (None = all sheets)
            
        Returns:
            ParsedDocument with extracted content
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Excel file not found: {file_path}")
        
        start_time = datetime.now(timezone.utc)
        file_size = os.path.getsize(file_path)
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            logger.info(f"Starting Excel/CSV parsing ({file_size:,} bytes)")
            
            content_parts = []
            metadata = {
                "file_size": file_size,
                "file_type": file_ext,
            }
            
            if file_ext in ['.csv', 'csv']:
                # Parse CSV
                df = pd.read_csv(file_path, nrows=self.max_rows_per_sheet)
                content_parts.append(self._dataframe_to_text(df, "CSV Data"))
                metadata.update({
                    "sheets": 1,
                    "total_rows": len(df),
                    "total_columns": len(df.columns),
                    "columns": list(df.columns),
                })
            else:
                # Parse Excel
                excel_file = pd.ExcelFile(file_path)
                sheets_to_parse = sheet_names or excel_file.sheet_names
                
                sheet_data = []
                total_rows = 0
                total_columns = 0
                
                for sheet_name in sheets_to_parse:
                    if sheet_name in excel_file.sheet_names:
                        df = pd.read_excel(
                            excel_file, 
                            sheet_name=sheet_name,
                            nrows=self.max_rows_per_sheet
                        )
                        
                        content_parts.append(self._dataframe_to_text(df, f"Sheet: {sheet_name}"))
                        
                        sheet_data.append({
                            "name": sheet_name,
                            "rows": len(df),
                            "columns": len(df.columns),
                            "column_names": list(df.columns),
                        })
                        
                        total_rows += len(df)
                        total_columns = max(total_columns, len(df.columns))
                
                metadata.update({
                    "sheets": len(sheet_data),
                    "sheet_data": sheet_data,
                    "total_rows": total_rows,
                    "max_columns": total_columns,
                })
            
            content = "\n\n".join(content_parts)
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            logger.info(
                f"Excel/CSV parsing complete: {metadata.get('sheets', 1)} sheets, "
                f"{metadata.get('total_rows', 0)} rows in {processing_time:.2f}s"
            )
            
            return ParsedDocument(
                content=content,
                metadata=metadata,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Failed to parse Excel/CSV: {e}")
            raise
    
    def _dataframe_to_text(self, df: pd.DataFrame, title: str) -> str:
        """Convert DataFrame to readable text format."""
        lines = [f"[{title}]"]
        lines.append(f"Dimensions: {len(df)} rows × {len(df.columns)} columns")
        lines.append("")
        
        # Add column headers
        lines.append("Columns: " + " | ".join(str(col) for col in df.columns))
        lines.append("-" * 50)
        
        # Add data rows (limited)
        max_rows = min(100, len(df))  # Show first 100 rows in text
        for idx, row in df.head(max_rows).iterrows():
            row_text = " | ".join(str(val) for val in row.values)
            lines.append(row_text)
        
        if len(df) > max_rows:
            lines.append(f"... ({len(df) - max_rows} more rows)")
        
        return "\n".join(lines)