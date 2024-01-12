import pandas as pd
from jurispacy_tokenizer import JuriSpacyTokenizer

from juritools.postprocessing import PostProcessFromEntities
from juritools.type import Check, CheckTypeEnum, NamedEntity, PostProcessOutput
from tests.testing_utils import assert_equality_between_entities, assert_equality_between_outputs

tokenizer = JuriSpacyTokenizer()


def test_split_entity_multi_toks():
    input_entities = [
        NamedEntity(
            text="Marie Claire",
            start=0,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Marie",
            start=13,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="Claire",
            start=19,
            label="personnePhysique",
            source="postprocess",
        ),
    ]

    expected_entities = [
        NamedEntity(
            text="Marie",
            start=0,
            label="personnePhysique",
            source="postprocess",
            entityId="personnePhysique_marie",
        ),
        NamedEntity(
            text="Claire",
            start=6,
            label="personnePhysique",
            source="postprocess",
            entityId="personnePhysique_claire",
        ),
        NamedEntity(
            text="Marie",
            start=13,
            label="personnePhysique",
            source="postprocess",
            entityId="personnePhysique_marie",
        ),
        NamedEntity(
            text="Claire",
            start=19,
            label="personnePhysique",
            source="postprocess",
            entityId="personnePhysique_claire",
        ),
    ]

    expected_output = PostProcessOutput(
        deleted_entities=[
            NamedEntity(
                text="Marie Claire",
                start=0,
                label="personnePhysique",
                source="NER model",
            ),
        ],
        added_entities=[
            NamedEntity(
                text="Marie",
                start=0,
                label="personnePhysique",
                source="postprocess",
                entityId="personnePhysique_marie",
            ),
            NamedEntity(
                text="Claire",
                start=6,
                label="personnePhysique",
                source="postprocess",
                entityId="personnePhysique_claire",
            ),
        ],
    )

    postpro = PostProcessFromEntities(
        entities=input_entities,
        checklist=[],
        tokenizer=tokenizer,
    )

    output = postpro.split_entity_multi_toks()

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )

    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_match_address_in_moral():
    input_entities = [
        NamedEntity(
            text="du 141 quai de Valmy",
            start=0,
            label="personneMorale",
            source="NER model",
        )
    ]

    expected_entities = [
        NamedEntity(
            text="du 141 quai de Valmy",
            start=0,
            label="adresse",
            source="postprocess",
        )
    ]

    expected_output = PostProcessOutput(
        modified_entities=[
            NamedEntity(
                text="du 141 quai de Valmy",
                start=0,
                label="adresse",
                source="postprocess",
            )
        ]
    )

    postpro = PostProcessFromEntities(
        input_entities,
        checklist=[],
        tokenizer=tokenizer,
    )
    output = postpro.match_address_in_moral()

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )

    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_check_entities():
    input_entities = [
        NamedEntity(
            text="Pauline",
            start=0,
            label="professionnelAvocat",
            source="NER model",
        ),
        NamedEntity(
            text="Pauline",
            start=26,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Martin",
            start=33,
            label="professionnelAvocat",
            source="NER model",
        ),
        NamedEntity(
            text="amaury",
            start=40,
            label="professionnelMagistratGreffier",
            source="NER model",
        ),
        NamedEntity(
            text="AmAuRÿ",
            start=47,
            label="personnePhysique",
            source="NER model",
        ),
    ]

    expected_checklists = [
        Check(
            check_type=CheckTypeEnum.different_categories,
            entities=[
                NamedEntity(
                    text="Pauline",
                    start=0,
                    label="professionnelAvocat",
                    source="NER model",
                ),
                NamedEntity(
                    text="Pauline",
                    start=26,
                    label="personnePhysique",
                    source="NER model",
                ),
            ],
        ),
        Check(
            check_type=CheckTypeEnum.different_categories,
            entities=[
                NamedEntity(
                    text="amaury",
                    start=40,
                    label="professionnelMagistratGreffier",
                    source="NER model",
                ),
                NamedEntity(
                    text="AmAuRÿ",
                    start=47,
                    label="personnePhysique",
                    source="NER model",
                ),
            ],
        ),
    ]

    expected_output = PostProcessOutput(added_checklist=expected_checklists)

    postpro = PostProcessFromEntities(
        input_entities,
        checklist=[],
        tokenizer=tokenizer,
    )
    output = postpro.check_entities()

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert postpro.checklist == expected_checklists


