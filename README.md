# Lab Checker

An AI-powered system for automatically checking and evaluating laboratory assignments using specialized agents. This system can parse assignment PDFs, analyze student submissions, and provide comprehensive grading with detailed feedback.

## Features

- **Assignment Analysis**: Automatically extracts tasks and requirements from assignment PDFs
- **Submission Processing**: Parses student submission PDFs and extracts content
- **AI-Powered Evaluation**: Uses OpenAI models to evaluate submissions against assignment criteria
- **Multi-Agent Architecture**: Employs specialized agents for different aspects of the checking process
- **Comprehensive Reporting**: Generates detailed evaluation reports with grades and feedback
- **Image Processing**: Handles images and diagrams within PDF documents

## Architecture

The system uses a multi-agent architecture with the following specialized agents:

- **LabCheckerCoordinator**: Orchestrates the entire workflow
- **AssignmentAgent**: Extracts and structures assignment tasks from PDFs
- **TaskSubmissionAgent**: Processes student submissions and maps them to assignment tasks
- **TaskEvaluationAgent**: Evaluates individual tasks and provides grades
- **ImageAgent**: Handles image processing and analysis within documents

## Installation

1. Clone the repository:
```bash
git clone https://github.com/IvanHahan/lab_checker.git
cd lab_checker
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file in the project root with your OpenAI API key:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage

### Basic Usage

```python
from dotenv import load_dotenv
from lab_checker.agents import create_lab_checker
from lab_checker.llm import OpenAIModel

# Load environment variables
load_dotenv()

# Initialize models
slm = OpenAIModel(model="gpt-4o-mini")  # Small language model for simple tasks
llm = OpenAIModel(model="gpt-4o")       # Large language model for complex evaluation

# Create coordinator
coordinator = create_lab_checker(slm, llm)

# Run analysis
results = coordinator.run_full_analysis(
    assignment_pdf="path/to/assignment.pdf",
    submission_pdf="path/to/submission.pdf",
    output_dir="./output"
)

# Access results
print(f"Overall Grade: {results['overall_assessment']['overall_grade']}%")
print(f"Tasks Completed: {results['summary']['tasks_completed']}")
```

### Running the Main Script

```bash
python -m lab_checker.main
```

## Project Structure

```
lab_checker/
├── lab_checker/           # Main package
│   ├── agents/           # Specialized AI agents
│   │   ├── assignment_agent.py
│   │   ├── evaluation_agent.py
│   │   ├── image_agent.py
│   │   ├── lab_checker_coordinator.py
│   │   └── task_submission_agent.py
│   ├── data_model/       # Data models and structures
│   │   ├── assignment.py
│   │   ├── base.py
│   │   └── work.py
│   ├── chains.py         # LangChain integration
│   ├── db.py            # Database utilities
│   ├── doc_parsing.py   # PDF parsing utilities
│   ├── image_utils.py   # Image processing utilities
│   ├── llm.py           # Language model interface
│   ├── main.py          # Main execution script
│   ├── message_utils.py # Message handling utilities
│   ├── parsers.py       # Content parsers
│   └── utils.py         # General utilities
├── tests/               # Test suite
├── data/               # Data directory
│   └── assignments/    # Assignment and submission files
└── requirements.txt    # Python dependencies
```

## Configuration

The system can be configured through environment variables:

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- Additional configuration options can be set in the `.env` file

## Testing

Run the test suite:

```bash
pytest tests/
```

Run specific tests:

```bash
pytest tests/test_task_submission_agent.py
pytest tests/test_doc_parsing.py
```

## Dependencies

- **langchain-openai**: LangChain integration with OpenAI
- **numpy**: Numerical computing
- **pdfplumber**: PDF text extraction
- **loguru**: Enhanced logging
- **openai-agents**: OpenAI agents framework

## Output Format

The system generates comprehensive evaluation results including:

- Overall grade percentage
- Individual task evaluations
- Detailed feedback for each task
- Summary statistics (completed, partial, incomplete tasks)
- Extracted content and analysis metadata

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please open an issue in the GitHub repository.