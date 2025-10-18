import json

from dotenv import load_dotenv

from lab_checker.agents.assignment_agent import AssignmentAgent
from lab_checker.agents.work_agent import WorkAgent
from lab_checker.llm import OpenAIModel

if __name__ == "__main__":
    load_dotenv()
    llm = OpenAIModel()

    # Process the assignment specification
    assignment_agent = AssignmentAgent(llm)
    assignment_pdf = "/Users/ivanhahanov/Projects/lab_checker/data/assignments/укрТПКС_2023_ЛБ_1/укрТПКС_2023_ЛБ_1.pdf"
    assignment_result = assignment_agent.run(assignment_pdf)
    print("=" * 80)
    print("ASSIGNMENT ANALYSIS:")
    print("=" * 80)
    print(assignment_result)
    print("\n")

    # Process the student submission
    work_agent = WorkAgent(llm)
    submission_pdf = "/Users/ivanhahanov/Projects/lab_checker/data/assignments/укрТПКС_2023_ЛБ_1/submissions/ЛБ1_Варіант14_Дорошенко Ю.С._КІУКІ-22-7.pdf"

    # Parse assignment_result as JSON if it's a string
    try:
        if isinstance(assignment_result, str):
            assignment_data = json.loads(assignment_result)
        else:
            assignment_data = assignment_result
    except json.JSONDecodeError:
        print("Warning: Could not parse assignment result as JSON, using raw result")
        assignment_data = {"raw": assignment_result}

    work_result = work_agent.run(
        assignment_data=assignment_data,
        submission_pdf=submission_pdf,
        student_id="Дорошенко Ю.С.",
        assignment_id="укрТПКС_2023_ЛБ_1",
    )

    print("=" * 80)
    print("STUDENT WORK ANALYSIS:")
    print("=" * 80)
    print(json.dumps(work_result, indent=2, ensure_ascii=False))
