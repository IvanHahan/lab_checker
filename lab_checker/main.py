from dotenv import load_dotenv

from lab_checker.agents.assignment_agent import AssignmentAgent
from lab_checker.agents.evaluation_agent import EvaluationAgent
from lab_checker.agents.work_agent import WorkAgent
from lab_checker.llm import OpenAIModel

if __name__ == "__main__":
    load_dotenv()
    llm = OpenAIModel()

    # Process the assignment specification
    assignment_agent = AssignmentAgent(llm)
    assignment_pdf = "/Users/ivanhahanov/Projects/lab_checker/data/assignments/укрТПКС_2023_ЛБ_1/укрТПКС_2023_ЛБ_1.pdf"
    assignment_result = assignment_agent.run(assignment_pdf)

    with open("assignment_result.json", "w", encoding="utf-8") as f:
        f.write(assignment_result)

    # Process the student submission
    work_agent = WorkAgent(llm)
    submission_pdf = "/Users/ivanhahanov/Projects/lab_checker/data/assignments/укрТПКС_2023_ЛБ_1/submissions/ЛБ1_Варіант14_Дорошенко Ю.С._КІУКІ-22-7.pdf"

    work_result = work_agent.run(
        assignment_data=assignment_result,
        submission_pdf=submission_pdf,
        student_id="Дорошенко Ю.С.",
        assignment_id="укрТПКС_2023_ЛБ_1",
    )

    with open("work_result.json", "w", encoding="utf-8") as f:
        f.write(work_result)

    # Evaluate the student submission
    evaluation_agent = EvaluationAgent(llm)
    evaluation_result = evaluation_agent.evaluate_from_results(
        assignment_result=assignment_result,
        work_result=work_result,
        student_id="Дорошенко Ю.С.",
        assignment_id="укрТПКС_2023_ЛБ_1",
    )

    with open("evaluation_result.json", "w", encoding="utf-8") as f:
        f.write(evaluation_result)
