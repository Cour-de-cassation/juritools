import pytest

from juritools.postprocessing import PostProcessFromText
from juritools.type import NamedEntity, PostProcessOutput
from tests.testing_utils import assert_equality_between_entities, assert_equality_between_outputs


def test_simple_additional_term():
    text = "Ceci est une annotation supplémentaire."
    additional_terms_str = "annotation supplémentaire"

    expected_entities = [
        NamedEntity(
            start=13,
            text="annotation supplémentaire",
            source="postprocess",
            label="annotationSupplementaire",
        )
    ]
    print(expected_entities)
    expected_output = PostProcessOutput(
        added_entities=[e.model_copy(deep=True) for e in expected_entities],
    )

    postpro = PostProcessFromText(text=text, entities=[], checklist=[])
    output = postpro.match_additional_terms(
        additional_terms_str=additional_terms_str,
        separators=["/"],
        ignore_accents=False,
        ignore_case=False,
    )

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_simple_additional_term_no_accent():
    text = "Ceci est une annotation supplémentaire."
    additional_terms_str = "annotation supplementaire"

    expected_entities = [
        NamedEntity(
            start=13,
            text="annotation supplémentaire",
            source="postprocess",
            label="annotationSupplementaire",
        )
    ]

    expected_output = PostProcessOutput(
        added_entities=expected_entities,
    )

    postpro = PostProcessFromText(text=text, entities=[], checklist=[])
    output = postpro.match_additional_terms(
        additional_terms_str=additional_terms_str,
        separators=["/"],
        ignore_accents=True,
        ignore_case=False,
    )

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_simple_additional_term_accent():
    text = "Ceci est une annotation supplémentaire."
    additional_terms_str = "annotation supplementaire"

    expected_entities = []

    expected_output = PostProcessOutput(
        added_entities=expected_entities,
    )

    postpro = PostProcessFromText(text=text, entities=[], checklist=[])
    output = postpro.match_additional_terms(
        additional_terms_str=additional_terms_str,
        separators=["/"],
        ignore_accents=False,
        ignore_case=False,
    )

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_simple_additional_term_no_case():
    text = "Ceci est une annotation supplémentaire."
    additional_terms_str = "ANNOTATION SUPPLÉMENTAIRE"

    expected_entities = [
        NamedEntity(
            start=13,
            text="annotation supplémentaire",
            source="postprocess",
            label="annotationSupplementaire",
        )
    ]

    expected_output = PostProcessOutput(
        added_entities=expected_entities,
    )

    postpro = PostProcessFromText(text=text, entities=[], checklist=[])
    output = postpro.match_additional_terms(
        additional_terms_str=additional_terms_str,
        separators=["/"],
        ignore_accents=False,
        ignore_case=True,
    )

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_simple_additional_term_case():
    text = "Ceci est une annotation supplémentaire."
    additional_terms_str = "ANNOTATION SUPPLÉMENTAIRE"

    expected_entities = []

    expected_output = PostProcessOutput(
        added_entities=expected_entities,
    )

    postpro = PostProcessFromText(text=text, entities=[], checklist=[])
    output = postpro.match_additional_terms(
        additional_terms_str=additional_terms_str,
        separators=["/"],
        ignore_accents=False,
        ignore_case=False,
    )

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_multiple_additional_terms():
    text = "Ce texte contient plusieurs annotations supplémentaires."
    additional_terms_str = "/ texte / annotations supplémentaires"
    expected_entities = [
        NamedEntity(
            start=3,
            text="texte",
            label="annotationSupplementaire",
            source="postprocess",
        ),
        NamedEntity(
            start=28,
            text="annotations supplémentaires",
            source="postprocess",
            label="annotationSupplementaire",
        ),
    ]

    expected_output = PostProcessOutput(
        added_entities=expected_entities,
    )

    postpro = PostProcessFromText(text=text, entities=[], checklist=[])
    output = postpro.match_additional_terms(
        additional_terms_str=additional_terms_str,
        separators=["/"],
        ignore_accents=False,
        ignore_case=False,
    )

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_multiple_additional_terms_with_other_separator():
    text = "Ce texte contient plusieurs annotations supplémentaires."
    additional_terms_str = r"\\ texte \\ annotations supplémentaires \\ "

    expected_entities = [
        NamedEntity(
            start=3,
            text="texte",
            label="annotationSupplementaire",
            source="postprocess",
        ),
        NamedEntity(
            start=28,
            text="annotations supplémentaires",
            source="postprocess",
            label="annotationSupplementaire",
        ),
    ]

    expected_output = PostProcessOutput(
        added_entities=expected_entities,
    )

    postpro = PostProcessFromText(text=text, entities=[], checklist=[])
    output = postpro.match_additional_terms(
        additional_terms_str=additional_terms_str,
        separators=[r"\\"],
        ignore_accents=False,
        ignore_case=False,
    )

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_multiple_additional_terms_with_website():
    text = "Ce texte contient un site web, à savoir, http://example.org"
    additional_terms_str = "texte / http://example.org"

    expected_entities = [
        NamedEntity(
            start=3,
            text="texte",
            source="postprocess",
            label="annotationSupplementaire",
        ),
        NamedEntity(
            start=41,
            text="http://example.org",
            source="postprocess",
            label="annotationSupplementaire",
        ),
    ]

    expected_output = PostProcessOutput(
        added_entities=expected_entities,
    )

    postpro = PostProcessFromText(text=text, entities=[], checklist=[])
    output = postpro.match_additional_terms(
        additional_terms_str=additional_terms_str,
        separators=["/"],
        ignore_accents=False,
        ignore_case=False,
    )

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_entangled_additional_terms():
    text = "Ce texte contient une annotation supplémentaire."
    additional_terms_str = "annotation / annotation supplémentaire"

    expected_entities = [
        NamedEntity(
            text="annotation supplémentaire",
            start=22,
            label="annotationSupplementaire",
            source="postprocess",
        )
    ]

    expected_output = PostProcessOutput(
        added_entities=expected_entities,
    )

    postpro = PostProcessFromText(text=text, entities=[], checklist=[])
    output = postpro.match_additional_terms(
        additional_terms_str=additional_terms_str,
        separators=["/"],
        ignore_accents=False,
        ignore_case=False,
    )

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


@pytest.mark.skip(reason="En attente d'arbitrage sur ce point")
def test_additional_term_and_other_entity():
    text = "Ce texte parle du cheval blanc d'Henri IV."
    additional_terms_str = "cheval blanc d'Henri IV"
    input_entities = [
        NamedEntity(
            text="Henri IV",
            start=33,
            label="personnePhysique",
            source="NER model",
        )
    ]
    expected_entities = [
        NamedEntity(
            start=18,
            text="cheval blanc d'Henri IV",
            source="postprocess",
            label="annotationSupplementaire",
        ),
    ]

    expected_output = PostProcessOutput(
        added_entities=expected_entities,
        deleted_entities=input_entities,
    )

    postpro = PostProcessFromText(text=text, entities=input_entities, checklist=[])

    output = postpro.match_additional_terms(
        additional_terms_str=additional_terms_str,
        separators=["/"],
        ignore_accents=False,
        ignore_case=False,
    )

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )
