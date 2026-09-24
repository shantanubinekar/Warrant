"""
API Routes — FastAPI endpoints for the Warrant system.

Endpoints:
  GET  /api/scenarios           — list all 6 demo scenarios
  GET  /api/scenarios/{id}      — get a specific demo scenario
  POST /api/scenarios/{id}/analyze — run a demo scenario through the full pipeline
  POST /api/analyze             — analyze a custom patient case (JSON)
  POST /api/upload              — upload clinical text for extraction + analysis
  POST /api/upload-file         — upload a PDF/DOCX/TXT report or prescription
  POST /api/ask                 — ask a free-form question about an analyzed case
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from backend.scenarios.demo_cases import DemoScenarios
from backend.pipeline.orchestrator import PipelineOrchestrator
from backend.schemas.patient_evidence import PatientCase
from backend.llm.llm_client import LLMClient
from backend.document.extractor import extract_text, UnsupportedDocumentError

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize pipeline — LLM client is optional
try:
    llm_client = LLMClient()
    if not llm_client.available:
        llm_client = None
        logger.info("LLM client not available — using template fallback for explanations")
except Exception:
    llm_client = None
    logger.info("LLM client initialization failed — using template fallback")

pipeline = PipelineOrchestrator(llm_client=llm_client)


# ── Request/Response models ──────────────────────────────────────────

class UploadRequest(BaseModel):
    """Request body for clinical text upload."""
    clinical_text: str
    case_description: Optional[str] = None


class ScenarioSummary(BaseModel):
    """Summary of a demo scenario for listing."""
    id: int
    title: str
    description: str
    target_state: str


class AskRequest(BaseModel):
    """Request body for asking a question about an already-analyzed case."""
    question: str
    case_id: Optional[str] = None
    # The reasoning_result portion of a previous /analyze, /upload, or
    # /scenarios/{id}/analyze response — sent back by the frontend as
    # grounding context. Accepted as a loose dict since it's just passed
    # through to the LLM as JSON, not re-validated against the schema.
    reasoning_result: dict


class AskResponse(BaseModel):
    answer: str


def _require_llm():
    if llm_client is None or not llm_client.available:
        raise HTTPException(
            status_code=503,
            detail=(
                "LLM client is not available. Set the GROQ_API_KEY environment "
                "variable and install the groq package to enable this feature."
            ),
        )


# ── Scenario endpoints ───────────────────────────────────────────────

@router.get("/scenarios")
def list_scenarios():
    """List all 6 demo scenarios with summaries."""
    scenarios = DemoScenarios.get_all_scenarios()
    return [
        ScenarioSummary(
            id=s["id"],
            title=s["title"],
            description=s["description"],
            target_state=s["target_state"],
        )
        for s in scenarios
    ]


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: int):
    """Get a specific demo scenario by ID."""
    try:
        scenario = DemoScenarios.get_scenario(scenario_id)
        return {
            "id": scenario["id"],
            "title": scenario["title"],
            "description": scenario["description"],
            "target_state": scenario["target_state"],
            "patient_case": scenario["patient_case"].model_dump(mode="json"),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/scenarios/{scenario_id}/analyze")
def analyze_scenario(scenario_id: int):
    """Run a demo scenario through the full reasoning pipeline.

    The scenario runs through the SAME reasoning engine as any other input.
    No hardcoded per-case return values.
    """
    try:
        scenario = DemoScenarios.get_scenario(scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    patient_case = scenario["patient_case"]
    logger.info(f"Analyzing scenario {scenario_id}: {scenario['title']}")

    try:
        response = pipeline.run_pipeline(patient_case)
        return {
            "scenario": {
                "id": scenario["id"],
                "title": scenario["title"],
                "description": scenario["description"],
                "target_state": scenario["target_state"],
            },
            "analysis": response.model_dump(mode="json"),
        }
    except Exception as e:
        logger.error(f"Pipeline error for scenario {scenario_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


# ── Custom analysis endpoint ─────────────────────────────────────────

@router.post("/analyze")
def analyze_custom_case(case: PatientCase):
    """Analyze a custom patient case submitted as JSON.

    The case goes through the same pipeline as demo scenarios.
    """
    logger.info(f"Analyzing custom case: {case.case_id}")

    try:
        response = pipeline.run_pipeline(case)
        return response.model_dump(mode="json")
    except Exception as e:
        logger.error(f"Pipeline error for custom case {case.case_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


# ── Shared extraction + pipeline helper ──────────────────────────────

def _extract_and_analyze(clinical_text: str, case_description: Optional[str]) -> dict:
    """Run LLM extraction then the deterministic pipeline over clinical text.

    Shared by both the pasted-text upload and the file upload endpoints so
    they behave identically once text is in hand.
    """
    patient_case = llm_client.extract_evidence(clinical_text)
    if patient_case is None:
        raise HTTPException(
            status_code=422,
            detail="Failed to extract structured evidence from the provided text",
        )

    if case_description:
        patient_case.case_description = case_description

    try:
        response = pipeline.run_pipeline(patient_case)
    except Exception as e:
        logger.error(f"Pipeline error for uploaded text: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

    return {
        "extracted_case": patient_case.model_dump(mode="json"),
        "analysis": response.model_dump(mode="json"),
    }


# ── Text upload endpoint (Mode B) ────────────────────────────────────

@router.post("/upload")
def upload_clinical_text(request: UploadRequest):
    """Upload clinical text for LLM extraction + pipeline analysis.

    Mode B: custom document upload → LLM extraction → same pipeline.
    Requires LLM client to be available.
    """
    _require_llm()
    logger.info("Extracting evidence from uploaded clinical text")
    return _extract_and_analyze(request.clinical_text, request.case_description)


# ── File upload endpoint (PDF / DOCX / TXT prescriptions & reports) ──

@router.post("/upload-file")
async def upload_clinical_file(
    file: UploadFile = File(...),
    case_description: Optional[str] = Form(None),
):
    """Upload a prescription/report FILE (PDF, DOCX, or TXT) for extraction.

    The file's text is pulled out server-side, then run through the exact
    same LLM extraction + deterministic pipeline as /api/upload.
    """
    _require_llm()

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    try:
        clinical_text = extract_text(file.filename or "upload", content)
    except UnsupportedDocumentError as e:
        raise HTTPException(status_code=422, detail=str(e))

    logger.info(f"Extracting evidence from uploaded file: {file.filename}")
    return _extract_and_analyze(clinical_text, case_description)


# ── Ask-about-this-case endpoint ─────────────────────────────────────

@router.post("/ask", response_model=AskResponse)
def ask_about_case(request: AskRequest):
    """Answer a free-form question about an already-analyzed case.

    This does NOT go through the deterministic reasoning engine — it's a
    separate, honest, best-effort LLM answer grounded only in that case's
    reasoning result. If the question is outside what this case's evidence
    can support (e.g. asking about an unrelated condition), the model is
    instructed to say so plainly instead of guessing.
    """
    _require_llm()

    if not request.question.strip():
        raise HTTPException(status_code=422, detail="Question cannot be empty")

    try:
        answer = llm_client.answer_case_question(
            question=request.question,
            case_context_json=json.dumps(request.reasoning_result, indent=2),
        )
    except Exception as e:
        logger.error(f"Case Q&A failed: {e}")
        raise HTTPException(status_code=500, detail=f"Q&A failed: {str(e)}")

    return AskResponse(answer=answer)
