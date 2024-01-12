from juritools.type import Decision
from jurispacy_tokenizer import JuriSpacyTokenizer
from juritools.predict import load_ner_model
from juritools.preprocess import PreProcess
import pandas as pd
import os

# Windows Fix for PosixPath issue
if os.name == "nt":
    import pathlib

    temp = pathlib.PosixPath
    pathlib.PosixPath = pathlib.WindowsPath

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "model")
model = load_ner_model(os.path.join(FIXTURE_DIR, "new_categories_model.pt"))
tokenizer = JuriSpacyTokenizer()


def test_preprocess_juritj_metdata():
    decision = Decision(
        idLabel="1234",
        idDecision="1234",
        sourceId=1234,
        sourceName="juritj",
        text="...",
        parties=[
            {"prenom": "Paul", "nom": "Dupont", "type": "PP", "qualite": "F"},
            {"prenom": "Amaury", "nom": "Belette", "type": "PM", "qualite": "G"},
            {"prenom": "Rio", "nom": "Grande", "type": "AA", "qualite": "G"},
        ],
    )

    preprocess = PreProcess(
        decision=decision,
        tokenizer=tokenizer,
        model=model,
    )

    expected_metadata = pd.DataFrame(
        {
            "text": ["Paul", "Dupont"],
            "entity": ["personnePhysique", "personnePhysique"],
        },
    )

    assert preprocess.metadata.to_csv(index=False) == expected_metadata.to_csv(index=False)


def test_preprocess_jurica_metadata():
    decision = Decision(
        idLabel="1234",
        idDecision="1234",
        sourceId=1234,
        sourceName="jurica",
        text="...",
        parties=[
            {"identite": "Paul Dupont", "attributes": {"typePersonne": "PP", "qualitePartie": "F"}},
            {"identite": "Amaury Belette", "attributes": {"typePersonne": "PM", "qualitePartie": "G"}},
            {"identite": "Rio Grande", "attributes": {"typePersonne": "AA", "qualitePartie": "G"}},
        ],
    )

    preprocess = PreProcess(
        decision=decision,
        tokenizer=tokenizer,
        model=model,
    )

    expected_metadata = pd.DataFrame(
        {
            "text": ["Paul", "Dupont"],
            "entity": ["personnePhysique", "personnePhysique"],
        },
    )

    assert preprocess.metadata.to_csv(index=False) == expected_metadata.to_csv(index=False)


def test_preprocess_jurinet_metadata():
    col_list = [
        "ID_DOCUMENT",
        "TYPE_PERSONNE",
        "ID_PARTIE",
        "NATURE_PARTIE",
        "TYPE_PARTIE",
        "ID_TITRE",
        "NOM",
        "PRENOM",
        "NOM_MARITAL",
        "AUTRE_PRENOM",
        "ALIAS",
        "SIGLE",
        "DOMICILIATION",
        "LIG_ADR1",
        "LIG_ADR2",
        "LIG_ADR3",
        "CODE_POSTAL",
        "NOM_COMMUNE",
        "NUMERO",
    ]
    raw_parties = ",,,,,,Dupont,Paul,,,,,,,,,,,"
    decision = Decision(
        idLabel="1234",
        idDecision="1234",
        sourceId=1234,
        sourceName="jurinet",
        text="...",
        parties=[raw_parties.split(",")],
    )

    preprocess = PreProcess(
        decision=decision,
        tokenizer=tokenizer,
        model=model,
    )

    expected_metadata = pd.DataFrame(
        {
            "PRENOM": ["Paul"],
            "NOM": ["Dupont"],
        },
    )
    for c in col_list:
        if c not in expected_metadata.columns:
            expected_metadata[c] = ""
    expected_metadata = expected_metadata[col_list]

    assert preprocess.metadata.to_csv(index=False) == expected_metadata.to_csv(index=False)


# Reproducing Unit tests from nlp-pseudonymisation-api


def test_process_metadata_jurinet_old():
    """Testing preprocessing of Jurinet metadata"""
    parties = [
        [
            1725609,
            "AVOCAT",
            12272125,
            0,
            None,
            "SCP",
            "Pat Patrouille",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "52011060",
        ],
        [
            1725609,
            "AVOCAT",
            12272125,
            0,
            None,
            "SCP",
            "Boul et Bill",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "52011060",
        ],
    ]

    preprocess = PreProcess(
        decision=Decision(
            idLabel="1234",
            idDecision="1234",
            sourceId=1234,
            sourceName="jurinet",
            parties=parties,
            text="...",
        ),
        tokenizer=tokenizer,
        model=model,
    )
    assert (
        preprocess.metadata.to_csv(index=False).replace("\r", "")
        == "ID_DOCUMENT,TYPE_PERSONNE,ID_PARTIE,NATURE_PARTIE,TYPE_PARTIE,ID_TITRE,NOM,"
        "PRENOM,NOM_MARITAL,AUTRE_PRENOM,ALIAS,SIGLE,DOMICILIATION,LIG_ADR1,LIG_ADR2,LIG"
        "_ADR3,CODE_POSTAL,NOM_COMMUNE,NUMERO\n1725609,AVOCAT,12272125,0,,SCP,Pat Patro"
        "uille,,,,,,,,,,,,52011060\n1725609,AVOCAT,12272125,0,,SCP,Boul et Bill,,,,,,,,"
        ",,,,52011060\n"
    )


def test_process_metadata_jurica_old():
    """Testing preprocessing of Jurica metadata"""
    parties = [
        {
            "attributes": {"qualitePartie": "I", "typePersonne": "PP"},
            "identite": "Monsieur Amaury FOURET",
        },
        {
            "attributes": {"qualitePartie": "K", "typePersonne": "PP"},
            "identite": "Monsieur Romain GLE inconnu",
        },
        {
            "attributes": {"qualitePartie": "K", "typePersonne": "PM"},
            "identite": "S.A.R.L. LE BON BURGER",
        },
    ]

    preprocess = PreProcess(
        decision=Decision(
            idLabel="1234",
            idDecision="1234",
            sourceId=1234,
            sourceName="jurica",
            parties=parties,
            text="...",
        ),
        tokenizer=tokenizer,
        model=model,
    )

    csv_metadata = preprocess.metadata.to_csv(index=False).replace("\r", "")

    assert csv_metadata == (
        "text,entity\n"
        "Amaury,personnePhysique\n"
        "FOURET,personnePhysique\n"
        "Romain,personnePhysique\n"
        "GLE,personnePhysique\n"
    ), csv_metadata


def test_process_metadata_none():
    """Testing preprocessing of empty metadata"""
    parties = None
    preprocess = PreProcess(
        decision=Decision(
            idLabel="1234",
            idDecision="1234",
            sourceId=1234,
            sourceName="jurica",
            parties=parties,
            text="...",
        ),
        tokenizer=tokenizer,
        model=model,
    )

    assert preprocess.metadata is None
