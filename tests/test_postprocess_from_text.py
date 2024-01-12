import json
from io import StringIO

import pandas as pd

from juritools.postprocessing import PostProcessFromText
from juritools.type import Check, CheckTypeEnum, NamedEntity, PostProcessOutput, CategoryEnum
from tests.testing_utils import assert_equality_between_entities, assert_equality_between_outputs


def test_juvenile_facility_entities():
    input_entities = []
    text = "Etablissement pénitentiaire spécialisé pour mineurs du Rhône"

    expected_entities = [
        NamedEntity(
            text="Etablissement pénitentiaire spécialisé pour mineurs du Rhône",
            start=0,
            label="etablissement",
            source="postprocess",
        )
    ]

    expected_output = PostProcessOutput(
        added_entities=expected_entities,
    )

    postpro = PostProcessFromText(text, input_entities, checklist=[])
    output = postpro.juvenile_facility_entities()

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )

    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_check_cadastre():
    text_no_cadastre = "Amaury et Valentin mangent à la Cour."
    input_entities = []
    expected_entities = []
    expected_output = PostProcessOutput()

    postpro = PostProcessFromText(
        text_no_cadastre,
        input_entities,
        checklist=[],
    )
    output = postpro.check_cadastre()

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )

    text_cadastre = "Les parcelles cadastrées A82 et B72."
    input_entities = []
    expected_entities = []
    expected_output = PostProcessOutput(added_checklist=[Check(check_type=CheckTypeEnum.missing_cadatre)])

    postpro = PostProcessFromText(
        text_cadastre,
        input_entities,
        checklist=[],
    )
    output = postpro.check_cadastre()

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_check_compte_bancaire():
    text_no_bank_account = "Amaury et Valentin mangent à la Cour."
    input_entities = []
    expected_entities = []
    expected_output = PostProcessOutput()

    postpro = PostProcessFromText(
        text_no_bank_account,
        input_entities,
        checklist=[],
    )
    output = postpro.check_compte_bancaire()

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )

    text_bank_account = "Son numéro de compte bancaire est le 81212."
    input_entities = []
    expected_entities = []
    expected_output = PostProcessOutput(added_checklist=[Check(check_type=CheckTypeEnum.missing_bank_account)])

    postpro = PostProcessFromText(
        text_bank_account,
        input_entities,
        checklist=[],
    )
    output = postpro.check_compte_bancaire()

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_match_from_category():
    text = "BILLY et John Doe et John Doe et Jöhn et JOHN"
    input_entities = [
        NamedEntity(
            text="BILLY",
            start=0,
            label="professionnelAvocat",
            source="NER model",
        ),
        NamedEntity(
            text="John",
            start=9,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Doe",
            start=14,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="John Doe",
            start=21,
            label="personnePhysique",
            source="NER model",
        ),
    ]

    expected_entities = [
        NamedEntity(
            text="BILLY",
            start=0,
            label="professionnelAvocat",
            source="NER model",
        ),
        NamedEntity(
            text="John",
            start=9,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Doe",
            start=14,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="John Doe",
            start=21,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Jöhn",
            start=33,
            source="postprocess",
            label="personnePhysique",
        ),
        NamedEntity(
            text="JOHN",
            start=41,
            source="postprocess",
            label="personnePhysique",
        ),
    ]

    expected_output = PostProcessOutput(
        added_entities=[
            NamedEntity(
                text="Jöhn",
                start=33,
                source="postprocess",
                label="personnePhysique",
            ),
            NamedEntity(
                text="JOHN",
                start=41,
                source="postprocess",
                label="personnePhysique",
            ),
        ]
    )

    postpro = PostProcessFromText(text, input_entities, checklist=[])
    output = postpro.match_from_category([CategoryEnum.personnePhysique])

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_manage_le():
    text = "M. LE Préfet est attendu aujourd'hui. Monsieur Fouret est ici."

    input_entities = [
        NamedEntity(
            text="LE",
            start=3,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Fouret",
            start=47,
            label="personnePhysique",
            source="NER model",
        ),
    ]

    expected_entities = [
        NamedEntity(
            text="Fouret",
            start=47,
            label="personnePhysique",
            source="NER model",
        ),
    ]

    expected_output = PostProcessOutput(
        deleted_entities=[
            NamedEntity(
                text="LE",
                start=3,
                label="personnePhysique",
                source="NER model",
            ),
        ]
    )

    postpro = PostProcessFromText(text, input_entities, checklist=[])
    output = postpro.manage_le()

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_manage_quote():
    text = '''" Amaury 'Valentin » "TUNING2000 "'''
    input_entities = [
        NamedEntity(
            text='" Amaury',
            start=0,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="'Valentin »",
            start=9,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text='"TUNING2000',
            start=21,
            label="personneMorale",
            source="NER model",
        ),
        NamedEntity(
            text='"',
            start=33,
            label="personnePhysique",
            source="NER model",
        ),
    ]
    expected_entities = [
        NamedEntity(
            text="Amaury",
            start=2,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="Valentin",
            start=10,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text='"TUNING2000',
            start=21,
            label="personneMorale",
            source="NER model",
        ),
    ]

    expected_output = PostProcessOutput(
        modified_entities=expected_entities[:-1],
        deleted_entities=[
            NamedEntity(
                text='"',
                start=33,
                label="personnePhysique",
                source="NER model",
            ),
        ],
    )

    postpro = PostProcessFromText(text, input_entities, checklist=[])
    output = postpro.manage_quote()

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_check_metadata():
    text = "Pauline est bien seule dans ce texte."

    input_entities = [
        NamedEntity(
            text="Amaury",
            start=0,
            label="professionnelAvocat",
            source="NER model",
        ),
        NamedEntity(
            text="Amaury",
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
    ]

    input_metadata = pd.DataFrame(
        data={
            "text": [
                "Amaury",
                "Pauline",
                "Martin",
                "John",
                "Billy",
            ],
            "entity": [
                "personnePhysique",
                "personnePhysique",
                "professionnelAvocat",
                "professionnelAvocat",
                "personnePhysique",
            ],
        }
    )

    expected_entities = input_entities

    expected_output = PostProcessOutput(
        added_checklist=[
            Check(
                check_type=CheckTypeEnum.incorrect_metadata,
                metadata_text=["Pauline"],
            )
        ]
    )

    postpro = PostProcessFromText(
        text,
        input_entities,
        checklist=[],
        metadata=input_metadata,
    )
    output = postpro.check_metadata()

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_match_metadata_jurica():
    text = "Amaury FOURET et Amaury GLE sont cousins de Romain GLE."

    input_metadata = pd.DataFrame(
        [
            {"text": "Amaury", "entity": "personnePhysique"},
            {"text": "FOURET", "entity": "personnePhysique"},
            {"text": "Romain", "entity": "personnePhysique"},
            {"text": "GLE", "entity": "personnePhysique"},
        ]
    )

    input_entities = []

    expected_entities = [
        NamedEntity(
            text="Amaury",
            start=0,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="FOURET",
            start=7,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="Amaury",
            start=17,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="GLE",
            start=24,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="Romain",
            start=44,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="GLE",
            start=51,
            label="personnePhysique",
            source="postprocess",
        ),
    ]

    expected_output = PostProcessOutput(added_entities=expected_entities)

    postpro = PostProcessFromText(
        text,
        input_entities,
        checklist=[],
        metadata=input_metadata,
    )
    output = postpro.match_metadata_jurica()

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_match_metadata_jurinet():
    text = "SCP Serrano et Glé, Amaury Fouret, Gérard Jean."

    input_entities = []
    meta_str = "ID_DOCUMENT,TYPE_PERSONNE,ID_PARTIE,NATURE_PARTIE,TYPE_PARTIE,ID_TITRE,NOM,PRENOM,NOM_MARITAL,AUTRE_PRENOM,ALIAS,SIGLE,DOMICILIATION,LIG_ADR1,LIG_ADR2,LIG_ADR3,CODE_POSTAL,NOM_COMMUNE,NUMERO\r\n1725609,AVOCAT,12272125,0,,SCP,Serrano et Glé,,,,,,,,,,,,52011060\r\n1725609,AVOCAT,12272126,0,,SARL,Cabinet Dupont,,,,,,,,,,,,52011060\r\n1725609,AVOG,0,0,,Mme,Durand,Anne-Marie,,,,,,,,,,,52011060\r\n1725609,COMPO_GREFFIER,0,0,,Mme,Cassel,Florence,,,,,,,,,,,52011060\r\n1725609,COMPO_PRESIDENT,0,0,,M.,Jean,Gérard,,,,,,,,,,,52011060\r\n1725609,CONSRAP,0,0,,M.,Nolan,Michel,,,,,,,,,,,52011060\r\n1725609,PARTIE,12272125,1,PP,M,Fouret,Amaury,,,,,5 quai de l'horloge,,,,75001,Paris,52011060\r\n1725609,PARTIE,12272126,2,PM,STE,8J PLOC,,,,,,25 rue de Strasbourg,,,,92400,Courbevoie,52011060\r\n"  # noqa: E501
    input_metadata = pd.read_csv(StringIO(meta_str))

    expected_entities = [
        NamedEntity(
            text="Amaury",
            start=20,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="Fouret",
            start=27,
            label="personnePhysique",
            source="postprocess",
        ),
    ]

    expected_output = PostProcessOutput(added_entities=expected_entities)

    postpro = PostProcessFromText(
        text,
        input_entities,
        checklist=[],
        metadata=input_metadata,
    )
    output = postpro.match_metadata_jurinet()

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_match_regex():
    input_entities = []
    text = "Son IBAN est FR4330003000405419435692V57. Son numéro de CB n'est pas 4929 6437 9847 4381 mais 4929 6437 9847 4380"  # noqa: E501

    expected_entities = [
        NamedEntity(
            text="FR4330003000405419435692V57",
            start=13,
            label="compteBancaire",
            source="postprocess",
        ),
        NamedEntity(
            text="4929 6437 9847 4380",
            start=94,
            label="compteBancaire",
            source="postprocess",
        ),
    ]

    expected_output = PostProcessOutput(
        added_entities=expected_entities,
    )

    postpro = PostProcessFromText(text, input_entities, checklist=[])
    output = postpro.match_regex()

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_match_name_in_website():
    text = "Romain adminisitre son site internet https://www.lamaisonderomaingle.com avec brio. Il gère aussi le site de sa société Jardin Hivernal : http://jardinhivernal.fr"  # noqa: E501

    input_entities = [
        NamedEntity(
            text="Romain",
            start=0,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Jardin Hivernal",
            start=120,
            label="personneMorale",
            source="NER model",
        ),
    ]

    expected_entities = [
        NamedEntity(
            text="Romain",
            start=0,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="lamaisonderomaingle",
            start=49,
            label="siteWebSensible",
            source="postprocess",
        ),
        NamedEntity(
            text="Jardin Hivernal",
            start=120,
            label="personneMorale",
            source="NER model",
        ),
        NamedEntity(
            text="jardinhivernal",
            start=145,
            label="siteWebSensible",
            source="postprocess",
        ),
    ]

    expected_output = PostProcessOutput(
        added_entities=[
            NamedEntity(
                text="lamaisonderomaingle",
                start=49,
                label="siteWebSensible",
                source="postprocess",
            ),
            NamedEntity(
                text="jardinhivernal",
                start=145,
                label="siteWebSensible",
                source="postprocess",
            ),
        ]
    )

    postpro = PostProcessFromText(text, input_entities, checklist=[])
    output = postpro.match_name_in_website(legal_entity=True)

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_output_json():
    text = "Ceci est un test"
    input_entities = []
    postpro = PostProcessFromText(
        text,
        input_entities,
        checklist=[],
    )
    postpro.entities = [
        NamedEntity(
            text="Amaury",
            start=0,
            label="professionnelAvocat",
            source="NER model",
        )
    ]
    expected = postpro.output_json()
    assert json.loads(expected) == {
        "entities": [
            {
                "text": "Amaury",
                "start": 0,
                "end": 6,
                "label": "professionnelAvocat",
                "source": "NER model",
                "score": 1.0,
                "entityId": "professionnelAvocat_amaury",
            }
        ],
        "checklist": [],
    }
