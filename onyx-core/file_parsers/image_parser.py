"""
Image File Parser

This module handles parsing of image files (.png, .jpg, .jpeg) with metadata
extraction and placeholder content generation for vector indexing.
"""

import os
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
from .base_parser import BaseParser, ParseResult, ValidationResult


class ImageParser(BaseParser):
    """Parser for image files (.png, .jpg, .jpeg)"""

    SUPPORTED_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp']
    MAGIC_NUMBERS = {
        '.png': b'\x89PNG\r\n\x1a\n',
        '.jpg': b'\xff\xd8\xff',
        '.jpeg': b'\xff\xd8\xff',
        '.webp': b'RIFF\x00\x00\x00\x00WEBP',
    }

    def extract_content(self, file_path: str) -> ParseResult:
        """
        Extract metadata from image file (no OCR - metadata only)

        Args:
            file_path: Path to the image file

        Returns:
            ParseResult with image metadata and placeholder content
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

            # Extract image metadata
            metadata = self._extract_image_metadata(file_path)

            # Generate placeholder content for vector indexing
            placeholder_content = self._generate_image_placeholder(file_path, metadata)

            # Create a single chunk since this is just metadata
            chunks = [placeholder_content]

            processing_time = time.time() - start_time

            return ParseResult(
                success=True,
                content=placeholder_content,
                metadata=metadata,
                chunks=chunks,
                total_chunks=1,
                file_size=validation.file_size,
                processing_time=processing_time
            )

        except Exception as e:
            return ParseResult(
                success=False,
                error_message=f"Failed to parse image file: {str(e)}"
            )

    def _extract_image_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from image file

        Args:
            file_path: Path to the image file

        Returns:
            Dictionary of image metadata
        """
        metadata = {
            'file_type': 'image',
            'extraction_method': 'image_parser',
            'image_format': self._get_image_format(file_path),
            'file_size_bytes': os.path.getsize(file_path),
        }

        # Calculate file hash for deduplication
        metadata['content_hash'] = self._calculate_file_hash(file_path)

        # Extract basic image info using Pillow if available
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                metadata.update({
                    'width_pixels': img.width,
                    'height_pixels': img.height,
                    'mode': img.mode,  # RGB, RGBA, L, etc.
                    'format_name': img.format,
                    'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info,
                    'megapixels': round((img.width * img.height) / 1000000, 2),
                })

                # Extract EXIF data if available
                if hasattr(img, '_getexif') and img._getexif():
                    exif_data = img._getexif()
                    metadata['has_exif'] = True
                    metadata['exif_data'] = self._process_exif_data(exif_data)
                else:
                    metadata['has_exif'] = False

                # Additional image properties
                metadata.update({
                    'aspect_ratio': round(img.width / img.height, 3) if img.height > 0 else 0,
                    'is_square': img.width == img.height,
                    'is_landscape': img.width > img.height,
                    'is_portrait': img.height > img.width,
                })

        except ImportError:
            metadata['pillow_available'] = False
            metadata['extraction_note'] = 'PIL/Pillow not available - limited metadata extracted'
        except Exception as e:
            metadata['extraction_error'] = str(e)
            metadata['extraction_note'] = f'Failed to extract detailed metadata: {str(e)}'

        # Extract filename-based metadata
        filename = os.path.basename(file_path)
        metadata.update({
            'filename': filename,
            'filename_without_extension': os.path.splitext(filename)[0],
            'file_extension': os.path.splitext(filename)[1].lower(),
        })

        # Analyze filename for potential content clues
        metadata.update(self._analyze_filename(filename))

        return metadata

    def _get_image_format(self, file_path: str) -> str:
        """
        Determine image format from file signature and extension

        Args:
            file_path: Path to the image file

        Returns:
            Detected image format
        """
        # Check magic number first
        with open(file_path, 'rb') as f:
            header = f.read(16)

        for ext, signature in self.MAGIC_NUMBERS.items():
            if header.startswith(signature):
                return ext[1:]  # Remove the dot

        # Fallback to file extension
        extension = os.path.splitext(file_path)[1].lower()
        return extension[1:] if extension else 'unknown'

    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA-256 hash of file for deduplication

        Args:
            file_path: Path to the file

        Returns:
            SHA-256 hash as hexadecimal string
        """
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _process_exif_data(self, exif_data: Dict) -> Dict[str, Any]:
        """
        Process and extract relevant EXIF data

        Args:
            exif_data: Raw EXIF data from PIL

        Returns:
            Processed EXIF metadata
        """
        try:
            from PIL.ExifTags import TAGS

            processed_exif = {}
            relevant_tags = {
                'DateTime': 'datetime',
                'DateTimeOriginal': 'datetime_original',
                'DateTimeDigitized': 'datetime_digitized',
                'Make': 'camera_make',
                'Model': 'camera_model',
                'Software': 'software',
                'Artist': 'artist',
                'Copyright': 'copyright',
                'XResolution': 'x_resolution',
                'YResolution': 'y_resolution',
                'ResolutionUnit': 'resolution_unit',
                'Flash': 'flash_used',
                'FocalLength': 'focal_length',
                'FNumber': 'f_number',
                'ExposureTime': 'exposure_time',
                'ISOS': 'iso_speed',
                'WhiteBalance': 'white_balance',
            }

            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, tag_id)
                if tag_name in relevant_tags:
                    processed_key = relevant_tags[tag_name]
                    # Convert EXIF values to readable format
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8')
                        except UnicodeDecodeError:
                            value = str(value)
                    processed_exif[processed_key] = value

            return processed_exif

        except Exception:
            return {'exif_processing_error': 'Failed to process EXIF data'}

    def _analyze_filename(self, filename: str) -> Dict[str, Any]:
        """
        Analyze filename for content clues

        Args:
            filename: Image filename

        Returns:
            Filename analysis results
        """
        filename_lower = filename.lower()

        analysis = {
            'has_date_in_filename': bool(re.search(r'\d{4}[-_]\d{2}[-_]\d{2}', filename_lower)),
            'keywords': [],
            'content_hints': []
        }

        # Common image keywords
        keywords = [
            'screenshot', 'capture', 'photo', 'image', 'pic', 'picture',
            'diagram', 'chart', 'graph', 'table', 'flowchart', 'schema',
            'logo', 'icon', 'avatar', 'profile', 'banner', 'header',
            'thumbnail', 'preview', 'draft', 'final', 'version',
        ]

        for keyword in keywords:
            if keyword in filename_lower:
                analysis['keywords'].append(keyword)

        # Content type hints
        if any(word in filename_lower for word in ['screenshot', 'capture', 'screen']):
            analysis['content_hints'].append('screenshot')
        if any(word in filename_lower for word in ['diagram', 'chart', 'graph', 'flowchart']):
            analysis['content_hints'].append('diagram')
        if any(word in filename_lower for word in ['logo', 'icon', 'avatar']):
            analysis['content_hints'].append('graphic')
        if any(word in filename_lower for word in ['document', 'scan', 'pdf']):
            analysis['content_hints'].append('document_image')

        return analysis

    def _generate_image_placeholder(self, file_path: str, metadata: Dict[str, Any]) -> str:
        """
        Generate descriptive placeholder text for image

        Args:
            file_path: Path to the image file
            metadata: Extracted image metadata

        Returns:
            Descriptive placeholder text
        """
        lines = []

        # Basic image description
        filename = metadata.get('filename', os.path.basename(file_path))
        lines.append(f"IMAGE: {filename}")

        # Image properties
        if metadata.get('width_pixels') and metadata.get('height_pixels'):
            width = metadata['width_pixels']
            height = metadata['height_pixels']
            lines.append(f"Dimensions: {width}x{height} pixels")

            if metadata.get('megapixels'):
                lines.append(f"Resolution: {metadata['megapixels']} MP")

        # Format information
        format_info = metadata.get('image_format', 'unknown')
        mode = metadata.get('mode', 'unknown')
        lines.append(f"Format: {format_info.upper()}")
        lines.append(f"Color Mode: {mode}")

        # Aspect ratio information
        if metadata.get('aspect_ratio'):
            aspect_ratio = metadata['aspect_ratio']
            if metadata.get('is_square'):
                lines.append(f"Aspect Ratio: Square (1:1)")
            elif metadata.get('is_landscape'):
                lines.append(f"Aspect Ratio: Landscape ({aspect_ratio}:1)")
            elif metadata.get('is_portrait'):
                lines.append(f"Aspect Ratio: Portrait (1:{aspect_ratio})")

        # Camera information if available
        if metadata.get('exif_data'):
            exif = metadata['exif_data']
            camera_info = []

            if exif.get('camera_make') and exif.get('camera_model'):
                camera_info.append(f"Camera: {exif['camera_make']} {exif['camera_model']}")

            if exif.get('datetime_original'):
                camera_info.append(f"Taken: {exif['datetime_original']}")

            if camera_info:
                lines.append("Camera Information:")
                for info in camera_info:
                    lines.append(f"  {info}")

        # Content hints from filename
        if metadata.get('content_hints'):
            lines.append(f"Content Type: {', '.join(metadata['content_hints'])}")

        # Keywords from filename
        if metadata.get('keywords'):
            lines.append(f"Keywords: {', '.join(metadata['keywords'])}")

        # File information
        file_size = metadata.get('file_size_bytes', 0)
        if file_size > 0:
            if file_size < 1024:
                size_str = f"{file_size} bytes"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            lines.append(f"File Size: {size_str}")

        # Extraction notes
        if metadata.get('extraction_note'):
            lines.append(f"Note: {metadata['extraction_note']}")

        lines.append("Note: This image file contains visual content that requires visual inspection for full understanding.")

        return '\n'.join(lines)

    def validate_file(self, file_path: str) -> ValidationResult:
        """
        Enhanced image file validation

        Args:
            file_path: Path to image file

        Returns:
            ValidationResult with image-specific validation
        """
        base_validation = super().validate_file(file_path)

        if not base_validation.is_valid:
            return base_validation

        try:
            # Additional image-specific validation
            with open(file_path, 'rb') as file:
                header = file.read(32)  # Read more for better format detection

            # Check image format signatures
            format_detected = None
            for ext, signature in self.MAGIC_NUMBERS.items():
                if header.startswith(signature):
                    format_detected = ext[1:]  # Remove the dot
                    break

            if not format_detected:
                return ValidationResult(
                    is_valid=False,
                    error_message="File does not have a valid image format signature",
                    file_size=base_validation.file_size
                )

            # Verify file extension matches detected format
            file_extension = os.path.splitext(file_path)[1].lower()
            if file_extension and file_extension[1:] != format_detected:
                # Still valid but warn about mismatch
                base_validation.error_message = f"File extension '{file_extension}' doesn't match detected format '{format_detected}'"

            # Try to validate with Pillow if available
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    # Basic validation - can we load the image?
                    if img.width <= 0 or img.height <= 0:
                        return ValidationResult(
                            is_valid=False,
                            error_message="Image appears to have invalid dimensions",
                            file_size=base_validation.file_size
                        )

                    # Check for reasonable size limits
                    if img.width > 50000 or img.height > 50000:
                        return ValidationResult(
                            is_valid=False,
                            error_message="Image dimensions exceed maximum supported size (50000x50000)",
                            file_size=base_validation.file_size
                        )

            except ImportError:
                # Pillow not available - skip detailed validation
                pass
            except Exception as e:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Image validation failed: {str(e)}",
                    file_size=base_validation.file_size
                )

            return base_validation

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Image validation failed: {str(e)}"
            )