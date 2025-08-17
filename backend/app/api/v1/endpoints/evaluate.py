from fastapi import UploadFile, File, APIRouter
from typing import List
import pandas as pd
from io import StringIO
from pydantic import BaseModel

router = APIRouter()


class EvaluationResultRequest(BaseModel):
    questions: List[str]
    ground_truths: List[str]


class EvaluationScore(BaseModel):
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    overall_score: float


class EvaluationResultResponse(BaseModel):
    scores: EvaluationScore


@router.post("/evaluation/upload_dataset", operation_id="upload_dataset_v1")
async def upload_dataset_v1(file: UploadFile = File(...)):
    # contents = await file.read()
    # df = pd.read_csv(StringIO(contents.decode("utf-8")))

    # # Validate columns
    # if "question" not in df.columns or "ground_truth" not in df.columns:
    #     return {"error": "CSV must include 'question' and 'ground_truth' columns"}

    # # Save or return parsed data
    # return {"message": f"Loaded {len(df)} samples"}
    return []


@router.post(
    "/evaluation/run",
    response_model=EvaluationResultResponse,
    operation_id="run_evaluation_v1",
)
async def run_evaluation_v1(request: EvaluationResultRequest):
    # result = run_ragas_evaluation(
    #     questions=request.questions, ground_truths=request.ground_truths
    # )
    # return result
    return []


@router.get(
    "/evaluation/last_result",
    response_model=EvaluationResultResponse,
    operation_id="get_last_result",
)
async def get_last_result():
    return []


@router.get(
    "/evaluation/scores",
    response_model=EvaluationResultResponse,
    operation_id="get_scores",
)
async def get_scores():
    return []
