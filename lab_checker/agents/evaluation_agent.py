import json
from pathlib import Path
from typing import Any, Dict, Optional


class EvaluationAgent:
    """
    Agent responsible for evaluating student submissions based on
    assignment requirements and work analysis.
    """

    def __init__(self, llm):
        self.llm = llm
        self.system_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        """Load the system prompt from the prompts directory."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "evaluation_agent.md"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def run(
        self,
        assignment_data: Dict[str, Any],
        work_analysis: Dict[str, Any],
        student_id: Optional[str] = None,
        assignment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate student submission based on assignment requirements and work analysis.

        Args:
            assignment_data: The structured assignment data from AssignmentAgent
                            (JSON object with tasks, requirements, etc.)
            work_analysis: The structured work analysis from WorkAgent
                          (JSON object with task answers, implementation details, etc.)
            student_id: Student identifier (optional)
            assignment_id: Assignment identifier (optional)

        Returns:
            Dictionary containing structured evaluation with scores and feedback
        """
        # Prepare the user message with assignment and work analysis data
        user_message = self._prepare_user_message(
            assignment_data, work_analysis, student_id, assignment_id
        )

        # Call the LLM with system prompt and user message
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]

        response = self.llm._call(messages=messages, reasoning_effort="medium")

        return response

    def _prepare_user_message(
        self,
        assignment_data: Dict[str, Any],
        work_analysis: Dict[str, Any],
        student_id: Optional[str] = None,
        assignment_id: Optional[str] = None,
    ) -> str:
        """
        Prepare the user message containing assignment and work analysis information.

        Args:
            assignment_data: Structured assignment data
            work_analysis: Structured work analysis from WorkAgent
            student_id: Student identifier
            assignment_id: Assignment identifier

        Returns:
            Formatted string for the user message
        """
        message_parts = []

        # Add header
        message_parts.append("# Evaluation Request")
        message_parts.append("")
        message_parts.append(
            "Please evaluate the following student submission based on the assignment "
            "requirements and the work analysis provided."
        )
        message_parts.append("")

        # Add metadata if available
        if student_id or assignment_id:
            message_parts.append("## Metadata")
            if student_id:
                message_parts.append(f"**Student ID**: {student_id}")
            if assignment_id:
                message_parts.append(f"**Assignment ID**: {assignment_id}")
            message_parts.append("")

        # Add assignment specification
        message_parts.append("## Assignment Specification")
        message_parts.append(
            "Below is the complete assignment specification that defines all tasks, "
            "requirements, and evaluation criteria:"
        )
        message_parts.append("")
        message_parts.append("```json")
        message_parts.append(json.dumps(assignment_data, indent=2, ensure_ascii=False))
        message_parts.append("```")
        message_parts.append("")

        # Add work analysis
        message_parts.append("## Student Work Analysis")
        message_parts.append(
            "Below is the detailed analysis of what the student submitted, including "
            "implementation details, completeness status, and documentation quality:"
        )
        message_parts.append("")
        message_parts.append("```json")
        message_parts.append(json.dumps(work_analysis, indent=2, ensure_ascii=False))
        message_parts.append("```")
        message_parts.append("")

        # Add evaluation instruction
        message_parts.append("---")
        message_parts.append("")
        message_parts.append("## Instructions")
        message_parts.append(
            "Please evaluate each task and the overall submission according to the "
            "evaluation criteria specified in your system instructions. Provide:"
        )
        message_parts.append("")
        message_parts.append(
            "1. **Individual task scores** (0-10) with detailed breakdown"
        )
        message_parts.append("2. **Overall score** and letter grade")
        message_parts.append("3. **Specific feedback** for each task")
        message_parts.append("4. **Strengths and weaknesses**")
        message_parts.append("5. **Actionable suggestions** for improvement")
        message_parts.append("")
        message_parts.append(
            "Base your evaluation strictly on the evidence provided in the work analysis. "
            "Be fair, objective, and constructive in your feedback."
        )

        return "\n".join(message_parts)

    def evaluate_from_results(
        self,
        assignment_result: Any,
        work_result: Any,
        student_id: Optional[str] = None,
        assignment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convenience method to evaluate when you have raw results from other agents.
        Handles parsing of string results to JSON if needed.

        Args:
            assignment_result: Result from AssignmentAgent.run() (dict or JSON string)
            work_result: Result from WorkAgent.run() (dict or JSON string)
            student_id: Student identifier (optional)
            assignment_id: Assignment identifier (optional)

        Returns:
            Dictionary containing structured evaluation with scores and feedback
        """
        # Parse assignment_result if it's a string
        if isinstance(assignment_result, str):
            try:
                assignment_data = json.loads(assignment_result)
            except json.JSONDecodeError:
                raise ValueError(
                    "assignment_result is a string but could not be parsed as JSON"
                )
        else:
            assignment_data = assignment_result

        # Parse work_result if it's a string
        if isinstance(work_result, str):
            try:
                work_analysis = json.loads(work_result)
            except json.JSONDecodeError:
                raise ValueError(
                    "work_result is a string but could not be parsed as JSON"
                )
        else:
            work_analysis = work_result

        # Handle case where work_result has an error but contains raw_response
        if isinstance(work_analysis, dict) and "error" in work_analysis:
            if "raw_response" in work_analysis:
                try:
                    work_analysis = json.loads(work_analysis["raw_response"])
                except json.JSONDecodeError:
                    # Keep the error structure if we can't parse raw_response
                    pass

        return self.run(assignment_data, work_analysis, student_id, assignment_id)
