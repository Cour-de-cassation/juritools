import pytest
from juritools.postprocessing import PostProcessFromEntities
from juritools.type import NamedEntity
from jurispacy_tokenizer import JuriSpacyTokenizer
import pandas as pd

tokenizer = JuriSpacyTokenizer()


def test_split_entity_multi_toks():
    ml_pred = [
        NamedEntity(
            text="Marie Claire",
            start=0,
            end=12,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Marie",
            start=13,
            end=18,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="Claire",
            start=19,
            end=25,
            label="personnePhysique",
            source="postprocess",
        ),
    ]
    postpro = PostProcessFromEntities(ml_pred, manual_checklist=[], tokenizer=tokenizer)
    expected = postpro.split_entity_multi_toks()
    assert postpro.entities == [
        NamedEntity(
            text="Marie",
            start=13,
            end=18,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="Claire",
            start=19,
            end=25,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="Marie",
            start=0,
            end=5,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="Claire",
            start=6,
            end=12,
            label="personnePhysique",
            source="postprocess",
        ),
    ]


def test_match_address_in_moral():
    ml_pred = [
        NamedEntity(
            text="du 141 quai de Valmy",
            start=0,
            end=19,
            label="personneMorale",
            source="NER model",
        )
    ]
    postpro = PostProcessFromEntities(ml_pred, manual_checklist=[], tokenizer=tokenizer)
    expected = postpro.match_address_in_moral()
    assert postpro.entities == [
        NamedEntity(
            text="du 141 quai de Valmy",
            start=0,
            end=19,
            label="adresse",
            source="postprocess",
        )
    ]


