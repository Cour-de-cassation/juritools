import pytest
from juritools.postprocessing import PostProcessFromText
from juritools.type import NamedEntity
import pandas as pd
from io import StringIO


def test_juvenile_facility_entities():

    ml_pred = []
    text = "Etablissement pénitentiaire spécialisé pour mineurs du Rhône"
    postpro = PostProcessFromText(text, ml_pred, manual_checklist=[])
    postpro.juvenile_facility_entities()

    assert postpro.entities == [
        NamedEntity(
            text="Etablissement pénitentiaire spécialisé pour mineurs du Rhône",
            start=0,
            end=60,
            label="etablissement",
            source="postprocess",
        )
    ]


def test_check_cadastre():

    ml_pred = []
    text_no_cadastre = "Amaury et Valentin mangent à la Cour."
    text_cadastre = "Les parcelles cadastrées A82 et B72."
    postpro_no_cadastre = PostProcessFromText(
        text_no_cadastre, ml_pred, manual_checklist=[]
    )
    postpro_no_cadastre.check_cadastre()
    assert len(postpro_no_cadastre.manual_checklist) == 0
    postpro_cadastre = PostProcessFromText(text_cadastre, ml_pred, manual_checklist=[])
    postpro_cadastre.check_cadastre()
    assert len(postpro_cadastre.manual_checklist) == 1


def test_check_compte_bancaire():

    ml_pred = []
    text_no_bank_account = "Amaury et Valentin mangent à la Cour."
    text_bank_account = "Son numéro de compte bancaire est le 81212."
    postpro_no_bank_account = PostProcessFromText(
        text_no_bank_account, ml_pred, manual_checklist=[]
    )
    postpro_no_bank_account.check_compte_bancaire()
    assert len(postpro_no_bank_account.manual_checklist) == 0
    postpro_bank_account = PostProcessFromText(
        text_bank_account, ml_pred, manual_checklist=[]
    )
    postpro_bank_account.check_compte_bancaire()
    assert len(postpro_bank_account.manual_checklist) == 1


def test_match_from_category():

    ml_pred = [
        NamedEntity(
            text="BILLY",
            start=0,
            end=5,
            label="professionnelavocat",
            source="NER model",
        ),
        NamedEntity(
            text="John", start=9, end=13, label="personnephysique", source="NER model"
        ),
        NamedEntity(
            text="Doe", start=14, end=17, label="personnephysique", source="NER model"
        ),
        NamedEntity(
            text="John Doe",
            start=21,
            end=29,
            label="personnephysique",
            source="NER model",
        ),
    ]

    text = "BILLY et John Doe et John Doe et John et JOHN"

    postpro = PostProcessFromText(text, ml_pred, manual_checklist=[])
    expected = postpro.match_from_category(["personnephysique"])

    assert expected == {"John", "JOHN"}
    assert postpro.entities[-2].text == "John"
    assert postpro.entities[-2].start == 33
    assert postpro.entities[-2].end == 37
    assert postpro.entities[-2].label == "personnephysique"
    assert postpro.entities[-2].source == "postprocess"
    assert postpro.entities[-1].text == "JOHN"
    assert postpro.entities[-1].start == 41
    assert postpro.entities[-1].end == 45
    assert postpro.entities[-1].label == "personnephysique"
    assert postpro.entities[-1].source == "postprocess"


def test_manage_le():

    ml_pred = [
        NamedEntity(
            text="LE", start=3, end=5, label="personnephysique", source="NER model"
        ),
        NamedEntity(
            text="Fouret",
            start=47,
            end=53,
            label="personnephysique",
            source="NER model",
        ),
    ]

    text = "M. LE Préfet est attendu aujourd'hui. Monsieur Fouret est ici."

    postpro = PostProcessFromText(text, ml_pred, manual_checklist=[])
    assert len(postpro.entities) == 2

    expected = postpro.manage_le()

    assert expected == 1
    assert len(postpro.entities) == 1
    assert postpro.entities[0].text == "Fouret"


def test_manage_quote():

    ml_pred = [
        NamedEntity(
            text='" Amaury',
            start=0,
            end=8,
            label="personnephysique",
            source="NER model",
        ),
        NamedEntity(
            text="'Valentin »",
            start=9,
            end=20,
            label="personnephysique",
            source="NER model",
        ),
        NamedEntity(
            text='"TUNING2000',
            start=21,
            end=32,
            label="personnemorale",
            source="NER model",
        ),
        NamedEntity(
            text='"', start=33, end=34, label="personnephysique", source="NER model"
        ),
    ]

    text = '''" Amaury 'Valentin » "TUNING2000 "'''

    postpro = PostProcessFromText(text, ml_pred, manual_checklist=[])
    expected = postpro.manage_quote()

    assert expected == 4
    assert postpro.entities[0].text == "Amaury"
    assert postpro.entities[0].start == 2
    assert postpro.entities[0].end == 8
    assert postpro.entities[1].text == "Valentin"
    assert postpro.entities[1].start == 10
    assert postpro.entities[1].end == 18
    assert postpro.entities[2].text == '"TUNING2000'
    assert postpro.entities[2].start == 21
    assert postpro.entities[2].end == 32
    assert len(postpro.entities) == 3


def test_check_metadata():

    ml_pred = [
        NamedEntity(
            text="Amaury",
            start=0,
            end=6,
            label="professionnelavocat",
            source="NER model",
        ),
        NamedEntity(
            text="Amaury",
            start=26,
            end=32,
            label="personnephysique",
            source="NER model",
        ),
        NamedEntity(
            text="Martin",
            start=33,
            end=41,
            label="professionnelavocat",
            source="NER model",
        ),
    ]

    text = "Pauline est bien seule dans ce texte."

    meta = pd.DataFrame(
        data={
            "text": ["Amaury", "Pauline", "Martin", "John", "Billy"],
            "entity": [
                "personnephysique",
                "personnephysique",
                "professionnelavocat",
                "professionnelavocat",
                "personnephysique",
            ],
        }
    )

    postpro = PostProcessFromText(text, ml_pred, manual_checklist=[], metadata=meta)
    expected = postpro.check_metadata()

    assert len(postpro.manual_checklist) == 1
    assert len(expected) == 1
    assert expected[0] == "Pauline"


def test_match_metadata_jurica():

    ml_pred = []

    text = "Amaury FOURET et Amaury GLE sont cousins de Romain GLE."

    meta_str = "text,entity\r\nAmaury,personnePhysique\r\nFOURET,personnePhysique\r\nRomain,personnePhysique\r\nGLE,personnePhysique\r\n"
    meta = pd.read_csv(StringIO(meta_str))

    postpro = PostProcessFromText(text, ml_pred, manual_checklist=[], metadata=meta)
    expected = postpro.match_metadata_jurica()

    assert len(expected) == 6
    assert postpro.entities == [
        NamedEntity(
            text="Amaury",
            start=0,
            end=6,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="FOURET",
            start=7,
            end=13,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="Amaury",
            start=17,
            end=23,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="GLE", start=24, end=27, label="personnePhysique", source="postprocess"
        ),
        NamedEntity(
            text="Romain",
            start=44,
            end=50,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="GLE", start=51, end=54, label="personnePhysique", source="postprocess"
        ),
    ]


