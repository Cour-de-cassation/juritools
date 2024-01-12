import pytest

from juritools.type import NamedEntity, merge_entities


def test_named_entity_overlaps():
    other_data = {"source": "NER model", "label": "personnePhysique"}
    n1 = NamedEntity(text="World", start=0, **other_data)
    n2 = NamedEntity(text="World", start=5, **other_data)
    n3 = NamedEntity(text="World", start=2, **other_data)
    n4 = NamedEntity(text="WorldWorld", start=2, **other_data)
    assert not n1.overlaps_with_other_entity(n2)
    assert n1.overlaps_with_other_entity(n3)
    assert n2.overlaps_with_other_entity(n3)
    assert n4.overlaps_with_other_entity(n3)
    assert n3.overlaps_with_other_entity(n4)


def test_named_entity_comparison_operators():
    other_data = {"source": "NER model", "label": "personnePhysique"}
    n1 = NamedEntity(text="World", start=0, **other_data)
    n2 = NamedEntity(text="World", start=5, **other_data)

    assert n1 < n2
    assert n2 > n1


def test_merge_entities():
    # text = "X" * 9
    other_data = {"source": "NER model", "label": "personnePhysique"}
    n1 = NamedEntity(text="XXX", start=0, **other_data)
    n2 = NamedEntity(text="XXX", start=3, **other_data)
    n3 = NamedEntity(text="XXX", start=6, **other_data)

    n4 = NamedEntity(text="XXXXXX", start=0, **other_data)
    n5 = NamedEntity(text="XXXXXX", start=3, **other_data)
    n6 = NamedEntity(text="XXXXXXXXX", start=0, **other_data)

    n7 = merge_entities(n1, n2)
    n8 = merge_entities(n3, n2)
    n9 = merge_entities(n2, n6)

    n10 = merge_entities(n2, n1)
    n11 = merge_entities(n2, n3)
    n12 = merge_entities(n6, n2)

    assert n7 == n4
    assert n8 == n5
    assert n9 == n6

    assert n10 == n7
    assert n11 == n8
    assert n12 == n9

    with pytest.raises(ValueError):
        merge_entities(n1, n3)

    with pytest.raises(ValueError):
        merge_entities(n3, n1)
