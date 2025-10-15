from ..db import MongoDB


class TeacherAgent:
    def __init__(self, llm, db: MongoDB):
        self.llm = llm
        self.db = db