def test_match_metadata_jurinet():

    ml_pred = []

    text = "SCP Serrano et Glé, Amaury Fouret, Gérard Jean."

    meta_str = "ID_DOCUMENT,TYPE_PERSONNE,ID_PARTIE,NATURE_PARTIE,TYPE_PARTIE,ID_TITRE,NOM,PRENOM,NOM_MARITAL,AUTRE_PRENOM,ALIAS,SIGLE,DOMICILIATION,LIG_ADR1,LIG_ADR2,LIG_ADR3,CODE_POSTAL,NOM_COMMUNE,NUMERO\r\n1725609,AVOCAT,12272125,0,,SCP,Serrano et Glé,,,,,,,,,,,,52011060\r\n1725609,AVOCAT,12272126,0,,SARL,Cabinet Dupont,,,,,,,,,,,,52011060\r\n1725609,AVOG,0,0,,Mme,Durand,Anne-Marie,,,,,,,,,,,52011060\r\n1725609,COMPO_GREFFIER,0,0,,Mme,Cassel,Florence,,,,,,,,,,,52011060\r\n1725609,COMPO_PRESIDENT,0,0,,M.,Jean,Gérard,,,,,,,,,,,52011060\r\n1725609,CONSRAP,0,0,,M.,Nolan,Michel,,,,,,,,,,,52011060\r\n1725609,PARTIE,12272125,1,PP,M,Fouret,Amaury,,,,,5 quai de l'horloge,,,,75001,Paris,52011060\r\n1725609,PARTIE,12272126,2,PM,STE,8J PLOC,,,,,,25 rue de Strasbourg,,,,92400,Courbevoie,52011060\r\n"
    meta = pd.read_csv(StringIO(meta_str))

    postpro = PostProcessFromText(text, ml_pred, manual_checklist=[], metadata=meta)
    expected = postpro.match_metadata_jurinet()

    assert len(expected) == 2
    assert postpro.entities == [
        NamedEntity(
            text="Amaury",
            start=20,
            end=26,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="Fouret",
            start=27,
            end=33,
            label="personnePhysique",
            source="postprocess",
        ),
    ]


def test_match_regex():

    ml_pred = []
    text = "Son IBAN est FR4330003000405419435692V57. Son numéro de CB n'est pas 4929 6437 9847 4381 mais 4929 6437 9847 4380"
    postpro = PostProcessFromText(text, ml_pred, manual_checklist=[])
    postpro.match_regex()
    assert postpro.entities == [
        NamedEntity(
            text="FR4330003000405419435692V57",
            start=13,
            end=40,
            label="compteBancaire",
            source="regex",
        ),
        NamedEntity(
            text="4929 6437 9847 4380",
            start=94,
            end=113,
            label="compteBancaire",
            source="regex",
        ),
    ]


def test_match_name_in_website():
    ml_pred = [
        NamedEntity(
            text="Romain", start=0, end=6, label="personnePhysique", source="NER model"
        ),
        NamedEntity(
            text="Jardin Hivernal",
            start=120,
            end=135,
            label="personneMorale",
            source="NER model",
        ),
    ]
    text = "Romain adminisitre son site internet https://www.lamaisonderomaingle.com avec brio. Il gère aussi le site de sa société Jardin Hivernal : http://jardinhivernal.fr"
    postpro = PostProcessFromText(text, ml_pred, manual_checklist=[])
    expected = postpro.match_name_in_website(legal_entity=True)
    assert expected == ["lamaisonderomaingle", "jardinhivernal"]
    assert postpro.entities[2] == NamedEntity(
        text="lamaisonderomaingle",
        start=49,
        end=68,
        label="siteWebSensible",
        source="regex",
    )
    assert postpro.entities[3] == NamedEntity(
        text="jardinhivernal",
        start=145,
        end=159,
        label="siteWebSensible",
        source="regex",
    )


def test_output_json():

    ml_pred = []
    text = "Ceci est un test"
    postpro = PostProcessFromText(text, ml_pred, manual_checklist=[])
    postpro.entities = [
        NamedEntity(
            text="Amaury",
            start=0,
            end=6,
            label="professionnelAvocat",
            source="NER model",
        )
    ]
    expected = postpro.output_json()
    assert (
        expected
        == '{\n    "entities": [\n        {\n            "text": "Amaury",\n            "start": 0,\n            "end": 6,\n            "label": "professionnelAvocat",\n            "source": "NER model",\n            "score": 1.0\n        }\n    ],\n    "checklist": []\n}'
    )
