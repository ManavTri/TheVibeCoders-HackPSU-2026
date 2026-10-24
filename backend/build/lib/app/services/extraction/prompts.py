"""Extraction guidance for future LLM-backed document parsing."""

EXTRACTION_INSTRUCTIONS = """
Extract only facts explicitly present in the document. Return amount (numeric),
currency, academic term, payment deadline (ISO date), and minimum credit
requirement. Use null for absent or ambiguous values. Never infer eligibility.
"""
