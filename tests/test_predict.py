import pytest
from juritools.predict import JuriTagger, load_ner_model
from juritools.type import NamedEntity
from jurispacy_tokenizer import JuriSpacyTokenizer
import os

# Windows Fix for PosixPath issue
if os.name == "nt":
    import pathlib

    temp = pathlib.PosixPath
    pathlib.PosixPath = pathlib.WindowsPath

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "model")
model = load_ner_model(os.path.join(FIXTURE_DIR, "sequence_tagger.pt"))
tokenizer = JuriSpacyTokenizer()

@pytest.fixture(scope="session")
def juritagger():
    return JuriTagger(tokenizer, model)


def test_simple_text(juritagger):
    text = "Pierre Dupont est ingénieur.\n Il est content."
    juritagger.predict(text)
    assert len(juritagger.flair_sentences) == 2
    named_entities = juritagger.get_entity_json_from_flair_sentences()
    for entity in named_entities:
        entity.score = 1.0
    assert named_entities == [
        NamedEntity(
            text="Pierre", start=0, end=6, label="personnePhysique", source="NER model"
        ),
        NamedEntity(
            text="Dupont", start=7, end=13, label="personnePhysique", source="NER model"
        ),
    ]


@pytest.mark.skip(reason="output is not a list of dict anymore")
def test_simple_text_old(juritagger):
    text = "Pierre Dupont est ingénieur.\n Il est content."
    juritagger.predict(text)
    assert len(juritagger.flair_sentences) == 2
    assert juritagger.get_entity_json_from_flair_sentences() == [
        {
            "text": "Pierre",
            "start": 0,
            "end": 6,
            "label": "personnePhysique",
            "source": "NER model",
        },
        {
            "text": "Dupont",
            "start": 7,
            "end": 13,
            "label": "personnePhysique",
            "source": "NER model",
        },
    ]

