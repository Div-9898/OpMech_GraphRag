"""
Processing module - Evidence retrieval, answer synthesis, and confidence calibration.
"""

from src.processing.evidence_retriever import EvidenceRetriever, EvidenceNode, EvidenceSet
from src.processing.answer_synthesizer import AnswerSynthesizer, OperatorOutput, SynthesizedAnswer, ValidationResult
from src.processing.confidence_calibrator import ConfidenceCalibrator, ConfidenceFactors

__all__ = [
    'EvidenceRetriever',
    'EvidenceNode',
    'EvidenceSet',
    'AnswerSynthesizer',
    'OperatorOutput',
    'SynthesizedAnswer',
    'ValidationResult',
    'ConfidenceCalibrator',
    'ConfidenceFactors',
]