# @pytest.mark.skip(
#     reason="personnePhysiqueNom et personnePhysiquePrenom are one category personnePhysique now"
# )
# def test_manage_natural_persons():
#     input_entities = [
#         NamedEntity(
#             text="Amaury",
#             start=0,
#            #             label="personnephysiquenom",
#             source="NER model",
#         ),
#         NamedEntity(
#             text="amaury",
#             start=0,
#            #             label="personnephysiqueprenom",
#             source="NER model",
#         ),
#         NamedEntity(
#             text="AmaurY",
#             start=0,
#            #             label="personnephysiqueprenom",
#             source="NER model",
#         ),
#         NamedEntity(
#             text="Valentin",
#             start=0,
#            #             label="personnephysiqueprenom",
#             source="NER model",
#         ),
#         NamedEntity(
#             text="Valentin",
#             start=0,
#            #             label="personnephysiquenom",
#             source="NER model",
#         ),
#     ]

#     postpro = PostProcessFromEntities(input_entities, checklist=[], tokenizer=tokenizer)
#     expected = postpro.manage_natural_persons()

#     assert len(expected) == 1
#     assert expected == {"amaury"}
#     assert postpro.entities[0].label.value == "personnePhysique"


# TODO: Vérifier avec Amaury
def test_change_pro_to_physique():
    input_entities = [
        NamedEntity(
            text="Joëlle",
            start=0,
            label="professionnelMagistratGreffier",
            source="NER model",
        ),
        NamedEntity(
            text="Joëlle",
            start=7,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Remoulade",
            start=14,
            label="professionnelMagistratGreffier",
            source="NER model",
        ),
        NamedEntity(
            text="Joëlle",
            start=26,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Valentin",
            start=33,
            label="professionnelAvocat",
            source="NER model",
        ),
    ]

    input_metadata = pd.DataFrame(
        data={
            "text": [
                "Rémoulade",
                "Valentin",
                "Valentin",
            ],
            "entity": [
                "personnePhysique",
                "personnePhysique",
                "professionnelAvocat",
            ],
        }
    )

    expected_entities = [
        NamedEntity(
            text="Joëlle",
            start=0,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="Joëlle",
            start=7,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Remoulade",
            start=14,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="Joëlle",
            start=26,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Valentin",
            start=33,
            label="personnePhysique",
            source="postprocess",
        ),
    ]

    expected_output = PostProcessOutput(
        modified_entities=[
            NamedEntity(
                text="Joëlle",
                start=0,
                label="personnePhysique",
                source="postprocess",
            ),
            NamedEntity(
                text="Remoulade",
                start=14,
                label="personnePhysique",
                source="postprocess",
            ),
            NamedEntity(
                text="Valentin",
                start=33,
                label="personnePhysique",
                source="postprocess",
            ),
        ]
    )

    postpro = PostProcessFromEntities(
        input_entities,
        checklist=[],
        metadata=input_metadata,
        tokenizer=tokenizer,
    )
    output = postpro.change_pro_to_physique(use_meta=True)

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )

    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_match_localite_in_adress():
    input_entities = [
        NamedEntity(
            text="92022 NANTERRE CEDEX",
            start=1104,
            label="adresse",
            source="NER model",
        ),
        NamedEntity(
            text="34 rue de l'Armée, 92022 NANTERRE CEDEX",
            start=1250,
            label="adresse",
            source="NER model",
        ),
    ]

    expected_entities = [
        NamedEntity(
            text="92022 NANTERRE CEDEX",
            start=1104,
            label="localite",
            source="postprocess",
            entityId="localite_92022 nanterre cedex",
        ),
        NamedEntity(
            text="34 rue de l'Armée, 92022 NANTERRE CEDEX",
            start=1250,
            label="adresse",
            source="NER model",
            entityId="adresse_34 rue de l'armee, 92022 nanterre cedex",
        ),
    ]
    expected_output = PostProcessOutput(
        modified_entities=[
            NamedEntity(
                text="92022 NANTERRE CEDEX",
                start=1104,
                label="localite",
                source="postprocess",
                entityId="localite_92022 nanterre cedex",
            ),
        ]
    )

    postpro = PostProcessFromEntities(
        input_entities,
        checklist=[],
        tokenizer=tokenizer,
    )
    output = postpro.match_localite_in_adress()

    assert expected_output == output
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_manage_year_in_date():
    input_entities = [
        NamedEntity(
            text="11 Septembre 1992",
            start=0,
            label="dateNaissance",
            source="NER model",
        ),
        NamedEntity(
            text="1942",
            start=18,
            label="dateNaissance",
            source="NER model",
        ),
        NamedEntity(
            text="4 février 2021",
            start=23,
            label="dateMariage",
            source="NER model",
        ),
    ]

    expected_entities = [
        NamedEntity(
            text="11 Septembre",
            start=0,
            label="dateNaissance",
            source="postprocess",
            entityId="dateNaissance_11 septembre",
        ),
        NamedEntity(
            text="4 février",
            start=23,
            label="dateMariage",
            source="postprocess",
            entityId="dateMariage_4 février",
        ),
    ]

    expected_output = PostProcessOutput(
        modified_entities=[
            NamedEntity(
                text="11 Septembre",
                start=0,
                label="dateNaissance",
                source="postprocess",
                entityId="dateNaissance_11 septembre",
            ),
            NamedEntity(
                text="4 février",
                start=23,
                label="dateMariage",
                source="postprocess",
                entityId="dateMariage_4 février",
            ),
        ],
        deleted_entities=[
            NamedEntity(
                text="1942",
                start=18,
                label="dateNaissance",
                source="NER model",
            ),
        ],
    )

    postpro = PostProcessFromEntities(
        input_entities,
        checklist=[],
        tokenizer=tokenizer,
    )
    output = postpro.manage_year_in_date()

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_match_natural_persons_in_moral():
    input_entities = [
        NamedEntity(
            text="Jean",
            start=0,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Dupont",
            start=5,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Jean Dupont Maçonnerie",
            start=12,
            label="personneMorale",
            source="NER model",
        ),
        NamedEntity(
            text="Dupont les bons gâteaux",
            start=35,
            label="personneMorale",
            source="NER model",
        ),
        NamedEntity(
            text="Le café du Commerce",
            start=59,
            label="personneMorale",
            source="NER model",
        ),
        NamedEntity(
            text="Cardin",
            start=79,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="SCP Dupont-Cardin",
            start=86,
            label="personneMorale",
            source="NER model",
        ),
        NamedEntity(
            text="My little fabric CARDIN",
            start=104,
            label="personneMorale",
            source="NER model",
        ),
        NamedEntity(
            text="Martin-Simon",
            start=128,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Martin & Simon Mystères",
            start=141,
            label="personneMorale",
            source="NER model",
        ),
    ]

    expected_entities = [
        NamedEntity(
            text="Jean",
            start=0,
            label="personnePhysique",
            source="NER model",
            entityId="personnePhysique_jean",
        ),
        NamedEntity(
            text="Dupont",
            start=5,
            label="personnePhysique",
            source="NER model",
            entityId="personnePhysique_dupont",
        ),
        NamedEntity(
            text="Jean",
            start=12,
            label="personnePhysique",
            source="postprocess",
            entityId="personnePhysique_jean",
        ),
        NamedEntity(
            text="Dupont",
            start=17,
            label="personnePhysique",
            source="postprocess",
            entityId="personnePhysique_dupont",
        ),
        NamedEntity(
            text="Dupont",
            start=35,
            label="personnePhysique",
            source="postprocess",
            entityId="personnePhysique_dupont",
        ),
        NamedEntity(
            text="Le café du Commerce",
            start=59,
            label="personneMorale",
            source="NER model",
            entityId="personneMorale_le cafe du commerce",
        ),
        NamedEntity(
            text="Cardin",
            start=79,
            label="personnePhysique",
            source="NER model",
            entityId="personnePhysique_cardin",
        ),
        NamedEntity(
            text="Dupont",
            start=90,
            label="personnePhysique",
            source="postprocess",
            entityId="personnePhysique_dupont",
        ),
        NamedEntity(
            text="Cardin",
            start=97,
            label="personnePhysique",
            source="postprocess",
            entityId="personnePhysique_cardin",
        ),
        NamedEntity(
            text="Cardin",
            start=121,
            label="personnePhysique",
            source="postprocess",
            entityId="personnePhysique_cardin",
        ),
        NamedEntity(
            text="Martin-Simon",
            start=128,
            label="personnePhysique",
            source="NER model",
            entityId="personnePhysique_martin-simon",
        ),
        NamedEntity(
            text="Martin",
            start=141,
            label="personnePhysique",
            source="postprocess",
            entityId="personnePhysique_martin",
        ),
        NamedEntity(
            text="Simon",
            start=150,
            label="personnePhysique",
            source="postprocess",
            entityId="personnePhysique_simon",
        ),
    ]

    expected_output = PostProcessOutput(
        added_entities=[
            NamedEntity(
                text="Jean",
                start=12,
                label="personnePhysique",
                source="postprocess",
                entityId="personnePhysique_jean",
            ),
            NamedEntity(
                text="Dupont",
                start=17,
                label="personnePhysique",
                source="postprocess",
                entityId="personnePhysique_dupont",
            ),
            NamedEntity(
                text="Dupont",
                start=35,
                label="personnePhysique",
                source="postprocess",
                entityId="personnePhysique_dupont",
            ),
            NamedEntity(
                text="Dupont",
                start=90,
                label="personnePhysique",
                source="postprocess",
                entityId="personnePhysique_dupont",
            ),
            NamedEntity(
                text="Cardin",
                start=97,
                label="personnePhysique",
                source="postprocess",
                entityId="personnePhysique_cardin",
            ),
            NamedEntity(
                text="Cardin",
                start=121,
                label="personnePhysique",
                source="postprocess",
                entityId="personnePhysique_cardin",
            ),
            NamedEntity(
                text="Martin",
                start=141,
                label="personnePhysique",
                source="postprocess",
                entityId="personnePhysique_martin",
            ),
            NamedEntity(
                text="Simon",
                start=150,
                label="personnePhysique",
                source="postprocess",
                entityId="personnePhysique_simon",
            ),
        ],
        deleted_entities=[
            NamedEntity(
                text="Jean Dupont Maçonnerie",
                start=12,
                label="personneMorale",
                source="NER model",
            ),
            NamedEntity(
                text="SCP Dupont-Cardin",
                start=86,
                label="personneMorale",
                source="NER model",
            ),
            NamedEntity(
                text="Dupont les bons gâteaux",
                start=35,
                label="personneMorale",
                source="NER model",
            ),
            NamedEntity(
                text="My little fabric CARDIN",
                start=104,
                label="personneMorale",
                source="NER model",
            ),
            NamedEntity(
                text="Martin & Simon Mystères",
                start=141,
                label="personneMorale",
                source="NER model",
            ),
        ],
    )

    postpro = PostProcessFromEntities(input_entities, checklist=[], tokenizer=tokenizer)
    output = postpro.match_natural_persons_in_moral(False)

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_check_similarities():
    input_entities = [
        NamedEntity(
            text="Jean",
            start=0,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Gérard",
            start=5,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Jeah",
            start=12,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Gerart",
            start=35,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Gérard",
            start=79,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Martin",
            start=128,
            label="personnePhysique",
            source="NER model",
        ),
    ]
    expected_output = PostProcessOutput(
        added_checklist=[
            Check(
                check_type=CheckTypeEnum.similar_writing,
                entities=[
                    NamedEntity(
                        text="Jean",
                        start=0,
                        label="personnePhysique",
                        source="NER model",
                    ),
                    NamedEntity(
                        text="Jeah",
                        start=12,
                        label="personnePhysique",
                        source="NER model",
                    ),
                ],
            ),
        ]
    )
    expected_entities = input_entities
    postpro = PostProcessFromEntities(
        input_entities,
        checklist=[],
        tokenizer=tokenizer,
    )
    output = postpro.check_similarities()

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_match_natural_persons_in_moral_complicated():
    input_entities = [
        NamedEntity(
            text="La super entreprise de Paul le beau gosse Dupont SAS",
            label="personneMorale",
            start=0,
            source="NER model",
        ),
        NamedEntity(
            start=100,
            text="Paul",
            source="NER model",
            label="personnePhysique",
        ),
        NamedEntity(
            start=200,
            text="Dupont",
            source="NER model",
            label="personnePhysique",
        ),
    ]

    expected_entities = [
        NamedEntity(
            start=23,
            text="Paul",
            source="postprocess",
            label="personnePhysique",
        ),
        NamedEntity(
            text="Dupont",
            start=42,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            start=100,
            text="Paul",
            source="NER model",
            label="personnePhysique",
        ),
        NamedEntity(
            start=200,
            text="Dupont",
            source="NER model",
            label="personnePhysique",
        ),
    ]

    expected_output = PostProcessOutput(
        added_entities=[
            NamedEntity(
                start=23,
                text="Paul",
                source="postprocess",
                label="personnePhysique",
            ),
            NamedEntity(
                text="Dupont",
                start=42,
                label="personnePhysique",
                source="postprocess",
            ),
        ],
        deleted_entities=[
            NamedEntity(
                text="La super entreprise de Paul le beau gosse Dupont SAS",
                label="personneMorale",
                start=0,
                source="NER model",
            ),
        ],
    )

    postpro = PostProcessFromEntities(
        entities=input_entities,
        checklist=[],
        tokenizer=tokenizer,
    )
    output = postpro.match_natural_persons_in_moral()

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_check_entities_no_match():
    input_entities = [
        NamedEntity(**d)
        for d in [
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
    ]

    expected_entities = input_entities

    expected_output = PostProcessOutput()

    postpro = PostProcessFromEntities(
        entities=input_entities,
        checklist=[],
        tokenizer=tokenizer,
    )
    output = postpro.check_entities()

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )
