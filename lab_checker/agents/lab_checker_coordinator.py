"""Coordinator agent that orchestrates the specialized agents for lab checking workflow."""

import json
import os
from typing import Any, Dict, Optional

from ..doc_parsing import parse_pdf
from ..llm import OpenAIModel
from .assignment_extraction_agent import AssignmentExtractionAgent
from .evaluation_agent import TaskEvaluationAgent
from .task_extraction_agent import TaskExtractionAgent
from .task_submission_agent import TaskSubmissionAgent


class LabCheckerCoordinator:
    """
    Coordinator agent that orchestrates the entire lab checking workflow
    using specialized agents for different aspects of the process.
    """

    def __init__(self, llm: OpenAIModel):
        self.llm = llm

        # Initialize specialized agents
        self.assignment_extraction_agent = AssignmentExtractionAgent(llm)
        self.task_extraction_agent = TaskExtractionAgent(llm)
        self.task_submission_agent = TaskSubmissionAgent(llm)
        self.evaluation_agent = TaskEvaluationAgent(llm)

    def run_full_analysis(
        self,
        assignment_pdf: Optional[str] = None,
        submission_pdf: Optional[str] = None,
        use_comprehensive_analysis: bool = True,
        output_dir: str = ".",
    ) -> Dict[str, Any]:
        """
        Run the complete lab checking workflow using specialized agents.

        Args:
            assignment_pdf: Path to assignment PDF file
            submission_pdf: Path to submission PDF file
            use_comprehensive_analysis: Whether to use comprehensive assignment analysis
            output_dir: Directory for output files

        Returns:
            Dictionary with complete analysis results
        """
        # Step 1: Extract or load assignment structure
        assignment_data = self._get_assignment_data(
            assignment_pdf, use_comprehensive_analysis, output_dir
        )

        if not assignment_data:
            raise ValueError("Could not extract or load assignment data")

        # Extract tasks from the assignment data
        tasks = assignment_data["result"]["tasks"]

        # Step 2: Parse submission PDF
        submission_content = parse_pdf(submission_pdf) if submission_pdf else None
        if not submission_content:
            raise ValueError("Could not parse submission PDF")

        # Step 3: Process each task
        task_results = []
        evaluations = []

        for i, task in enumerate(tasks):
            print(
                f"Processing task {i + 1}/{len(tasks)}: {task.get('title', task.get('name', f'Task {i + 1}'))}"
            )

            # Extract task-specific submission content
            task_extraction = self.task_extraction_agent.extract_task_submission(
                submission_content, task
            )

            # Save task extraction
            self.task_extraction_agent.save_task_submission(
                task_extraction, i, output_dir
            )

            # Comprehensive task submission analysis
            task_analysis = self.task_submission_agent.analyze_task_submission(
                submission_pdf, task, assignment_data
            )

            # Save task analysis
            self.task_submission_agent.save_analysis(task_analysis, i, output_dir)

            # Evaluate task submission
            evaluation = self.evaluation_agent.evaluate_task_submission(
                task,
                (
                    task_extraction.result
                    if hasattr(task_extraction, "result")
                    else task_extraction
                ),
                submission_content.get("visuals", {}),
            )

            # Save evaluation
            self.evaluation_agent.save_evaluation(evaluation, i, output_dir)

            task_results.append(
                {
                    "task_index": i,
                    "task": task,
                    "extraction": task_extraction,
                    "analysis": task_analysis,
                    "evaluation": evaluation,
                }
            )

            evaluations.append(evaluation)

        # Step 4: Generate overall assessment
        overall_grade = self.evaluation_agent.generate_overall_grade(evaluations)

        # Step 5: Compile final results
        final_results = {
            "assignment_data": assignment_data,
            "submission_metadata": {
                "pdf_path": submission_pdf,
                "total_tasks": len(tasks),
                "processed_tasks": len(task_results),
            },
            "task_results": task_results,
            "overall_assessment": overall_grade,
            "summary": {
                "total_score": overall_grade["overall_grade"],
                "tasks_completed": len(
                    [r for r in task_results if self._is_task_completed(r)]
                ),
                "tasks_partial": len(
                    [r for r in task_results if self._is_task_partial(r)]
                ),
                "tasks_incomplete": len(
                    [r for r in task_results if self._is_task_incomplete(r)]
                ),
            },
        }

        # Save final results
        self._save_final_results(final_results, output_dir)

        return final_results

    def _get_assignment_data(
        self, assignment_pdf: Optional[str], use_comprehensive: bool, output_dir: str
    ) -> Dict[str, Any]:
        """Get assignment data either from existing file or by extraction."""
        assignment_file = f"{output_dir}/assignment.json"

        # Check if assignment.json already exists
        if os.path.exists(assignment_file):
            with open(assignment_file, "r") as f:
                return json.load(f)

        # Extract assignment data if PDF is provided
        if assignment_pdf:
            assignment_data = self.assignment_extraction_agent.extract_assignment(
                assignment_pdf
            )
            self.assignment_extraction_agent.save_assignment(
                assignment_data, assignment_file
            )

            return (
                assignment_data.result
                if hasattr(assignment_data, "result")
                else assignment_data
            )

        return None

    def _is_task_completed(self, task_result: Dict[str, Any]) -> bool:
        """Check if a task is completed based on evaluation."""
        evaluation = task_result.get("evaluation", {})
        result = (
            evaluation.get("result", {})
            if hasattr(evaluation, "result")
            else evaluation
        )
        return result.get("completeness") == "complete"

    def _is_task_partial(self, task_result: Dict[str, Any]) -> bool:
        """Check if a task is partially completed based on evaluation."""
        evaluation = task_result.get("evaluation", {})
        result = (
            evaluation.get("result", {})
            if hasattr(evaluation, "result")
            else evaluation
        )
        return result.get("completeness") == "partial"

    def _is_task_incomplete(self, task_result: Dict[str, Any]) -> bool:
        """Check if a task is incomplete based on evaluation."""
        evaluation = task_result.get("evaluation", {})
        result = (
            evaluation.get("result", {})
            if hasattr(evaluation, "result")
            else evaluation
        )
        return result.get("completeness") == "incomplete"

    def _save_final_results(self, results: Dict[str, Any], output_dir: str) -> None:
        """Save final results to JSON file."""
        output_path = f"{output_dir}/lab_analysis_results.json"
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"Final results saved to: {output_path}")

    def run_quick_analysis(
        self,
        assignment_pdf: Optional[str] = None,
        submission_pdf: Optional[str] = None,
        output_dir: str = ".",
    ) -> Dict[str, Any]:
        """
        Run a quicker analysis using the simpler extraction methods.

        Args:
            assignment_pdf: Path to assignment PDF file
            submission_pdf: Path to submission PDF file
            output_dir: Directory for output files

        Returns:
            Dictionary with analysis results
        """
        return self.run_full_analysis(
            assignment_pdf=assignment_pdf,
            submission_pdf=submission_pdf,
            use_comprehensive_analysis=False,
            output_dir=output_dir,
        )
