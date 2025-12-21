"""Sample file data for testing document parsing."""

import base64

# Minimal valid PDF (1 page with "Test Contract" text)
# This is a minimal valid PDF structure
SAMPLE_PDF_BYTES = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Test Contract) Tj ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000266 00000 n
0000000359 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
434
%%EOF"""

SAMPLE_PDF_BASE64 = base64.b64encode(SAMPLE_PDF_BYTES).decode()

# Plain text sample
SAMPLE_TXT_CONTENT = """SAMPLE AGREEMENT

1. CONFIDENTIALITY
The parties agree to maintain confidentiality.

2. TERM
This agreement is valid for one year.
"""

SAMPLE_TXT_BYTES = SAMPLE_TXT_CONTENT.encode("utf-8")
SAMPLE_TXT_BASE64 = base64.b64encode(SAMPLE_TXT_BYTES).decode()


def create_file_part(
    mime_type: str,
    data_base64: str,
    name: str = "test_file",
) -> dict:
    """Create a FilePart.file dictionary for testing.

    Args:
        mime_type: MIME type of the file
        data_base64: Base64-encoded file content
        name: Filename

    Returns:
        Dictionary matching FilePart.file structure
    """
    return {
        "uri": f"data:{mime_type};base64,{data_base64}",
        "mimeType": mime_type,
        "name": name,
    }


def create_pdf_file_part(name: str = "contract.pdf") -> dict:
    """Create a PDF FilePart for testing."""
    return create_file_part(
        mime_type="application/pdf",
        data_base64=SAMPLE_PDF_BASE64,
        name=name,
    )


def create_text_file_part(name: str = "contract.txt") -> dict:
    """Create a text FilePart for testing."""
    return create_file_part(
        mime_type="text/plain",
        data_base64=SAMPLE_TXT_BASE64,
        name=name,
    )
