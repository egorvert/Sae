"""Tests for document parsing service."""

import base64

import pytest

from sae.services.document_parser import (
    DocumentParserError,
    UnsupportedFileTypeError,
    parse_document,
)
from tests.fixtures.sample_files import (
    SAMPLE_TXT_BASE64,
    SAMPLE_TXT_CONTENT,
    create_file_part,
    create_text_file_part,
)


class TestParseDocument:
    """Tests for parse_document function."""

    @pytest.mark.asyncio
    async def test_parse_text_success(self) -> None:
        """Test successful parsing of plain text file."""
        file_part = create_text_file_part("contract.txt")

        result = await parse_document(file_part)

        assert "SAMPLE AGREEMENT" in result
        assert "CONFIDENTIALITY" in result

    @pytest.mark.asyncio
    async def test_parse_text_preserves_content(self) -> None:
        """Test that text content is preserved correctly."""
        file_part = create_text_file_part()

        result = await parse_document(file_part)

        # Check content matches (strip to handle trailing whitespace)
        assert result.strip() == SAMPLE_TXT_CONTENT.strip()

    @pytest.mark.asyncio
    async def test_unsupported_mime_type_raises_error(self) -> None:
        """Test that unsupported MIME types raise UnsupportedFileTypeError."""
        file_part = create_file_part(
            mime_type="application/x-unknown",
            data_base64=SAMPLE_TXT_BASE64,
            name="unknown.xyz",
        )

        with pytest.raises(UnsupportedFileTypeError) as exc_info:
            await parse_document(file_part)

        assert "Unsupported file type" in str(exc_info.value)
        assert "application/x-unknown" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_data_uri_raises_error(self) -> None:
        """Test that invalid data URI format raises DocumentParserError."""
        file_part = {
            "uri": "not-a-data-uri",
            "mimeType": "text/plain",
            "name": "test.txt",
        }

        with pytest.raises(DocumentParserError) as exc_info:
            await parse_document(file_part)

        assert "Only data URIs are currently supported" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_base64_raises_error(self) -> None:
        """Test that invalid base64 data raises DocumentParserError."""
        file_part = {
            "uri": "data:text/plain;base64,not-valid-base64!!!",
            "mimeType": "text/plain",
            "name": "test.txt",
        }

        with pytest.raises(DocumentParserError) as exc_info:
            await parse_document(file_part)

        # Error could be about base64 decode or URI format
        error_msg = str(exc_info.value).lower()
        assert "base64" in error_msg or "uri" in error_msg or "padding" in error_msg

    @pytest.mark.asyncio
    async def test_empty_text_file(self) -> None:
        """Test parsing an empty text file."""
        empty_base64 = base64.b64encode(b"").decode()
        file_part = create_file_part(
            mime_type="text/plain",
            data_base64=empty_base64,
            name="empty.txt",
        )

        result = await parse_document(file_part)

        assert result == ""

    @pytest.mark.asyncio
    async def test_missing_mime_type_raises_error(self) -> None:
        """Test that missing MIME type raises UnsupportedFileTypeError."""
        file_part = {
            "uri": f"data:text/plain;base64,{SAMPLE_TXT_BASE64}",
            "name": "test.txt",
            # mimeType is missing
        }

        with pytest.raises(UnsupportedFileTypeError):
            await parse_document(file_part)

    @pytest.mark.asyncio
    async def test_utf8_text_encoding(self) -> None:
        """Test that UTF-8 encoded text is parsed correctly."""
        unicode_text = "Contract with unicode: café résumé naïve"
        unicode_base64 = base64.b64encode(unicode_text.encode("utf-8")).decode()
        file_part = create_file_part(
            mime_type="text/plain",
            data_base64=unicode_base64,
            name="unicode.txt",
        )

        result = await parse_document(file_part)

        assert result == unicode_text

    @pytest.mark.asyncio
    async def test_latin1_text_encoding(self) -> None:
        """Test that Latin-1 encoded text is parsed correctly."""
        # Text that's valid Latin-1 but not valid UTF-8
        latin1_text = "Contract with special chars: \xe9\xe8\xe0"
        latin1_bytes = latin1_text.encode("latin-1")
        latin1_base64 = base64.b64encode(latin1_bytes).decode()
        file_part = create_file_part(
            mime_type="text/plain",
            data_base64=latin1_base64,
            name="latin1.txt",
        )

        result = await parse_document(file_part)

        # Should decode successfully (might use latin-1 fallback)
        assert len(result) > 0


class TestSupportedMimeTypes:
    """Tests for MIME type support."""

    @pytest.mark.asyncio
    async def test_pdf_mime_type_recognized(self) -> None:
        """Test that PDF MIME type is recognized (may fail to parse minimal PDF)."""
        # Use text content but PDF mime type - will fail parsing but should not
        # raise UnsupportedFileTypeError
        file_part = create_file_part(
            mime_type="application/pdf",
            data_base64=SAMPLE_TXT_BASE64,  # Invalid PDF content
            name="fake.pdf",
        )

        # Should raise DocumentParserError (parse error), not UnsupportedFileTypeError
        with pytest.raises(DocumentParserError) as exc_info:
            await parse_document(file_part)

        assert "UnsupportedFileType" not in type(exc_info.value).__name__

    @pytest.mark.asyncio
    async def test_docx_mime_type_recognized(self) -> None:
        """Test that DOCX MIME type is recognized."""
        file_part = create_file_part(
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            data_base64=SAMPLE_TXT_BASE64,  # Invalid DOCX content
            name="fake.docx",
        )

        # Should raise DocumentParserError, not UnsupportedFileTypeError
        with pytest.raises(DocumentParserError) as exc_info:
            await parse_document(file_part)

        assert "UnsupportedFileType" not in type(exc_info.value).__name__

    @pytest.mark.asyncio
    async def test_msword_mime_type_recognized(self) -> None:
        """Test that legacy MS Word MIME type is recognized."""
        file_part = create_file_part(
            mime_type="application/msword",
            data_base64=SAMPLE_TXT_BASE64,  # Invalid DOC content
            name="fake.doc",
        )

        # Should raise DocumentParserError, not UnsupportedFileTypeError
        with pytest.raises(DocumentParserError) as exc_info:
            await parse_document(file_part)

        assert "UnsupportedFileType" not in type(exc_info.value).__name__
