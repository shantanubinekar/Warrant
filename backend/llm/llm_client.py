"""
LLM Client — Abstraction over Groq for extraction and explanation.

The LLM is asked to extract, structure, and explain.
It is NEVER asked to determine the evidence state or make clinical decisions.

If no API key is configured, all methods gracefully return None/fallback.

Swapping providers later: Groq's SDK follows the OpenAI-compatible
chat-completions interface, so any future model swap only needs a
GROQ_MODEL change in .env — no code changes needed here.
"""

import json
import logging
import os
import traceback
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Optional import — system works without LLM
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.info("groq not installed — LLM features disabled")

from backend.schemas.patient_evidence import (
    PatientCase, TroponinEvidence, ECGEvidence, SymptomsEvidence,
    ClinicalHistory, TimingEvidence, VerificationStatus,
)
from backend.schemas.engine_output import ReasoningResult, StateAction
from backend.llm.prompts import (
    EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_TEMPLATE,
    EXPLANATION_SYSTEM_PROMPT, EXPLANATION_USER_TEMPLATE,
)


class LLMClient:
    """LLM client wrapping the Groq SDK (OpenAI-compatible chat completions).

    Two capabilities:
      1. extract_evidence(text) → PatientCase
      2. generate_explanation(reasoning_result, action) → str

    Gracefully degrades when API key is missing or SDK unavailable.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        # Model is also env-configurable so a future model swap needs no
        # code change either — just GROQ_MODEL in .env.
        self.model_name = model_name or os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
        self.available = False
        self.client = None

        api_key = api_key or os.environ.get("GROQ_API_KEY")

        if not GROQ_AVAILABLE:
            logger.warning("LLM client: groq not available")
            return

        if not api_key:
            logger.warning("LLM client: no API key configured (set GROQ_API_KEY)")
            return

        try:
            self.client = Groq(api_key=api_key)
            self.available = True
            logger.info(f"LLM client initialized with model: {self.model_name}")
        except Exception as e:
            logger.error(f"LLM client initialization failed: {e}\n{traceback.format_exc()}")

    def extract_evidence(self, clinical_text: str) -> Optional[PatientCase]:
        """Extract structured patient evidence from clinical text.

        Args:
            clinical_text: Raw clinical text (lab report, notes, etc.)

        Returns:
            PatientCase with extracted evidence, or None if extraction fails.
        """
        if not self.available:
            logger.warning("LLM not available — cannot extract evidence")
            return None

        try:
            prompt = EXTRACTION_USER_TEMPLATE.format(clinical_text=clinical_text)

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            raw_json = (response.choices[0].message.content or "").strip()
            if not raw_json:
                logger.error("LLM extraction returned empty response (check finish_reason)")
                return None

            extracted = json.loads(raw_json)

            return self._build_patient_case(extracted, source=f"llm_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM extraction JSON: {e}")
            return None
        except Exception as e:
            # Full traceback so real auth/model/quota errors are visible in
            # the server logs instead of collapsing into a generic 422.
            logger.error(f"LLM extraction failed: {e}\n{traceback.format_exc()}")
            return None

    def generate_explanation(
        self,
        reasoning_result: ReasoningResult,
        action: StateAction,
    ) -> str:
        """Generate human-readable explanation from the reasoning result.

        The LLM is constrained to ONLY the authoritative structured state.
        It must not invent stronger conclusions than supported_claims allows.

        Args:
            reasoning_result: Authoritative state from the reasoning engine.
            action: Mapped action from the state-action mapper.

        Returns:
            Explanation text.

        Raises:
            RuntimeError: If LLM is unavailable.
        """
        if not self.available:
            raise RuntimeError("LLM not available for explanation generation")

        reasoning_json = reasoning_result.model_dump_json(indent=2)
        action_json = action.model_dump_json(indent=2)

        prompt = EXPLANATION_USER_TEMPLATE.format(
            reasoning_result_json=reasoning_json,
            action_json=action_json,
        )

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": EXPLANATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        raw_text = (response.choices[0].message.content or "").strip()
        return self._strip_markdown(raw_text)

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """Defensive cleanup in case the LLM still emits markdown syntax
        despite the plain-text instruction (headers, bullets, bold)."""
        import re
        text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)  # headers
        text = re.sub(r"^[\*\-]\s+", "", text, flags=re.MULTILINE)  # bullets
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # bold
        text = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"\1", text)  # italics
        return text

    def _build_patient_case(self, extracted: dict, source: str) -> PatientCase:
        """Convert extracted JSON into a PatientCase."""
        case = PatientCase(
            case_id=f"extracted_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            case_description="Extracted from uploaded clinical text via LLM",
        )

        # Troponin
        trop = extracted.get("troponin")
        if trop and trop.get("value") is not None:
            serial = None
            if trop.get("serial_values"):
                serial = [
                    {"value": sv.get("value"), "timestamp": sv.get("timestamp")}
                    for sv in trop["serial_values"]
                    if sv.get("value") is not None
                ]

            case.troponin = TroponinEvidence(
                value=float(trop["value"]) if trop["value"] is not None else None,
                unit=trop.get("unit"),
                assay=trop.get("assay"),
                serial_values=serial if serial else None,
                extraction_confidence=float(trop.get("extraction_confidence", 0.0)),
                extraction_source=source,
                verification_status=VerificationStatus.UNVERIFIED,
                schema_valid=True,
            )

        # ECG
        ecg = extracted.get("ecg")
        if ecg and ecg.get("interpretation"):
            case.ecg = ECGEvidence(
                interpretation=ecg.get("interpretation"),
                st_elevation=ecg.get("st_elevation"),
                st_depression=ecg.get("st_depression"),
                q_waves=ecg.get("q_waves"),
                quality=ecg.get("quality"),
                extraction_confidence=float(ecg.get("extraction_confidence", 0.0)),
                extraction_source=source,
                verification_status=VerificationStatus.UNVERIFIED,
                schema_valid=True,
            )

        # Symptoms
        symp = extracted.get("symptoms")
        if symp and symp.get("chest_pain") is not None:
            case.symptoms = SymptomsEvidence(
                chest_pain=symp.get("chest_pain"),
                characteristics=symp.get("characteristics"),
                duration_minutes=float(symp["duration_minutes"]) if symp.get("duration_minutes") else None,
                radiation=symp.get("radiation"),
                associated_symptoms=symp.get("associated_symptoms"),
                extraction_confidence=float(symp.get("extraction_confidence", 0.0)),
                extraction_source=source,
                verification_status=VerificationStatus.UNVERIFIED,
                schema_valid=True,
            )

        # Clinical history
        hist = extracted.get("clinical_history")
        if hist and (hist.get("age") or hist.get("sex")):
            case.clinical_history = ClinicalHistory(
                age=int(hist["age"]) if hist.get("age") else None,
                sex=hist.get("sex"),
                diabetes=hist.get("diabetes"),
                hypertension=hist.get("hypertension"),
                smoking=hist.get("smoking"),
                prior_mi=hist.get("prior_mi"),
                extraction_confidence=float(hist.get("extraction_confidence", 0.0)),
                extraction_source=source,
                verification_status=VerificationStatus.UNVERIFIED,
                schema_valid=True,
            )

        # Timing
        timing = extracted.get("timing")
        if timing and (timing.get("symptom_onset") or timing.get("presentation_time")
                       or timing.get("serial_sample_spacing_minutes") is not None):
            case.timing = TimingEvidence(
                serial_sample_spacing_minutes=timing.get("serial_sample_spacing_minutes"),
                extraction_confidence=float(timing.get("extraction_confidence", 0.0)),
                extraction_source=source,
                verification_status=VerificationStatus.UNVERIFIED,
                schema_valid=True,
            )

        return case
