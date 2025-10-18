import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..doc_parsing import parse_pdf
from ..message_utils import prepare_message_with_visuals


class WorkAgent:
    """
    Agent responsible for analyzing student submissions and extracting
    what the student implemented for each task in the assignment.
    """

    def __init__(self, llm):
        self.llm = llm
        self.system_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        """Load the system prompt from the prompts directory."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "work_agent.md"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def run(
        self,
        assignment_data: Dict[str, Any],
        submission_pdf: Optional[str] = None,
        submission_files: Optional[List[Dict[str, str]]] = None,
        student_id: Optional[str] = None,
        assignment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze student submission and extract answers for each task.

        Args:
            assignment_data: The structured assignment data from AssignmentAgent
                            (JSON object with tasks, requirements, etc.)
            submission_pdf: Path to PDF file containing student's work (optional)
            submission_files: List of submitted files, each containing:
                             - 'path': file path/name
                             - 'content': file content as string
                             - 'type': file type (optional, e.g., 'python', 'markdown')
                             (optional, used if submission_pdf is not provided)
            student_id: Student identifier (optional)
            assignment_id: Assignment identifier (optional)

        Returns:
            Dictionary containing structured analysis of student's work
        """
        # Prepare the user message content
        if submission_pdf:
            # Parse PDF submission
            parsed_content = parse_pdf(submission_pdf)
            message_content = self._prepare_message_from_pdf(
                assignment_data, parsed_content, student_id, assignment_id
            )
        elif submission_files:
            # Use file-based submission
            message_content = self._prepare_message_from_files(
                assignment_data, submission_files, student_id, assignment_id
            )
        else:
            raise ValueError(
                "Either submission_pdf or submission_files must be provided"
            )

        # Call the LLM with system prompt and user message
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": message_content},
        ]

        response = self.llm._call(messages=messages)

        # Parse the response (assuming it returns JSON)
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # If the response is not valid JSON, wrap it in a structure
            result = {
                "error": "Failed to parse LLM response as JSON",
                "raw_response": response,
            }

        return result

    def _prepare_message_from_pdf(
        self,
        assignment_data: Dict[str, Any],
        parsed_content: Dict[str, Any],
        student_id: Optional[str] = None,
        assignment_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Prepare message content from parsed PDF submission.

        Args:
            assignment_data: Structured assignment data
            parsed_content: Parsed PDF content with text and visuals
            student_id: Student identifier
            assignment_id: Assignment identifier

        Returns:
            List of content entries for the LLM (text and images)
        """
        # Prepare assignment data as JSON
        assignment_json = json.dumps(assignment_data, indent=2)

        # Build the text prompt
        text_parts = []

        # Add metadata if available
        if student_id or assignment_id:
            text_parts.append("# Submission Metadata")
            if student_id:
                text_parts.append(f"Student ID: {student_id}")
            if assignment_id:
                text_parts.append(f"Assignment ID: {assignment_id}")
            text_parts.append("")

        # Add assignment specification
        text_parts.append("# Assignment Specification")
        text_parts.append(
            "Below is the complete assignment specification extracted from the laboratory document:"
        )
        text_parts.append("")
        text_parts.append("```json")
        text_parts.append(assignment_json)
        text_parts.append("```")
        text_parts.append("")

        # Add student submission header
        text_parts.append("# Student Submission")
        text_parts.append(
            f"The student submitted a {parsed_content['page_count']}-page PDF document. "
            "Below is the content extracted from the submission:"
        )
        text_parts.append("")
        text_parts.append("---")
        text_parts.append("")

        # Combine with submission text
        full_text = "\n".join(text_parts) + parsed_content["text"]

        # Add instruction for analysis
        full_text += "\n\n---\n\n"
        full_text += (
            "Please analyze this submission according to the assignment specification and extract "
            "what the student implemented for each task. Follow the output format specified in your "
            "system instructions."
        )

        # Prepare message with images using the shared utility
        return prepare_message_with_visuals(
            full_text, parsed_content.get("visuals", [])
        )

    def _prepare_message_from_files(
        self,
        assignment_data: Dict[str, Any],
        submission_files: List[Dict[str, str]],
        student_id: Optional[str] = None,
        assignment_id: Optional[str] = None,
    ) -> str:
        """
        Prepare the user message containing assignment and submission information.

        Args:
            assignment_data: Structured assignment data
            submission_files: List of submitted files with content
            student_id: Student identifier
            assignment_id: Assignment identifier

        Returns:
            Formatted string for the user message
        """
        message_parts = []

        # Add metadata if available
        if student_id or assignment_id:
            message_parts.append("# Submission Metadata")
            if student_id:
                message_parts.append(f"Student ID: {student_id}")
            if assignment_id:
                message_parts.append(f"Assignment ID: {assignment_id}")
            message_parts.append("")

        # Add assignment specification
        message_parts.append("# Assignment Specification")
        message_parts.append(
            "Below is the complete assignment specification extracted from the laboratory document:"
        )
        message_parts.append("")
        message_parts.append("```json")
        message_parts.append(json.dumps(assignment_data, indent=2))
        message_parts.append("```")
        message_parts.append("")

        # Add student submission
        message_parts.append("# Student Submission")
        message_parts.append(
            f"The student submitted {len(submission_files)} file(s). Below are the contents of each file:"
        )
        message_parts.append("")

        for file_info in submission_files:
            file_path = file_info.get("path", "unknown")
            file_content = file_info.get("content", "")
            file_type = file_info.get("type", "text")

            message_parts.append(f"## File: `{file_path}`")
            if file_type:
                message_parts.append(f"Type: {file_type}")
            message_parts.append("")
            message_parts.append(f"```{file_type if file_type != 'text' else ''}")
            message_parts.append(file_content)
            message_parts.append("```")
            message_parts.append("")

        # Add instruction for analysis
        message_parts.append("---")
        message_parts.append("")
        message_parts.append(
            "Please analyze this submission according to the assignment specification and extract "
            "what the student implemented for each task. Follow the output format specified in your "
            "system instructions."
        )

        return "\n".join(message_parts)

    def analyze_directory(
        self,
        assignment_data: Dict[str, Any],
        submission_dir: Path,
        student_id: Optional[str] = None,
        assignment_id: Optional[str] = None,
        file_extensions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a directory containing student submission files.

        Args:
            assignment_data: The structured assignment data from AssignmentAgent
            submission_dir: Path to directory containing submission files
            student_id: Student identifier (optional)
            assignment_id: Assignment identifier (optional)
            file_extensions: List of file extensions to include (e.g., ['.py', '.md'])
                           If None, includes all text files

        Returns:
            Dictionary containing structured analysis of student's work
        """
        if file_extensions is None:
            # Default text file extensions
            file_extensions = [
                ".py",
                ".js",
                ".java",
                ".cpp",
                ".c",
                ".h",
                ".hpp",
                ".md",
                ".txt",
                ".json",
                ".xml",
                ".yaml",
                ".yml",
                ".css",
                ".html",
                ".sql",
                ".r",
                ".m",
                ".swift",
                ".kt",
                ".rs",
            ]

        submission_files = []
        submission_path = Path(submission_dir)

        if not submission_path.exists():
            raise ValueError(f"Submission directory does not exist: {submission_dir}")

        # Recursively find all files with specified extensions
        for ext in file_extensions:
            for file_path in submission_path.rglob(f"*{ext}"):
                if file_path.is_file():
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()

                        # Get relative path from submission directory
                        relative_path = file_path.relative_to(submission_path)

                        # Determine file type from extension
                        file_type = ext.lstrip(".")

                        submission_files.append(
                            {
                                "path": str(relative_path),
                                "content": content,
                                "type": file_type,
                            }
                        )
                    except Exception as e:
                        # If file can't be read, add it with error note
                        submission_files.append(
                            {
                                "path": str(file_path.relative_to(submission_path)),
                                "content": f"Error reading file: {str(e)}",
                                "type": "error",
                            }
                        )

        # Sort files by path for consistent ordering
        submission_files.sort(key=lambda x: x["path"])

        return self.run(
            assignment_data=assignment_data,
            submission_files=submission_files,
            student_id=student_id,
            assignment_id=assignment_id,
        )
