"""
JSON File Parser

This module handles parsing of JSON (.json) files with intelligent
data extraction and structure preservation for vector indexing.
"""

import json
import os
import re
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from .base_parser import BaseParser, ParseResult, ValidationResult


class JSONParser(BaseParser):
    """Parser for JSON (.json) files"""

    SUPPORTED_EXTENSIONS = ['.json', '.jsonl']
    MAGIC_NUMBERS = {
        '.json': b'{',  # JSON objects start with {
        '.jsonl': b'',  # JSONL files are line-by-line JSON
    }

    def extract_content(self, file_path: str) -> ParseResult:
        """
        Extract content from JSON file with intelligent structuring

        Args:
            file_path: Path to the JSON file

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

            # Detect file format and parse accordingly
            file_extension = os.path.splitext(file_path)[1].lower()

            if file_extension == '.jsonl':
                parsed_data, metadata = self._parse_jsonl_file(file_path)
            else:
                parsed_data, metadata = self._parse_json_file(file_path)

            # Convert to searchable text format
            processed_content = self._convert_json_to_text(parsed_data, metadata)

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

        except Exception as e:
            return ParseResult(
                success=False,
                error_message=f"Failed to parse JSON file: {str(e)}"
            )

    def _parse_json_file(self, file_path: str) -> tuple[Any, Dict[str, Any]]:
        """
        Parse regular JSON file

        Args:
            file_path: Path to JSON file

        Returns:
            Tuple of (parsed_data, metadata)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

            metadata = {
                'file_type': 'json',
                'json_format': 'object',
                'root_type': type(data).__name__,
                'depth': self._calculate_depth(data),
                'total_keys': self._count_keys(data),
                'total_values': self._count_values(data),
                'has_arrays': self._has_arrays(data),
                'has_objects': self._has_objects(data),
                'max_array_length': self._get_max_array_length(data),
                'structure_analysis': self._analyze_structure(data)
            }

            return data, metadata

        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise Exception(f"JSON parsing failed: {str(e)}")

    def _parse_jsonl_file(self, file_path: str) -> tuple[List[Dict], Dict[str, Any]]:
        """
        Parse JSONL (JSON Lines) file - one JSON object per line

        Args:
            file_path: Path to JSONL file

        Returns:
            Tuple of (parsed_data, metadata)
        """
        try:
            data = []
            line_count = 0
            error_count = 0

            with open(file_path, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        json_obj = json.loads(line)
                        data.append(json_obj)
                        line_count += 1
                    except json.JSONDecodeError as e:
                        error_count += 1
                        # Continue parsing other lines even if some are invalid
                        continue

            if not data and error_count > 0:
                raise Exception(f"No valid JSON objects found in {error_count} lines")

            # Analyze the first few objects to understand structure
            sample_objects = data[:min(10, len(data))]
            structure_analysis = self._analyze_jsonl_structure(sample_objects)

            metadata = {
                'file_type': 'jsonl',
                'json_format': 'lines',
                'line_count': line_count,
                'error_count': error_count,
                'total_objects': len(data),
                'sample_structure': structure_analysis,
                'consistent_structure': self._check_consistent_structure(data)
            }

            return data, metadata

        except Exception as e:
            raise Exception(f"JSONL parsing failed: {str(e)}")

    def _calculate_depth(self, obj: Any, current_depth: int = 0) -> int:
        """
        Calculate the maximum depth of nested JSON structure

        Args:
            obj: JSON object to analyze
            current_depth: Current recursion depth

        Returns:
            Maximum depth
        """
        if isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(self._calculate_depth(v, current_depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return current_depth
            return max(self._calculate_depth(item, current_depth + 1) for item in obj)
        else:
            return current_depth

    def _count_keys(self, obj: Any) -> int:
        """
        Count total number of keys in JSON structure

        Args:
            obj: JSON object to analyze

        Returns:
            Total key count
        """
        count = 0
        if isinstance(obj, dict):
            count += len(obj)
            for value in obj.values():
                count += self._count_keys(value)
        elif isinstance(obj, list):
            for item in obj:
                count += self._count_keys(item)
        return count

    def _count_values(self, obj: Any) -> int:
        """
        Count total number of values (non-object, non-array) in JSON structure

        Args:
            obj: JSON object to analyze

        Returns:
            Total value count
        """
        count = 0
        if isinstance(obj, dict):
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    count += self._count_values(value)
                else:
                    count += 1
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    count += self._count_values(item)
                else:
                    count += 1
        else:
            count = 1
        return count

    def _has_arrays(self, obj: Any) -> bool:
        """
        Check if JSON structure contains arrays

        Args:
            obj: JSON object to analyze

        Returns:
            True if arrays are present
        """
        if isinstance(obj, list):
            return True
        elif isinstance(obj, dict):
            return any(self._has_arrays(v) for v in obj.values())
        return False

    def _has_objects(self, obj: Any) -> bool:
        """
        Check if JSON structure contains objects

        Args:
            obj: JSON object to analyze

        Returns:
            True if objects are present
        """
        if isinstance(obj, dict):
            return True
        elif isinstance(obj, list):
            return any(self._has_objects(item) for item in obj)
        return False

    def _get_max_array_length(self, obj: Any) -> int:
        """
        Get the maximum array length in JSON structure

        Args:
            obj: JSON object to analyze

        Returns:
            Maximum array length
        """
        max_length = 0
        if isinstance(obj, list):
            max_length = max(max_length, len(obj))
            for item in obj:
                max_length = max(max_length, self._get_max_array_length(item))
        elif isinstance(obj, dict):
            for value in obj.values():
                max_length = max(max_length, self._get_max_array_length(value))
        return max_length

    def _analyze_structure(self, obj: Any) -> Dict[str, Any]:
        """
        Analyze JSON structure and extract key patterns

        Args:
            obj: JSON object to analyze

        Returns:
            Structure analysis dictionary
        """
        analysis = {
            'root_keys': [],
            'key_types': {},
            'value_types': {},
            'common_patterns': []
        }

        if isinstance(obj, dict):
            analysis['root_keys'] = list(obj.keys())
            analysis['key_types'] = {k: type(v).__name__ for k, v in obj.items()}
        elif isinstance(obj, list) and obj:
            # If root is an array, analyze first item
            first_item = obj[0]
            if isinstance(first_item, dict):
                analysis['root_keys'] = list(first_item.keys())
                analysis['key_types'] = {k: type(v).__name__ for k, v in first_item.items()}

        # Analyze value types distribution
        value_counts = self._count_value_types(obj)
        analysis['value_types'] = value_counts

        return analysis

    def _count_value_types(self, obj: Any) -> Dict[str, int]:
        """
        Count different value types in JSON structure

        Args:
            obj: JSON object to analyze

        Returns:
            Dictionary of type counts
        """
        type_counts = {}

        def count_types(item):
            if isinstance(item, dict):
                for value in item.values():
                    count_types(value)
            elif isinstance(item, list):
                for element in item:
                    count_types(element)
            else:
                type_name = type(item).__name__
                type_counts[type_name] = type_counts.get(type_name, 0) + 1

        count_types(obj)
        return type_counts

    def _analyze_jsonl_structure(self, objects: List[Dict]) -> Dict[str, Any]:
        """
        Analyze structure of JSONL objects

        Args:
            objects: List of JSON objects

        Returns:
            Structure analysis dictionary
        """
        if not objects:
            return {}

        # Analyze first object as template
        first_obj = objects[0]
        analysis = {
            'template_keys': list(first_obj.keys()),
            'template_types': {k: type(v).__name__ for k, v in first_obj.items()},
            'field_frequency': {},
            'sample_values': {}
        }

        # Count field frequency across all objects
        all_keys = set()
        for obj in objects:
            all_keys.update(obj.keys())

        for key in all_keys:
            frequency = sum(1 for obj in objects if key in obj)
            analysis['field_frequency'][key] = {
                'count': frequency,
                'percentage': (frequency / len(objects)) * 100
            }

        # Get sample values for each field
        for key in analysis['template_keys']:
            sample_values = []
            for obj in objects[:5]:  # First 5 objects
                if key in obj and obj[key] is not None:
                    sample_values.append(str(obj[key]))

            if sample_values:
                analysis['sample_values'][key] = sample_values[:3]  # First 3 samples

        return analysis

    def _check_consistent_structure(self, objects: List[Dict]) -> bool:
        """
        Check if all JSONL objects have consistent structure

        Args:
            objects: List of JSON objects

        Returns:
            True if structure is consistent
        """
        if not objects:
            return True

        first_keys = set(objects[0].keys())

        for obj in objects[1:]:
            current_keys = set(obj.keys())

            # Allow some flexibility - consider consistent if 80% of keys match
            intersection = len(first_keys.intersection(current_keys))
            union = len(first_keys.union(current_keys))

            if (intersection / union) < 0.8:
                return False

        return True

    def _convert_json_to_text(self, data: Any, metadata: Dict[str, Any]) -> str:
        """
        Convert JSON data to searchable text format

        Args:
            data: Parsed JSON data
            metadata: JSON metadata

        Returns:
            Formatted text content
        """
        text_sections = []

        # Add metadata section
        metadata_section = []
        metadata_section.append(f"JSON File Information:")
        metadata_section.append(f"- Format: {metadata.get('json_format', 'unknown')}")
        metadata_section.append(f"- Root Type: {metadata.get('root_type', 'unknown')}")
        metadata_section.append(f"- Maximum Depth: {metadata.get('depth', 0)}")
        metadata_section.append(f"- Total Keys: {metadata.get('total_keys', 0)}")
        metadata_section.append(f"- Total Values: {metadata.get('total_values', 0)}")

        if metadata.get('json_format') == 'lines':
            metadata_section.append(f"- Total Objects: {metadata.get('total_objects', 0)}")
            metadata_section.append(f"- Consistent Structure: {metadata.get('consistent_structure', False)}")
        else:
            metadata_section.append(f"- Contains Arrays: {metadata.get('has_arrays', False)}")
            metadata_section.append(f"- Contains Objects: {metadata.get('has_objects', False)}")
            metadata_section.append(f"- Max Array Length: {metadata.get('max_array_length', 0)}")

        text_sections.append('\n'.join(metadata_section))

        # Add structure analysis
        structure = metadata.get('structure_analysis', {})
        if structure.get('root_keys'):
            structure_section = []
            structure_section.append(f"\nJSON Structure:")
            structure_section.append(f"- Root Keys: {', '.join(structure['root_keys'])}")

            if structure.get('key_types'):
                types_info = [f"{k}: {v}" for k, v in structure['key_types'].items()]
                structure_section.append(f"- Key Types: {', '.join(types_info)}")

            if structure.get('value_types'):
                types_info = [f"{k}: {v}" for k, v in structure['value_types'].items()]
                structure_section.append(f"- Value Types: {', '.join(types_info)}")

            text_sections.append('\n'.join(structure_section))

        # Add data content
        if metadata.get('json_format') == 'lines':
            # JSONL format
            content_section = []
            content_section.append(f"\nJSONL Data Content:")

            # Show sample objects
            if isinstance(data, list) and data:
                content_section.append(f"\nSample JSON Objects (showing first {min(5, len(data))}):")
                for i, obj in enumerate(data[:5]):
                    content_section.append(f"\nObject {i+1}:")
                    obj_text = self._format_json_object(obj, max_depth=2)
                    content_section.append(obj_text)

            # Add field analysis
            if metadata.get('sample_structure', {}).get('field_frequency'):
                freq_section = []
                freq_section.append(f"\nField Frequency Analysis:")
                field_freq = metadata['sample_structure']['field_frequency']
                for field, info in sorted(field_freq.items(), key=lambda x: x[1]['count'], reverse=True)[:10]:
                    freq_section.append(f"- {field}: {info['count']} occurrences ({info['percentage']:.1f}%)")
                content_section.append('\n'.join(freq_section))

            text_sections.append('\n'.join(content_section))
        else:
            # Regular JSON format
            content_section = []
            content_section.append(f"\nJSON Data Content:")
            json_text = self._format_json_object(data, max_depth=3)
            content_section.append(json_text)
            text_sections.append('\n'.join(content_section))

        return '\n'.join(text_sections)

    def _format_json_object(self, obj: Any, max_depth: int = 3, current_depth: int = 0, indent: str = "") -> str:
        """
        Format JSON object as readable text

        Args:
            obj: JSON object to format
            max_depth: Maximum depth to format
            current_depth: Current recursion depth
            indent: Current indentation string

        Returns:
            Formatted text representation
        """
        if current_depth >= max_depth:
            if isinstance(obj, (dict, list)):
                return f"{indent}[... nested content ...]"
            return f"{indent}{str(obj)}"

        if isinstance(obj, dict):
            if not obj:
                return f"{indent}{{}}"

            lines = [f"{indent}{{"]
            for key, value in list(obj.items())[:10]:  # Limit to first 10 items
                if isinstance(value, (dict, list)):
                    lines.append(f"{indent}  {key}:")
                    nested = self._format_json_object(value, max_depth, current_depth + 1, indent + "  ")
                    lines.append(nested)
                else:
                    lines.append(f"{indent}  {key}: {value}")

            if len(obj) > 10:
                lines.append(f"{indent}  ... and {len(obj) - 10} more items")

            lines.append(f"{indent}}}")
            return '\n'.join(lines)

        elif isinstance(obj, list):
            if not obj:
                return f"{indent}[]"

            lines = [f"{indent}["]
            for i, item in enumerate(obj[:10]):  # Limit to first 10 items
                if isinstance(item, (dict, list)):
                    lines.append(f"{indent}  [{i}]:")
                    nested = self._format_json_object(item, max_depth, current_depth + 1, indent + "  ")
                    lines.append(nested)
                else:
                    lines.append(f"{indent}  [{i}]: {item}")

            if len(obj) > 10:
                lines.append(f"{indent}  ... and {len(obj) - 10} more items")

            lines.append(f"{indent}]")
            return '\n'.join(lines)

        else:
            return f"{indent}{str(obj)}"

    def validate_file(self, file_path: str) -> ValidationResult:
        """
        Enhanced JSON file validation

        Args:
            file_path: Path to JSON file

        Returns:
            ValidationResult with JSON-specific validation
        """
        base_validation = super().validate_file(file_path)

        if not base_validation.is_valid:
            return base_validation

        try:
            # Additional JSON-specific validation
            file_extension = os.path.splitext(file_path)[1].lower()

            # Try to parse a sample to check JSON validity
            with open(file_path, 'r', encoding='utf-8') as file:
                sample = file.read(1024)

            # Basic JSON format check
            if not (sample.strip().startswith('{') or sample.strip().startswith('[') or file_extension == '.jsonl'):
                base_validation.error_message = "File may not be properly formatted JSON"

            # Try to validate JSON structure
            if file_extension == '.jsonl':
                # Validate JSONL format
                try:
                    lines = sample.split('\n')
                    valid_lines = 0
                    for line in lines:
                        if line.strip():
                            json.loads(line)
                            valid_lines += 1

                    if valid_lines == 0 and len([l for l in lines if l.strip()]) > 0:
                        return ValidationResult(
                            is_valid=False,
                            error_message="No valid JSON objects found in JSONL file",
                            file_size=base_validation.file_size
                        )

                except json.JSONDecodeError:
                    return ValidationResult(
                        is_valid=False,
                        error_message="JSONL file contains invalid JSON format",
                        file_size=base_validation.file_size
                    )
            else:
                # Validate regular JSON format
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        json.load(file)
                except json.JSONDecodeError as e:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Invalid JSON format: {str(e)}",
                        file_size=base_validation.file_size
                    )

            return base_validation

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"JSON validation failed: {str(e)}"
            )