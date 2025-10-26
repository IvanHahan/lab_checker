"""Coordinator agent that orchestrates the specialized agents for lab checking workflow."""

import json
import os
from typing import Any, Dict, Optional

from loguru import logger

from ..doc_parsing import parse_pdf
from ..llm import OpenAIModel
from .assignment_agent import AssignmentAgent
from .evaluation_agent import TaskEvaluationAgent
from .task_submission_agent import TaskSubmissionAgent


class LabCheckerCoordinator:
    """
    Coordinator agent that orchestrates the entire lab checking workflow
    using specialized agents for different aspects of the process.
    """

    def __init__(self, slm: OpenAIModel, llm: OpenAIModel):
        logger.info("Initializing LabCheckerCoordinator")
        self.slm = slm
        self.llm = llm

        # Initialize specialized agents
        logger.debug("Initializing specialized agents")
        self.assignment_extraction_agent = AssignmentAgent(slm)
        self.task_submission_agent = TaskSubmissionAgent(llm)
        self.evaluation_agent = TaskEvaluationAgent(llm)
        logger.info("LabCheckerCoordinator initialized successfully")

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
        logger.info(
            f"Starting full analysis with assignment_pdf={assignment_pdf}, submission_pdf={submission_pdf}"
        )
        logger.debug(
            f"Parameters: use_comprehensive_analysis={use_comprehensive_analysis}, output_dir={output_dir}"
        )

        # Step 1: Extract or load assignment structure
        logger.info("Step 1: Extracting/loading assignment structure")
        assignment_data = self.assignment_extraction_agent.extract_assignment(
            assignment_pdf
        )
        os.makedirs(output_dir, exist_ok=True)
        with open(f"{output_dir}/assignment.json", "w") as f:
            f.write(assignment_data.model_dump_json(indent=2, ensure_ascii=False))

        if not assignment_data:
            logger.error("Could not extract or load assignment data")
            raise ValueError("Could not extract or load assignment data")

        # Extract tasks from the assignment data
        tasks = assignment_data.result["tasks"]
        logger.info(f"Found {len(tasks)} tasks in assignment")

        # Step 2: Parse submission PDF
        logger.info("Step 2: Parsing submission PDF")
        submission_content = parse_pdf(submission_pdf) if submission_pdf else None
        if not submission_content:
            logger.error(f"Could not parse submission PDF: {submission_pdf}")
            raise ValueError("Could not parse submission PDF")
        logger.debug("Submission PDF parsed successfully")

        # Step 3: Process each task
        logger.info("Step 3: Processing individual tasks")
        task_results = []
        evaluations = []

        for i, task in enumerate(tasks):
            task_title = task.get("title", task.get("name", f"Task {i + 1}"))
            logger.info(f"Processing task {i + 1}/{len(tasks)}: {task_title}")
            print(f"Processing task {i + 1}/{len(tasks)}: {task_title}")

            # Extract task-specific submission content
            logger.debug(f"Extracting submission content for task {i + 1}")
            task_submission = self.task_submission_agent.extract_task_submission(
                submission_content, task
            )

            # Save task submission
            logger.debug(f"Saving task submission for task {i + 1}")
            with open(f"{output_dir}/task_{i + 1}_submission.json", "w") as f:
                f.write(task_submission.model_dump_json(indent=2, ensure_ascii=False))

            # Evaluate task submission
            logger.debug(f"Evaluating task submission for task {i + 1}")
            evaluation = self.evaluation_agent.evaluate_task_submission(
                task,
                task_submission.result,
                submission_content.get("visuals", {}),
            )

            # Save evaluation
            logger.debug(f"Saving evaluation for task {i + 1}")
            with open(f"{output_dir}/task_{i + 1}_evaluation.json", "w") as f:
                f.write(evaluation.model_dump_json(indent=2, ensure_ascii=False))

            task_results.append(
                {
                    "task_index": i,
                    "task": task,
                    "extraction": task_submission,
                    "evaluation": evaluation,
                }
            )

            evaluations.append(evaluation)
            logger.info(f"Completed processing task {i + 1}: {task_title}")

        # Step 4: Generate overall assessment
        logger.info("Step 4: Generating overall assessment")
        overall_grade = self.evaluation_agent.generate_overall_grade(evaluations)

        # Step 5: Compile final results
        logger.info("Step 5: Compiling final results")
        completed_tasks = len([r for r in task_results if self._is_task_completed(r)])
        partial_tasks = len([r for r in task_results if self._is_task_partial(r)])
        incomplete_tasks = len([r for r in task_results if self._is_task_incomplete(r)])

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
                "tasks_completed": completed_tasks,
                "tasks_partial": partial_tasks,
                "tasks_incomplete": incomplete_tasks,
            },
        }

        logger.info(
            f"Analysis complete - Score: {overall_grade['overall_grade']}, "
            f"Completed: {completed_tasks}, Partial: {partial_tasks}, Incomplete: {incomplete_tasks}"
        )

        # Save final results
        self._save_final_results(final_results, output_dir)

        return final_results

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
        logger.info(f"Saving final results to {output_path}")
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.success(f"Final results saved to: {output_path}")
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
        logger.info("Starting quick analysis mode")
        return self.run_full_analysis(
            assignment_pdf=assignment_pdf,
            submission_pdf=submission_pdf,
            use_comprehensive_analysis=False,
            output_dir=output_dir,
        )
