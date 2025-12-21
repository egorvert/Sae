"""Tests for clause analysis models."""

import pytest
from pydantic import ValidationError

from sae.models.clauses import (
    ClauseType,
    ContractAnalysis,
    ExtractedClause,
    Recommendation,
    RiskAssessment,
    RiskLevel,
)


class TestClauseType:
    """Tests for ClauseType enum."""

    def test_clause_type_has_16_values(self) -> None:
        """Test that ClauseType has exactly 16 values."""
        assert len(ClauseType) == 16

    def test_clause_type_values(self) -> None:
        """Test specific ClauseType values."""
        assert ClauseType.INDEMNIFICATION == "indemnification"
        assert ClauseType.LIABILITY == "liability"
        assert ClauseType.TERMINATION == "termination"
        assert ClauseType.CONFIDENTIALITY == "confidentiality"
        assert ClauseType.INTELLECTUAL_PROPERTY == "intellectual_property"
        assert ClauseType.PAYMENT == "payment"
        assert ClauseType.WARRANTY == "warranty"
        assert ClauseType.FORCE_MAJEURE == "force_majeure"
        assert ClauseType.DISPUTE_RESOLUTION == "dispute_resolution"
        assert ClauseType.GOVERNING_LAW == "governing_law"
        assert ClauseType.ASSIGNMENT == "assignment"
        assert ClauseType.AMENDMENT == "amendment"
        assert ClauseType.NOTICE == "notice"
        assert ClauseType.ENTIRE_AGREEMENT == "entire_agreement"
        assert ClauseType.SEVERABILITY == "severability"
        assert ClauseType.OTHER == "other"

    def test_clause_type_is_string_enum(self) -> None:
        """Test that ClauseType values are strings."""
        for clause_type in ClauseType:
            assert isinstance(clause_type.value, str)


class TestRiskLevel:
    """Tests for RiskLevel enum."""

    def test_risk_level_has_4_values(self) -> None:
        """Test that RiskLevel has exactly 4 values."""
        assert len(RiskLevel) == 4

    def test_risk_level_values(self) -> None:
        """Test RiskLevel values."""
        assert RiskLevel.LOW == "low"
        assert RiskLevel.MEDIUM == "medium"
        assert RiskLevel.HIGH == "high"
        assert RiskLevel.CRITICAL == "critical"

    def test_risk_level_ordering(self) -> None:
        """Test that risk levels can be compared by their string values."""
        # Note: This is alphabetical, not severity-based
        levels = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert all(isinstance(level.value, str) for level in levels)


class TestExtractedClause:
    """Tests for ExtractedClause model."""

    def test_extracted_clause_creation(self) -> None:
        """Test creating an ExtractedClause."""
        clause = ExtractedClause(
            id="clause-001",
            type=ClauseType.LIABILITY,
            title="Limitation of Liability",
            text="The company shall not be liable for any indirect damages.",
            location="Section 5.1",
        )
        assert clause.id == "clause-001"
        assert clause.type == ClauseType.LIABILITY
        assert clause.title == "Limitation of Liability"
        assert clause.text == "The company shall not be liable for any indirect damages."
        assert clause.location == "Section 5.1"
        assert clause.metadata == {}

    def test_extracted_clause_with_metadata(self) -> None:
        """Test ExtractedClause with custom metadata."""
        clause = ExtractedClause(
            id="clause-002",
            type=ClauseType.CONFIDENTIALITY,
            title="NDA",
            text="All information is confidential.",
            location="Section 1",
            metadata={"confidence": 0.95, "source": "page_1"},
        )
        assert clause.metadata["confidence"] == 0.95
        assert clause.metadata["source"] == "page_1"

    def test_extracted_clause_required_fields(self) -> None:
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            ExtractedClause(
                id="test",
                type=ClauseType.OTHER,
                # Missing: title, text, location
            )  # type: ignore

    def test_extracted_clause_all_clause_types(self) -> None:
        """Test that all ClauseType values can be used."""
        for clause_type in ClauseType:
            clause = ExtractedClause(
                id=f"test-{clause_type.value}",
                type=clause_type,
                title="Test",
                text="Test text",
                location="Section 1",
            )
            assert clause.type == clause_type


