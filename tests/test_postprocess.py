from juritools.postprocessing import PostProcess
from juritools.type import NamedEntity, CategoryEnum


def test_sort_entities():
    entities = [
        NamedEntity(
            start=300,
            label="personnePhysique",
            text="Hello",
            source="NER model",
        ),
        NamedEntity(
            start=200,
            label="personnePhysique",
            text="Hello",
            source="NER model",
        ),
        NamedEntity(
            start=100,
            label="personneMorale",
            text="Hello",
            source="NER model",
        ),
        NamedEntity(
            start=0,
            label="personneMorale",
            text="Hello",
            source="NER model",
        ),
    ]

    postpro = PostProcess(
        entities=entities,
        checklist=[],
        metadata=None,
    )

    assert postpro.entities == entities
    assert postpro.start_ents == [e.start for e in entities]
    assert postpro.end_ents == [e.end for e in entities]
    assert postpro.entities_by_category[CategoryEnum.personnePhysique] == [entities[0], entities[1]]
    assert postpro.entities_by_category[CategoryEnum.personneMorale] == [entities[2], entities[3]]

    postpro.sort_entities()

    assert postpro.entities == sorted(entities)
    assert postpro.start_ents == [0, 100, 200, 300]
    assert postpro.end_ents == [5, 105, 205, 305]
    assert postpro.entities_by_category[CategoryEnum.personnePhysique] == [entities[1], entities[0]]
    assert postpro.entities_by_category[CategoryEnum.personneMorale] == [entities[3], entities[2]]
