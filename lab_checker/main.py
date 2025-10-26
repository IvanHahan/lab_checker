import json

from dotenv import load_dotenv

from lab_checker.agents import create_lab_checker
from lab_checker.data_model import Assignment
from lab_checker.llm import OpenAIModel


def load_assignment_result(filepath: str) -> Assignment:
    """Load assignment result from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        assignment_data = json.load(f)
        return Assignment(**assignment_data)


def main_new_agents():
    """Demonstrate the new specialized agent system."""
    load_dotenv()
    slm = OpenAIModel(model="gpt-5-nano")
    llm = OpenAIModel(model="gpt-5")

    # File paths
    assignment_pdf = "/Users/ivanhahanov/Projects/lab_checker/data/assignments/укрТПКС_2023_ЛБ_1/укрТПКС_2023_ЛБ_1.pdf"
    submission_pdf = "/Users/ivanhahanov/Projects/lab_checker/data/assignments/укрТПКС_2023_ЛБ_1/submissions/ЛБ1_Варіант14_Дорошенко Ю.С._КІУКІ-22-7.pdf"

    # Create coordinator with specialized agents
    coordinator = create_lab_checker(slm, llm)

    print("Running comprehensive analysis with specialized agents...")

    # Run full analysis with new agent system
    results = coordinator.run_full_analysis(
        assignment_pdf=assignment_pdf,
        submission_pdf=submission_pdf,
        output_dir="./output_new",
    )

    # Display results
    print("\n=== Analysis Results ===")
    print(f"Overall Grade: {results['overall_assessment']['overall_grade']}%")
    print(f"Total Tasks: {results['submission_metadata']['total_tasks']}")
    print(f"Tasks Completed: {results['summary']['tasks_completed']}")
    print(f"Tasks Partial: {results['summary']['tasks_partial']}")
    print(f"Tasks Incomplete: {results['summary']['tasks_incomplete']}")

    return results


if __name__ == "__main__":
    print("Lab Checker - Specialized Agents System")
    print("=====================================")

    # Choose which demonstration to run:

    # 1. Run new agent system
    main_new_agents()

    # 2. Compare systems (uncomment to run)
    # main_legacy_comparison()
