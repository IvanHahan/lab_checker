from lab_checker.agents.assignment_agent import AssignmentAgent
from lab_checker.llm import OpenAIModel

if __name__ == "__main__":
    assignment_agent = AssignmentAgent(OpenAIModel())
    res = assignment_agent.run(
        "/Users/ivanhahanov/Projects/lab_checker/data/укрТПКС_2023_ЛБ_1.pdf"
    )
    print(res)
