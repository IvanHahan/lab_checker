from ..doc_parsing import parse_pdf


class AssignmentAgent:
    def __init__(self, llm):
        self.llm = llm

    def run(self, pdf: str):
        # Process the PDF to extract text and images
        parsed_content = parse_pdf(pdf)
        text = parsed_content["text"]
        images = parsed_content["images"]
        page_count = parsed_content["page_count"]

        # Here you can add logic to interact with the LLM using the extracted text and images
        # For example, you might want to summarize the content or answer questions about it

        return {
            "text": text,
            "images": images,
            "page_count": page_count,
        }
