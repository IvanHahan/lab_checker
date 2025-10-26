"""Evaluation agent for grading student task submissions against requirements."""

import json
from typing import Any, Dict, List

from lab_checker.message_utils import prepare_message_with_visuals

from ..chains import chain_json_with_thinking
from ..llm import OpenAIModel


class TaskEvaluationAgent:
    """
    Agent responsible for evaluating student task submissions against assignment requirements.
    This agent provides objective scoring, feedback, and detailed assessment of student work.
    """

    def __init__(self, llm: OpenAIModel):
        self.llm = llm

    def evaluate_task_submission(
        self,
        task: Dict[str, Any],
        submission_analysis: Dict[str, Any],
        visual_context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate a student's task submission against task requirements.

        Args:
            task: Task specification from assignment
            submission_analysis: Analysis of student's submission for this task
            visual_context: Visual elements from submission if available

        Returns:
            Dictionary containing evaluation results, scores, and feedback
        """
        # Extract visual references from submission if present
        visual_references = submission_analysis.get("visual_references", [])
        visual_text = ""

        if visual_references and visual_context:
            for visual_ref in visual_references:
                tag = visual_ref.get("tag", "")
                description = visual_ref.get("description", "")
                if tag:
                    visual_text += f"\n{description}:\n{tag}\n"

        # Prepare visual content for evaluation
        visual_content = []
        if visual_context and visual_text:
            visual_content = prepare_message_with_visuals(
                text=visual_text,
                visuals=visual_context,
            )

        # Prepare message content
        message_content = [
            {
                "type": "input_text",
                "text": self.EVALUATE_PROMPT.format(
                    task_description=json.dumps(task, ensure_ascii=False),
                    student_submission=json.dumps(
                        submission_analysis, ensure_ascii=False
                    ),
                ),
            },
            *visual_content,
        ]

        # Get evaluation from LLM
        response = chain_json_with_thinking(self.llm).invoke(
            "",
            messages=[
                {
                    "role": "user",
                    "content": message_content,
                },
            ],
        )

        return response

    def evaluate_multiple_tasks(
        self,
        tasks: List[Dict[str, Any]],
        submissions: List[Dict[str, Any]],
        visual_contexts: List[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Evaluate multiple task submissions.

        Args:
            tasks: List of task specifications
            submissions: List of submission analyses
            visual_contexts: List of visual contexts for each submission

        Returns:
            List of evaluation results for each task
        """
        evaluations = []
        visual_contexts = visual_contexts or [None] * len(tasks)

        for i, (task, submission) in enumerate(zip(tasks, submissions)):
            visual_context = visual_contexts[i] if i < len(visual_contexts) else None
            evaluation = self.evaluate_task_submission(task, submission, visual_context)
            evaluations.append(evaluation)

        return evaluations

    def save_evaluation(
        self, evaluation_data: Dict[str, Any], task_index: int, output_dir: str = "."
    ) -> None:
        """
        Save task evaluation results to a JSON file.

        Args:
            evaluation_data: Evaluation data from evaluate_task_submission
            task_index: Index of the task (for filename generation)
            output_dir: Directory where to save the evaluation JSON file
        """
        output_path = f"{output_dir}/task_{task_index}_eval.json"
        with open(output_path, "w") as f:
            f.write(evaluation_data.model_dump_json(indent=2, ensure_ascii=False))

    def generate_overall_grade(
        self, evaluations: List[Dict[str, Any]], weights: List[float] = None
    ) -> Dict[str, Any]:
        """
        Generate an overall grade based on individual task evaluations.

        Args:
            evaluations: List of task evaluation results
            weights: Optional weights for each task (defaults to equal weighting)

        Returns:
            Dictionary containing overall grade and summary
        """
        if not evaluations:
            return {"overall_grade": 0, "summary": "No evaluations provided"}

        # Default to equal weights if not provided
        if weights is None:
            weights = [1.0] * len(evaluations)

        # Normalize weights
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        # Calculate weighted average
        total_score = 0
        total_possible = 0

        for eval_data, weight in zip(evaluations, normalized_weights):
            task_result = eval_data.get("result", {})
            grade = float(task_result.get("grade", 0))
            total_score += grade * weight * 100  # Assuming grade is 0-100
            total_possible += weight * 100

        overall_grade = (
            (total_score / total_possible * 100) if total_possible > 0 else 0
        )

        return {
            "overall_grade": round(overall_grade, 2),
            "individual_scores": [
                {
                    "task_index": i,
                    "score": eval_data.get("result", {}).get("grade", 0),
                    "weight": weights[i],
                }
                for i, eval_data in enumerate(evaluations)
            ],
            "summary": f"Overall grade: {overall_grade:.2f}% based on {len(evaluations)} tasks",
        }

    @property
    def EVALUATE_PROMPT(self) -> str:
        """Prompt template for task evaluation."""
        return """
# Student Submission Evaluation Prompt
You are an expert at evaluating student submissions for laboratory assignments.
Your task is to evaluate the student's submission based on the provided assignment specification and the student's work analysis.

## Task Specification:
{task_description}

## Student Task Submission:
{student_submission}

Evaluation JSON Schema:
{{
    "completeness": "<complete|incomplete|partial>",
    "mistakes": ["<List of mistakes or omissions>"],
    "grade": "<0-100>",
    "detailed_feedback": {{
        "strengths": ["<List of positive aspects>"],
        "weaknesses": ["<List of areas for improvement>"],
        "suggestions": ["<Specific suggestions for improvement>"]
    }},
    "criterion_scores": {{
        "functionality": "<0-10> - Does the implementation work as required?",
        "completeness": "<0-10> - Are all requirements addressed?",
        "code_quality": "<0-10> - Is the code well-organized and readable?",
        "documentation": "<0-10> - Is the work properly documented?"
    }}
}}

## Guidelines:
- Analyze given task specification and user submission for the specific task.
- Analyze visual references provided in the submission.
- Check if visual references contain task/variant requirements.
- Compare student's submission against the task and variant-specific requirements.
- Identify mistakes or omissions in the submission.
- Determine the completeness of the submission for the task.
- Assign a grade based on the quality of the submission (0-100 scale).
- Provide constructive feedback that helps the student improve.
- Be fair but thorough in assessment.
- Consider partial credit for incomplete but correct implementations.
- Ensure the final output is valid JSON adhering to the specified structure.
- NEVER make up any information. If something is not present in the context, indicate it as such.

## Response Template (strictly follow):
THINKING: <Step-by-step thought process with numbered points (8 steps max, <=20 words each)>
FINAL_OUTPUT: <evaluation_json>

## Student Visual References:
"""
