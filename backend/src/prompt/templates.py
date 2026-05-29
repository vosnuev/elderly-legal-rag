from langchain_core.prompts import ChatPromptTemplate

from .prompt_loader import load_prompt


# 보기 생성용 system/human prompt를 LangChain 템플릿으로 구성
def create_clarification_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", load_prompt("clarification_system.md")),
            ("human", load_prompt("clarification_human.md")),
        ]
    )


# RAG 근거 기반 답변용 system/human prompt를 LangChain 템플릿으로 구성
def create_grounded_answer_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", load_prompt("grounded_answer_system.md")),
            ("human", load_prompt("grounded_answer_human.md")),
        ]
    )
