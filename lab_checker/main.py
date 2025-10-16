from lab_checker.agents.assignment_agent import AssignmentAgent

if __name__ == "__main__":
    assignment_agent = AssignmentAgent(None)
    res = assignment_agent.run(
        "/Users/ivanhahanov/Projects/lab_checker/data/укрТПКС_2023_ЛБ_1.pdf"
    )
    print(res)