def test_check_entities():

    ml_pred = [
        NamedEntity(
            text="Pauline",
            start=0,
            end=6,
            label="professionnelavocat",
            source="NER model",
        ),
        NamedEntity(
            text="Pauline",
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

    postpro = PostProcessFromEntities(ml_pred, manual_checklist=[], tokenizer=tokenizer)
    expected = postpro.check_entities()

    assert expected == [("Pauline", "personnephysique", ["professionnelavocat"])]
    assert postpro.manual_check == True
    assert (
        postpro.manual_checklist[0]
        == "L'annotation 'Pauline' est de catégorie 'personnephysique' mais on retrouve la même annotation dans une autre catégorie 'professionnelavocat'. Les annotations sont-elles réellement de catégories différentes ?"
    )


@pytest.mark.skip(
    reason="Les catégories personnePhysiqueNom et personnePhysiquePrenom sont réunies dans la catégorie personnePhysique"
)
def test_manage_natural_persons():
    ml_pred = [
        NamedEntity(
            text="Amaury",
            start=0,
            end=60,
            label="personnephysiquenom",
            source="NER model",
        ),
        NamedEntity(
            text="amaury",
            start=0,
            end=160,
            label="personnephysiqueprenom",
            source="NER model",
        ),
        NamedEntity(
            text="AmaurY",
            start=0,
            end=60,
            label="personnephysiqueprenom",
            source="NER model",
        ),
        NamedEntity(
            text="Valentin",
            start=0,
            end=60,
            label="personnephysiqueprenom",
            source="NER model",
        ),
        NamedEntity(
            text="Valentin",
            start=0,
            end=60,
            label="personnephysiquenom",
            source="NER model",
        ),
    ]

    postpro = PostProcessFromEntities(ml_pred, manual_checklist=[], tokenizer=tokenizer)
    expected = postpro.manage_natural_persons()

    assert len(expected) == 1
    assert expected == {"amaury"}
    assert postpro.entities[0].label == "personnephysiqueprenom"


def test_change_pro_to_physique():

    ml_pred = [
        NamedEntity(
            text="Amaury",
            start=0,
            end=6,
            label="professionnelmagistratgreffier",
            source="NER model",
        ),
        NamedEntity(
            text="Amaury",
            start=7,
            end=13,
            label="personnephysique",
            source="NER model",
        ),
        NamedEntity(
            text="Remoulade",
            start=14,
            end=25,
            label="professionnelmagistratgreffier",
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
            text="Valentin",
            start=33,
            end=41,
            label="professionnelavocat",
            source="NER model",
        ),
    ]

    meta = pd.DataFrame(
        data={
            "text": ["Rémoulade", "Valentin", "Valentin"],
            "entity": [
                "personnephysique",
                "personnephysique",
                "professionnelavocat",
            ],
        }
    )

    postpro = PostProcessFromEntities(
        ml_pred, manual_checklist=[], metadata=meta, tokenizer=tokenizer
    )
    expected = postpro.change_pro_to_physique(use_meta=True)

    assert len(expected) == 2
    assert postpro.entities[0].label == "personnephysique"
    assert postpro.entities[2].label == "personnephysique"
    assert postpro.entities[4].label == "professionnelavocat"


def test_match_localite_in_adress():
    ml_pred = [
        NamedEntity(
            text="92022 NANTERRE CEDEX",
            start=1104,
            end=1124,
            label="adresse",
            source="NER model",
        ),
        NamedEntity(
            text="J'habite à 34 rue de l'Armée, 92022 NANTERRE CEDEX",
            start=1250,
            end=1890,
            label="adresse",
            source="NER model",
        ),
        NamedEntity(
            text="34 rue de l'Armée, 92022 NANTERRE CEDEX",
            start=1250,
            end=1540,
            label="adresse",
            source="NER model",
        ),
    ]
    postpro = PostProcessFromEntities(ml_pred, manual_checklist=[], tokenizer=tokenizer)
    expected = postpro.match_localite_in_adress()
    assert postpro.entities == [
        NamedEntity(
            text="92022 NANTERRE CEDEX",
            start=1104,
            end=1124,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="J'habite à 34 rue de l'Armée, 92022 NANTERRE CEDEX",
            start=1250,
            end=1890,
            label="adresse",
            source="NER model",
        ),
        NamedEntity(
            text="34 rue de l'Armée, 92022 NANTERRE CEDEX",
            start=1250,
            end=1540,
            label="adresse",
            source="NER model",
        ),
    ]


def test_manage_year_in_date():

    ml_pred = [
        NamedEntity(
            text="11 Septembre 1992",
            start=0,
            end=17,
            label="datedenaissance",
            source="NER model",
        ),
        NamedEntity(
            text="1942",
            start=18,
            end=22,
            label="datedenaissance",
            source="NER model",
        ),
        NamedEntity(
            text="4 février 2021",
            start=23,
            end=39,
            label="datedemariage",
            source="NER model",
        ),
    ]

    postpro = PostProcessFromEntities(ml_pred, manual_checklist=[], tokenizer=tokenizer)
    expected = postpro.manage_year_in_date()

    assert len(expected) == 3
    assert expected == ["11 Septembre", "1942", "4 février"]
    assert postpro.entities == [
        NamedEntity(
            text="11 Septembre",
            start=0,
            end=12,
            label="datedenaissance",
            source="NER model",
        ),
        NamedEntity(
            text="4 février",
            start=23,
            end=34,
            label="datedemariage",
            source="NER model",
        ),
    ]


def test_match_natural_persons_in_moral():

    ml_pred = [
        NamedEntity(
            text="Jean",
            start=0,
            end=4,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Dupont",
            start=5,
            end=11,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Jean Dupont Maçonnerie",
            start=12,
            end=34,
            label="personneMorale",
            source="NER model",
        ),
        NamedEntity(
            text="Dupont les bons gâteaux",
            start=35,
            end=58,
            label="personneMorale",
            source="NER model",
        ),
        NamedEntity(
            text="Le café du Commerce",
            start=59,
            end=78,
            label="personneMorale",
            source="NER model",
        ),
        NamedEntity(
            text="Cardin",
            start=79,
            end=85,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="SCP Dupont-Cardin",
            start=86,
            end=103,
            label="personneMorale",
            source="NER model",
        ),
        NamedEntity(
            text="My little fabric CARDIN",
            start=104,
            end=127,
            label="personneMorale",
            source="NER model",
        ),
    ]

    postpro = PostProcessFromEntities(ml_pred, manual_checklist=[], tokenizer=tokenizer)
    expected = postpro.match_natural_persons_in_moral(False)
    print(postpro.entities)
    assert len(expected) == 3
    assert postpro.entities == [
        NamedEntity(
            text="Jean",
            start=0,
            end=4,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Dupont",
            start=5,
            end=11,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Le café du Commerce",
            start=59,
            end=78,
            label="personneMorale",
            source="NER model",
        ),
        NamedEntity(
            text="Cardin",
            start=79,
            end=85,
            label="personnePhysique",
            source="NER model",
        ),
        NamedEntity(
            text="Jean",
            start=12,
            end=16,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="Dupont",
            start=17,
            end=23,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="Dupont",
            start=35,
            end=41,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="Dupont",
            start=90,
            end=96,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="Cardin",
            start=97,
            end=103,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="Cardin",
            start=121,
            end=127,
            label="personnePhysique",
            source="postprocess",
        ),
    ]
