"""
CSV File Parser

This module handles parsing of CSV (.csv) files with intelligent data
extraction and structure preservation for vector indexing.
"""

import csv
import io
import os
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from .base_parser import BaseParser, ParseResult, ValidationResult


class CSVParser(BaseParser):
    """Parser for CSV (.csv) files"""

    SUPPORTED_EXTENSIONS = ['.csv']
    MAGIC_NUMBERS = {
        '.csv': b'',  # CSV files don't have reliable magic numbers
    }

    def extract_content(self, file_path: str) -> ParseResult:
        """
        Extract content from CSV file with intelligent structuring

        Args:
            file_path: Path to the CSV file

        Returns:
            ParseResult with extracted content and metadata
        """
        import time
        start_time = time.time()

        try:
            # Validate file first
            validation = self.validate_file(file_path)
            if not validation.is_valid:
                return ParseResult(
                    success=False,
                    error_message=validation.error_message
                )

            # Detect encoding and read file
            encoding = self._detect_encoding(file_path)
            with open(file_path, 'r', encoding=encoding, newline='') as file:
                content = file.read()

            if not content.strip():
                return ParseResult(
                    success=False,
                    error_message="CSV file appears to be empty"
                )

            # Parse CSV with intelligent format detection
            parsed_data, metadata = self._parse_csv_content(content, file_path)

            # Convert to searchable text format
            processed_content = self._convert_csv_to_text(parsed_data, metadata)

            # Create chunks for vector indexing
            chunks = self.chunk_text(processed_content)

            processing_time = time.time() - start_time

            return ParseResult(
                success=True,
                content=processed_content,
                metadata=metadata,
                chunks=chunks,
                total_chunks=len(chunks),
                file_size=validation.file_size,
                processing_time=processing_time
            )

        except UnicodeDecodeError as e:
            return ParseResult(
                success=False,
                error_message=f"Failed to decode CSV file with detected encoding: {str(e)}"
            )
        except Exception as e:
            return ParseResult(
                success=False,
                error_message=f"Failed to parse CSV file: {str(e)}"
            )

    def _detect_encoding(self, file_path: str) -> str:
        """
        Detect file encoding with fallback options

        Args:
            file_path: Path to the file

        Returns:
            Detected encoding string
        """
        encodings_to_try = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']

        for encoding in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read(1024)  # Try to read a small chunk
                return encoding
            except UnicodeDecodeError:
                continue
            except Exception:
                continue

        # Fallback to utf-8 with error handling
        return 'utf-8'

    def _parse_csv_content(self, content: str, file_path: str) -> tuple[List[List[str]], Dict[str, Any]]:
        """
        Parse CSV content with intelligent format detection

        Args:
            content: Raw CSV content
            file_path: Path to the file

        Returns:
            Tuple of (parsed_data, metadata)
        """
        # Detect CSV dialect
        try:
            sample = content[:1024]
            sniffer = csv.Sniffer()

            # Check if it's actually CSV content
            if not sniffer.has_header(sample):
                # Try to detect if it's actually another delimiter format
                dialect = sniffer.sniff(sample, delimiters=',;\t|')
            else:
                dialect = sniffer.sniff(sample)

        except Exception:
            # Fallback to default CSV format
            import csv
            class DefaultDialect:
                delimiter = ','
                quotechar = '"'
                quoting = csv.QUOTE_MINIMAL
                lineterminator = '\n'
            dialect = DefaultDialect()

        # Parse the CSV content
        parsed_data = []
        metadata = {
            'file_type': 'csv',
            'delimiter': dialect.delimiter,
            'has_header': False,
            'row_count': 0,
            'column_count': 0,
            'encoding': self._detect_encoding(file_path),
            'total_cells': 0,
            'numeric_columns': [],
            'text_columns': [],
            'data_types': {}
        }

        try:
            # Use io.StringIO for proper CSV parsing
            csv_file = io.StringIO(content)
            reader = csv.reader(csv_file, dialect=dialect)

            # Parse all rows
            rows = list(reader)

            if not rows:
                return [], metadata

            # Detect header
            if len(rows) > 1:
                metadata['has_header'] = self._detect_header(rows[0], rows[1:])

            # Process rows
            if metadata['has_header']:
                headers = rows[0]
                data_rows = rows[1:]
            else:
                headers = [f"Column_{i+1}" for i in range(len(rows[0]))]
                data_rows = rows

            # Normalize data (clean up each cell)
            for row in data_rows:
                # Pad or truncate to match header length
                normalized_row = []
                for i in range(len(headers)):
                    if i < len(row):
                        cell_value = str(row[i]).strip()
                        # Remove quotes and clean whitespace
                        cell_value = cell_value.strip('"\'')
                        cell_value = re.sub(r'\s+', ' ', cell_value)
                        normalized_row.append(cell_value)
                    else:
                        normalized_row.append('')  # Empty cell for missing columns
                parsed_data.append(normalized_row)

            # Analyze data types
            metadata.update(self._analyze_data_types(parsed_data, headers))
            metadata['row_count'] = len(parsed_data)
            metadata['column_count'] = len(headers)
            metadata['total_cells'] = len(parsed_data) * len(headers) if parsed_data else 0

            # Store headers for reference
            metadata['headers'] = headers

        except Exception as e:
            raise Exception(f"CSV parsing failed: {str(e)}")

        return parsed_data, metadata

    def _detect_header(self, first_row: List[str], sample_rows: List[List[str]]) -> bool:
        """
        Detect if first row is likely a header

        Args:
            first_row: First row of CSV
            sample_rows: Sample of data rows

        Returns:
            True if first row appears to be a header
        """
        if not sample_rows or not first_row:
            return False

        # Check if header looks different from data rows
        header_score = 0

        # Headers often contain text, data often contains numbers
        for i, header_cell in enumerate(first_row):
            if not header_cell.strip():
                continue

            # Check corresponding cells in sample rows
            sample_values = []
            for row in sample_rows[:min(5, len(sample_rows))]:  # Check first 5 data rows
                if i < len(row):
                    val = row[i].strip()
                    if val:
                        sample_values.append(val)

            if not sample_values:
                continue

            # Scoring factors
            header_text_ratio = len(re.findall(r'[a-zA-Z]', header_cell)) / max(len(header_cell), 1)
            sample_numeric_ratio = sum(1 for v in sample_values if self._is_numeric(v)) / max(len(sample_values), 1)

            # Header is likely if:
            # 1. Header has more text than data
            # 2. Data has more numbers than header
            # 3. Header uses spaces/camelCase (common for column names)
            has_spaces_or_camel = ' ' in header_cell or re.match(r'[a-z][A-Z]', header_cell)

            if header_text_ratio > sample_numeric_ratio:
                header_score += 1
            if sample_numeric_ratio > 0.5:
                header_score += 1
            if has_spaces_or_camel:
                header_score += 1

        # Consider it a header if it scores well
        return header_score >= len(first_row) * 0.3

    def _is_numeric(self, value: str) -> bool:
        """
        Check if a string value appears to be numeric

        Args:
            value: String to check

        Returns:
            True if value appears numeric
        """
        try:
            float(value.replace(',', '').replace('$', '').replace('%', ''))
            return True
        except ValueError:
            return False

    def _analyze_data_types(self, data: List[List[str]], headers: List[str]) -> Dict[str, Any]:
        """
        Analyze data types in CSV columns

        Args:
            data: Parsed CSV data
            headers: Column headers

        Returns:
            Dictionary with data type analysis
        """
        if not data or not headers:
            return {
                'numeric_columns': [],
                'text_columns': [],
                'data_types': {}
            }

        analysis = {
            'numeric_columns': [],
            'text_columns': [],
            'data_types': {},
            'column_stats': {}
        }

        # Analyze each column
        for col_idx, header in enumerate(headers):
            if col_idx >= len(data[0]):
                continue

            column_values = []
            for row in data:
                if col_idx < len(row):
                    val = row[col_idx].strip()
                    if val:
                        column_values.append(val)

            if not column_values:
                analysis['data_types'][header] = 'empty'
                continue

            # Determine column type
            numeric_count = sum(1 for v in column_values if self._is_numeric(v))
            total_count = len(column_values)
            numeric_ratio = numeric_count / total_count

            if numeric_ratio > 0.7:
                # Mostly numeric
                analysis['numeric_columns'].append(header)
                analysis['data_types'][header] = 'numeric'
            else:
                # Mostly text
                analysis['text_columns'].append(header)
                analysis['data_types'][header] = 'text'

            # Basic statistics
            stats = {
                'total_values': total_count,
                'empty_values': len([row for row in data if col_idx >= len(row) or not row[col_idx].strip()]),
                'unique_values': len(set(column_values)),
                'numeric_ratio': numeric_ratio
            }

            # Numeric stats
            if analysis['data_types'][header] == 'numeric':
                try:
                    numeric_vals = [float(v.replace(',', '').replace('$', '').replace('%', ''))
                                   for v in column_values if self._is_numeric(v)]
                    if numeric_vals:
                        stats.update({
                            'min_value': min(numeric_vals),
                            'max_value': max(numeric_vals),
                            'avg_value': sum(numeric_vals) / len(numeric_vals)
                        })
                except Exception:
                    pass

            analysis['column_stats'][header] = stats

        return analysis

    def _convert_csv_to_text(self, data: List[List[str]], metadata: Dict[str, Any]) -> str:
        """
        Convert CSV data to searchable text format

        Args:
            data: Parsed CSV data
            metadata: CSV metadata

        Returns:
            Formatted text content
        """
        if not data:
            return ""

        text_sections = []

        # Add metadata section
        metadata_section = []
        metadata_section.append(f"CSV File Information:")
        metadata_section.append(f"- Total Rows: {metadata.get('row_count', 0)}")
        metadata_section.append(f"- Total Columns: {metadata.get('column_count', 0)}")
        metadata_section.append(f"- Delimiter: '{metadata.get('delimiter', ',')}'")
        metadata_section.append(f"- Has Header: {metadata.get('has_header', False)}")

        if metadata.get('headers'):
            metadata_section.append(f"- Column Names: {', '.join(metadata['headers'])}")

        text_sections.append('\n'.join(metadata_section))

        # Add data summary
        if metadata.get('numeric_columns') or metadata.get('text_columns'):
            summary_section = []
            summary_section.append(f"\nColumn Analysis:")
            summary_section.append(f"- Numeric Columns: {', '.join(metadata.get('numeric_columns', []))}")
            summary_section.append(f"- Text Columns: {', '.join(metadata.get('text_columns', []))}")
            text_sections.append('\n'.join(summary_section))

        # Add formatted data
        data_section = []
        data_section.append(f"\nCSV Data Content:")

        headers = metadata.get('headers', [f"Column_{i+1}" for i in range(len(data[0]) if data else 0)])

        # Add column information
        for i, header in enumerate(headers):
            if i < len(data[0]):
                col_data = [row[i] for row in data if i < len(row) and row[i].strip()]
                if col_data:
                    unique_values = list(set(col_data[:10]))  # First 10 unique values
                    data_section.append(f"\nColumn '{header}' ({len(col_data)} values):")
                    data_section.append(f"Sample values: {', '.join(str(v) for v in unique_values[:5])}")

        # Add row-based representation for context
        data_section.append(f"\nData Rows (showing first 10 rows):")
        for i, row in enumerate(data[:10]):
            row_data = []
            for j, cell in enumerate(row):
                if j < len(headers):
                    row_data.append(f"{headers[j]}: {cell}")
            data_section.append(f"Row {i+1}: {' | '.join(row_data)}")

        text_sections.append('\n'.join(data_section))

        return '\n'.join(text_sections)

    def validate_file(self, file_path: str) -> ValidationResult:
        """
        Enhanced CSV file validation

        Args:
            file_path: Path to CSV file

        Returns:
            ValidationResult with CSV-specific validation
        """
        base_validation = super().validate_file(file_path)

        if not base_validation.is_valid:
            return base_validation

        try:
            # Additional CSV-specific validation
            encoding = self._detect_encoding(file_path)

            # Try to read and validate CSV structure
            with open(file_path, 'r', encoding=encoding) as file:
                sample = file.read(1024)

            # Check if file looks like CSV data
            if ',' not in sample and ';' not in sample and '\t' not in sample:
                # May not be CSV - still valid but with warning
                base_validation.error_message = "File may not be properly formatted CSV (no common delimiters found)"

            # Try basic CSV parsing validation
            try:
                import csv
                csv_file = io.StringIO(sample)
                reader = csv.reader(csv_file)
                rows = list(reader)

                if not rows:
                    return ValidationResult(
                        is_valid=False,
                        error_message="CSV file appears to be empty or malformed",
                        file_size=base_validation.file_size
                    )

                # Check for consistent column counts
                if len(rows) > 1:
                    first_row_length = len(rows[0])
                    inconsistent_rows = sum(1 for row in rows if len(row) != first_row_length)

                    if inconsistent_rows > len(rows) * 0.5:  # More than 50% inconsistent
                        base_validation.error_message = f"CSV has inconsistent row lengths ({inconsistent_rows} of {len(rows)} rows differ from first row)"

            except Exception as e:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"CSV structure validation failed: {str(e)}",
                    file_size=base_validation.file_size
                )

            return base_validation

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"CSV validation failed: {str(e)}"
            )