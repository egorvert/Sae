"""Mock LLM responses for testing."""

# Valid clause extraction response (with markdown wrapper)
MOCK_CLAUSE_EXTRACTION_JSON = """```json
[
    {
        "type": "confidentiality",
        "title": "Confidentiality",
        "text": "The Receiving Party agrees to hold in confidence all Confidential Information disclosed by the Disclosing Party.",
        "location": "Section 1"
    },
    {
        "type": "liability",
        "title": "Limitation of Liability",
        "text": "IN NO EVENT SHALL PROVIDER BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES.",
        "location": "Section 3"
    },
    {
        "type": "termination",
        "title": "Termination",
        "text": "Either party may terminate this Agreement with sixty (60) days written notice.",
        "location": "Section 6"
    }
]
```"""

# Valid clause extraction response (plain JSON, no markdown)
MOCK_CLAUSE_EXTRACTION_PLAIN_JSON = """[
    {
        "type": "confidentiality",
        "title": "Confidentiality",
        "text": "All information shall remain confidential.",
        "location": "Section 1"
    }
]"""

# Risk analysis response (with markdown wrapper)
MOCK_RISK_ANALYSIS_JSON = """```json
[
    {
        "clause_id": "clause-001",
        "risk_level": "high",
        "confidence": 0.85,
        "issues": [
            "Unlimited liability exposure",
            "No cap on damages"
        ],
        "explanation": "This clause exposes the client to significant financial risk as there is no limitation on the types or amounts of damages that may be claimed.",
        "affected_party": "client"
    },
    {
        "clause_id": "clause-002",
        "risk_level": "low",
        "confidence": 0.92,
        "issues": [],
        "explanation": "Standard confidentiality clause with reasonable time limits.",
        "affected_party": "both"
    },
    {
        "clause_id": "clause-003",
        "risk_level": "medium",
        "confidence": 0.78,
        "issues": [
            "Short termination notice period"
        ],
        "explanation": "60-day notice period may not provide sufficient time to transition services.",
        "affected_party": "client"
    }
]
```"""

# Risk analysis with critical risk
MOCK_RISK_ANALYSIS_CRITICAL_JSON = """```json
[
    {
        "clause_id": "clause-001",
        "risk_level": "critical",
        "confidence": 0.95,
        "issues": [
            "One-sided indemnification",
            "Unlimited scope",
            "Includes attorney fees"
        ],
        "explanation": "This indemnification clause is heavily one-sided and exposes the client to unlimited liability for any claims, regardless of fault.",
        "affected_party": "client"
    }
]
```"""

# Recommendations response
MOCK_RECOMMENDATIONS_JSON = """```json
[
    {
        "clause_id": "clause-001",
        "priority": 1,
        "action": "Add mutual liability cap",
        "rationale": "Limits exposure for both parties and provides predictable risk allocation.",
        "suggested_text": "Neither party shall be liable for any amount exceeding the total fees paid under this Agreement in the twelve (12) months preceding the claim.",
        "risk_reduction": "medium"
    },
    {
        "clause_id": "clause-003",
        "priority": 2,
        "action": "Extend termination notice period",
        "rationale": "Provides adequate time for transition planning.",
        "suggested_text": "Either party may terminate this Agreement with ninety (90) days written notice.",
        "risk_reduction": "low"
    },
    {
        "clause_id": "clause-002",
        "priority": 5,
        "action": "No changes recommended",
        "rationale": "Clause is standard and balanced.",
        "suggested_text": null,
        "risk_reduction": null
    }
]
```"""

# Empty responses
MOCK_EMPTY_CLAUSES_JSON = "[]"
MOCK_EMPTY_RISKS_JSON = "[]"
MOCK_EMPTY_RECOMMENDATIONS_JSON = "[]"

# Malformed responses for error testing
MOCK_MALFORMED_JSON = "This is not valid JSON at all"
MOCK_PARTIAL_JSON = '[{"type": "liability", "title":'
MOCK_INVALID_STRUCTURE_JSON = '{"clauses": [], "invalid": true}'

# Response with unknown clause type (should default to OTHER)
MOCK_UNKNOWN_CLAUSE_TYPE_JSON = """[
    {
        "type": "unknown_type_xyz",
        "title": "Unknown Clause",
        "text": "Some clause text here.",
        "location": "Section 99"
    }
]"""

# Response with invalid risk level (should default to LOW)
MOCK_INVALID_RISK_LEVEL_JSON = """[
    {
        "clause_id": "clause-001",
        "risk_level": "super_critical_extreme",
        "confidence": 0.5,
        "issues": [],
        "explanation": "Test clause",
        "affected_party": "both"
    }
]"""

# Response with out-of-range confidence (should be clamped)
MOCK_OUT_OF_RANGE_CONFIDENCE_JSON = """[
    {
        "clause_id": "clause-001",
        "risk_level": "high",
        "confidence": 1.5,
        "issues": ["Test issue"],
        "explanation": "Confidence is above 1.0",
        "affected_party": "client"
    },
    {
        "clause_id": "clause-002",
        "risk_level": "low",
        "confidence": -0.5,
        "issues": [],
        "explanation": "Confidence is below 0.0",
        "affected_party": "vendor"
    }
]"""

# Response with out-of-range priority (should be clamped)
MOCK_OUT_OF_RANGE_PRIORITY_JSON = """[
    {
        "clause_id": "clause-001",
        "priority": 0,
        "action": "Priority too low",
        "rationale": "Should be clamped to 1",
        "suggested_text": null,
        "risk_reduction": null
    },
    {
        "clause_id": "clause-002",
        "priority": 10,
        "action": "Priority too high",
        "rationale": "Should be clamped to 5",
        "suggested_text": null,
        "risk_reduction": null
    }
]"""

# Response with missing fields (should use defaults)
MOCK_MISSING_FIELDS_JSON = """[
    {
        "type": "liability"
    }
]"""

# Nested markdown code blocks
MOCK_NESTED_MARKDOWN_JSON = """Here's the analysis:

```json
[
    {
        "type": "warranty",
        "title": "Warranty",
        "text": "Standard warranty clause.",
        "location": "Section 7"
    }
]
```

That's the complete list of clauses found."""