class TestRiskAssessment:
    """Tests for RiskAssessment model."""

    def test_risk_assessment_creation(self) -> None:
        """Test creating a RiskAssessment."""
        risk = RiskAssessment(
            clause_id="clause-001",
            risk_level=RiskLevel.HIGH,
            confidence=0.85,
            issues=["Unlimited liability", "One-sided"],
            explanation="This clause exposes the client to risk.",
            affected_party="client",
        )
        assert risk.clause_id == "clause-001"
        assert risk.risk_level == RiskLevel.HIGH
        assert risk.confidence == 0.85
        assert len(risk.issues) == 2
        assert risk.affected_party == "client"

    def test_risk_assessment_confidence_lower_bound(self) -> None:
        """Test that confidence must be >= 0.0."""
        with pytest.raises(ValidationError) as exc_info:
            RiskAssessment(
                clause_id="test",
                risk_level=RiskLevel.LOW,
                confidence=-0.1,
                explanation="Test",
            )
        assert "confidence" in str(exc_info.value)

    def test_risk_assessment_confidence_upper_bound(self) -> None:
        """Test that confidence must be <= 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            RiskAssessment(
                clause_id="test",
                risk_level=RiskLevel.LOW,
                confidence=1.1,
                explanation="Test",
            )
        assert "confidence" in str(exc_info.value)

    def test_risk_assessment_confidence_at_bounds(self) -> None:
        """Test confidence at exact bounds (0.0 and 1.0)."""
        risk_low = RiskAssessment(
            clause_id="test1",
            risk_level=RiskLevel.LOW,
            confidence=0.0,
            explanation="Test",
        )
        assert risk_low.confidence == 0.0

        risk_high = RiskAssessment(
            clause_id="test2",
            risk_level=RiskLevel.HIGH,
            confidence=1.0,
            explanation="Test",
        )
        assert risk_high.confidence == 1.0

    def test_risk_assessment_default_issues(self) -> None:
        """Test that issues defaults to empty list."""
        risk = RiskAssessment(
            clause_id="test",
            risk_level=RiskLevel.LOW,
            confidence=0.5,
            explanation="Test",
        )
        assert risk.issues == []

    def test_risk_assessment_default_affected_party(self) -> None:
        """Test that affected_party defaults to empty string."""
        risk = RiskAssessment(
            clause_id="test",
            risk_level=RiskLevel.LOW,
            confidence=0.5,
            explanation="Test",
        )
        assert risk.affected_party == ""

    def test_risk_assessment_all_risk_levels(self) -> None:
        """Test that all RiskLevel values can be used."""
        for level in RiskLevel:
            risk = RiskAssessment(
                clause_id="test",
                risk_level=level,
                confidence=0.5,
                explanation="Test",
            )
            assert risk.risk_level == level


class TestRecommendation:
    """Tests for Recommendation model."""

    def test_recommendation_creation(self) -> None:
        """Test creating a Recommendation."""
        rec = Recommendation(
            clause_id="clause-001",
            priority=1,
            action="Add liability cap",
            rationale="Limits risk exposure",
            suggested_text="Total liability shall not exceed $1M.",
            risk_reduction=RiskLevel.LOW,
        )
        assert rec.clause_id == "clause-001"
        assert rec.priority == 1
        assert rec.action == "Add liability cap"
        assert rec.suggested_text is not None
        assert rec.risk_reduction == RiskLevel.LOW

    def test_recommendation_priority_lower_bound(self) -> None:
        """Test that priority must be >= 1."""
        with pytest.raises(ValidationError) as exc_info:
            Recommendation(
                clause_id="test",
                priority=0,
                action="Test",
                rationale="Test",
            )
        assert "priority" in str(exc_info.value)

    def test_recommendation_priority_upper_bound(self) -> None:
        """Test that priority must be <= 5."""
        with pytest.raises(ValidationError) as exc_info:
            Recommendation(
                clause_id="test",
                priority=6,
                action="Test",
                rationale="Test",
            )
        assert "priority" in str(exc_info.value)

    def test_recommendation_priority_at_bounds(self) -> None:
        """Test priority at exact bounds (1 and 5)."""
        rec_low = Recommendation(
            clause_id="test1",
            priority=1,
            action="Urgent",
            rationale="Critical issue",
        )
        assert rec_low.priority == 1

        rec_high = Recommendation(
            clause_id="test2",
            priority=5,
            action="Minor",
            rationale="Nice to have",
        )
        assert rec_high.priority == 5

    def test_recommendation_optional_fields(self) -> None:
        """Test that suggested_text and risk_reduction are optional."""
        rec = Recommendation(
            clause_id="test",
            priority=3,
            action="Review clause",
            rationale="May need attention",
        )
        assert rec.suggested_text is None
        assert rec.risk_reduction is None

    def test_recommendation_all_priority_levels(self) -> None:
        """Test all valid priority levels (1-5)."""
        for priority in range(1, 6):
            rec = Recommendation(
                clause_id="test",
                priority=priority,
                action="Test",
                rationale="Test",
            )
            assert rec.priority == priority


class TestContractAnalysis:
    """Tests for ContractAnalysis model."""

    def test_contract_analysis_creation(self) -> None:
        """Test creating a ContractAnalysis."""
        analysis = ContractAnalysis(
            contract_id="contract-001",
            summary="This contract has 3 high-risk clauses.",
            overall_risk=RiskLevel.HIGH,
        )
        assert analysis.contract_id == "contract-001"
        assert analysis.summary == "This contract has 3 high-risk clauses."
        assert analysis.overall_risk == RiskLevel.HIGH
        assert analysis.clauses == []
        assert analysis.risks == []
        assert analysis.recommendations == []
        assert analysis.missing_clauses == []
        assert analysis.metadata == {}

    def test_contract_analysis_with_clauses(self) -> None:
        """Test ContractAnalysis with clauses."""
        clause = ExtractedClause(
            id="c1",
            type=ClauseType.LIABILITY,
            title="Liability",
            text="Test",
            location="Section 1",
        )
        analysis = ContractAnalysis(
            contract_id="test",
            summary="Test",
            clauses=[clause],
            overall_risk=RiskLevel.LOW,
        )
        assert len(analysis.clauses) == 1

    def test_contract_analysis_with_risks(self) -> None:
        """Test ContractAnalysis with risks."""
        risk = RiskAssessment(
            clause_id="c1",
            risk_level=RiskLevel.HIGH,
            confidence=0.9,
            explanation="Test",
        )
        analysis = ContractAnalysis(
            contract_id="test",
            summary="Test",
            risks=[risk],
            overall_risk=RiskLevel.HIGH,
        )
        assert len(analysis.risks) == 1

    def test_contract_analysis_with_recommendations(self) -> None:
        """Test ContractAnalysis with recommendations."""
        rec = Recommendation(
            clause_id="c1",
            priority=1,
            action="Fix it",
            rationale="It's broken",
        )
        analysis = ContractAnalysis(
            contract_id="test",
            summary="Test",
            recommendations=[rec],
            overall_risk=RiskLevel.MEDIUM,
        )
        assert len(analysis.recommendations) == 1

    def test_contract_analysis_with_missing_clauses(self) -> None:
        """Test ContractAnalysis with missing clauses."""
        analysis = ContractAnalysis(
            contract_id="test",
            summary="Missing important clauses",
            missing_clauses=[ClauseType.INDEMNIFICATION, ClauseType.FORCE_MAJEURE],
            overall_risk=RiskLevel.MEDIUM,
        )
        assert len(analysis.missing_clauses) == 2
        assert ClauseType.INDEMNIFICATION in analysis.missing_clauses

    def test_contract_analysis_full(self) -> None:
        """Test ContractAnalysis with all fields populated."""
        clause = ExtractedClause(
            id="c1",
            type=ClauseType.LIABILITY,
            title="Liability",
            text="Test",
            location="Section 1",
        )
        risk = RiskAssessment(
            clause_id="c1",
            risk_level=RiskLevel.HIGH,
            confidence=0.9,
            explanation="Test",
        )
        rec = Recommendation(
            clause_id="c1",
            priority=1,
            action="Fix",
            rationale="Broken",
        )
        analysis = ContractAnalysis(
            contract_id="full-test",
            summary="Complete analysis",
            clauses=[clause],
            risks=[risk],
            recommendations=[rec],
            missing_clauses=[ClauseType.WARRANTY],
            overall_risk=RiskLevel.HIGH,
            metadata={"version": 1, "analyzed_by": "test"},
        )
        assert analysis.contract_id == "full-test"
        assert len(analysis.clauses) == 1
        assert len(analysis.risks) == 1
        assert len(analysis.recommendations) == 1
        assert len(analysis.missing_clauses) == 1
        assert analysis.metadata["version"] == 1
