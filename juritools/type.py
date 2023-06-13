from typing import Optional
from pydantic import BaseModel, validator, root_validator


class NamedEntity(BaseModel):
    text: str
    start: int
    end: int
    label: str
    source: str
    score: float = 1.0
    #start_tok: Optional[int] = None
    #end_tok: Optional[int] = None

    @validator("text")
    @classmethod
    def text_should_not_be_empty(cls, v):
        if v == "":
            raise ValueError(
                "text field is empty, a named entity cannot be an empty string"
            )
        return v


# Problem between pytest and pydantic
"""
    @root_validator
    @classmethod
    def end_minus_start_must_be_len_text(cls, values):
        start, end, text = values.get('start'), values.get('end'), values.get('text')
        if end - start != len(text):
            raise ValueError(
                f"end integer minus start integer must be equal to length of text, {end-start} != {len(text)}"
            )
        return end - start
"""
