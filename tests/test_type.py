import pytest
from juritools.type import NamedEntity

def test_empty_text():
    with pytest.raises(ValueError, match="text field is empty, a named entity cannot be an empty string"):
        expected = NamedEntity(text="", start=0, end=0, label='adresse', source='NER Model')

# Problem between pytest and pydantic
"""
def test_indexes_do_not_match_len_text():
    with pytest.raises(ValueError, match="end integer minus start integer must be equal to length of text, 5 != 6"):
        expected = NamedEntity(text="Pierre", start=6, end=11, label='adresse', source='NER Model')
"""