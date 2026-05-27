from langchain_core.prompts import ChatPromptTemplate

from .prompt_loader import load_prompt


def create_clarification_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", load_prompt("clarification_system.md")),
            ("human", load_prompt("clarification_human.md")),
        ]
    )


def create_grounded_answer_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", load_prompt("grounded_answer_system.md")),
            ("human", load_prompt("grounded_answer_human.md")),
        ]
    )
