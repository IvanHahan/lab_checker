from langchain_core.runnables import RunnableLambda

from .data_model import ThoughtfulResponse
from .parsers import parse_json, parse_output_with_thinking


def chain_json_with_thinking(model, data_schema=None):
    return (
        model
        | parse_output_with_thinking
        | RunnableLambda(
            lambda response: ThoughtfulResponse(
                reasoning=response.reasoning,
                result=parse_json(response.result, data_schema),
            )
        )
    )


def chain_str_with_thinking(model):
    return model | parse_output_with_thinking
