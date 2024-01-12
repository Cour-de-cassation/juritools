from itertools import zip_longest
from pprint import pprint

from juritools.type import NamedEntity, PostProcessOutput


def assert_equality_between_entities(
    expected_entities: list[NamedEntity],
    actual_entities: list[NamedEntity],
):
    for index, (expected_entity, result_entity) in enumerate(
        zip_longest(
            expected_entities,
            actual_entities,
            fillvalue="missing",
        )
    ):
        print(index)
        print("ACTUAL ⬇️")
        pprint(result_entity)
        pprint(expected_entity)
        print("EXPECTED ⬆️")
    assert expected_entities == actual_entities


def assert_equality_between_outputs(
    expected_output: PostProcessOutput,
    actual_output: PostProcessOutput,
):
    print("ACTUAL OUTPUT")
    pprint(actual_output.model_dump())
    print("EXPECTED OUTPUT")
    pprint(expected_output.model_dump())

    assert actual_output == expected_output
    assert actual_output == expected_output
