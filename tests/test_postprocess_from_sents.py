import pytest
from juritools.postprocessing import PostProcessFromSents
from juritools.type import NamedEntity
from jurispacy_tokenizer import JuriSpacyTokenizer
from flair.data import Sentence, Token
import pandas as pd

tokenizer = JuriSpacyTokenizer()


def test_match_against_case():
    s = Sentence("")
    firstname = Token("Amaury", start_position=0)
    s._add_token(firstname)
    print(s)
    s[:1].set_label("ner", "professionnelAvocat")
    print(s.get_spans("ner"))
    flair_sentences = [
        Sentence(""),
        Sentence(""),
        Sentence(""),
        s,
        Sentence("C/"),
        Sentence("Urszula"),
    ]
    ml_pred = [
        NamedEntity(
            text="Amaury",
            start=0,
            end=6,
            label="professionnelAvocat",
            source="NER model",
        )
    ]
    postpro = PostProcessFromSents(flair_sentences, ml_pred, manual_checklist=[])
    expected = postpro.apply_methods(
        match_cities=False,
        match_facilities=False,
        match_siren_and_siret=False,
        match_phone_numbers=False,
        check_compte_bancaire=False,
        change_pro_no_context=False,
        change_pro_with_context=False,
    )
    assert expected == ["Amaury"]
    assert postpro.entities == [
        NamedEntity(
            text="Amaury", start=0, end=6, label="personnePhysique", source="NER model"
        )
    ]


def test_match_cities():
    flair_sentences = [
        Sentence(
            "Il habite L'Abergement-Clémenciat et 92400 MARSEILLE à la fois.",
            use_tokenizer=tokenizer,
            start_position=0,
        ),
        Sentence(
            "Son village s'appelle Bosc Roger sur Buchy (23488), surprenant non ?",
            use_tokenizer=tokenizer,
            start_position=57,
        ),
        Sentence(
            "Le tribunal de 92400 Nanterre a rendu son verdict.",
            use_tokenizer=tokenizer,
            start_position=117,
        ),
        Sentence(
            "Bienvenue à 92400 Courbevoie.", use_tokenizer=tokenizer, start_position=140
        ),
        Sentence("---==oO§Oo==---", use_tokenizer=tokenizer, start_position=170),
    ]
    ml_pred = [
        NamedEntity(
            text="Courbevoie", start=152, end=162, label="localite", source="NER Model"
        )
    ]
    postpro = PostProcessFromSents(flair_sentences, ml_pred, manual_checklist=[])
    expected = postpro.apply_methods(
        match_against=False,
        match_facilities=False,
        match_siren_and_siret=False,
        match_phone_numbers=False,
        check_compte_bancaire=False,
        change_pro_no_context=False,
        change_pro_with_context=False,
    )
    print(postpro.entities)
    assert postpro.entities == [
        NamedEntity(
            text="Courbevoie", start=152, end=162, label="localite", source="NER Model"
        ),
        NamedEntity(
            text="92400", start=37, end=42, label="localite", source="postprocess"
        ),
        NamedEntity(
            text="L'Abergement-Clémenciat",
            start=10,
            end=33,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="MARSEILLE", start=43, end=52, label="localite", source="postprocess"
        ),
        NamedEntity(
            text="23488", start=101, end=106, label="localite", source="postprocess"
        ),
        NamedEntity(
            text="Bosc Roger sur Buchy",
            start=79,
            end=99,
            label="localite",
            source="postprocess",
        ),
    ]
    assert expected[0] == "92400"
    assert expected[1] == "L'Abergement Clemenciat"
    assert expected[2] == "MARSEILLE"
    assert expected[3] == "23488"
    assert expected[4] == "Bosc Roger sur Buchy"
    assert len(expected) == 5


def test_match_facilities():
    flair_sentences = [
        Sentence("Il va à l'école Jules Ferry.", use_tokenizer=tokenizer),
        Sentence(
            "Son cours à lieu à l'Université Pierre et Marie Curie.",
            use_tokenizer=tokenizer,
            start_position=29,
        ),
        Sentence("Bienvenue à Courbevoie.", use_tokenizer=tokenizer, start_position=82),
        Sentence(
            "Il a séjourné à l'hôpital de la Sainte Marie Madeleine.",
            use_tokenizer=tokenizer,
            start_position=140,
        ),
    ]
    for sent in flair_sentences:
        if sent.start_position:
            for token in sent:
                token.start_position += sent.start_position

    ml_pred = []
    postpro = PostProcessFromSents(flair_sentences, ml_pred, manual_checklist=[])
    expected = postpro.apply_methods(
        match_against=False,
        match_cities=False,
        match_siren_and_siret=False,
        match_phone_numbers=False,
        check_compte_bancaire=False,
        change_pro_no_context=False,
        change_pro_with_context=False,
    )
    assert expected[0] == "Jules Ferry"
    assert expected[1] == "Pierre et Marie Curie"
    assert expected[2] == "Sainte Marie Madeleine"
    assert len(expected) == 3


def test_check_compte_bancaire():
    flair_sentences = [
        Sentence(
            "Son numéro de compte bancaire est 7457568743.", use_tokenizer=tokenizer
        )
    ]
    ml_pred = []
    postpro = PostProcessFromSents(flair_sentences, ml_pred, manual_checklist=[])
    expected = postpro.apply_methods(
        match_against=False,
        match_cities=False,
        match_facilities=False,
        match_siren_and_siret=False,
        match_phone_numbers=False,
        change_pro_no_context=False,
        change_pro_with_context=False,
    )
    assert expected[0] == "Son numéro de compte bancaire est 7457568743."
    assert postpro.manual_checklist == [
        "Il semblerait qu'un ou plusieurs numéros de comptes bancaires n'aient pas été repérées"
    ]


def test_match_siren_siret():
    flair_sentences = [
        Sentence(
            "Son SIREN est 732829320 et son SIRET est 73282932012345.",
            use_tokenizer=tokenizer,
        )
    ]
    ml_pred = []
    postpro = PostProcessFromSents(flair_sentences, ml_pred, manual_checklist=[])
    expected = postpro.apply_methods(
        match_against=False,
        match_cities=False,
        match_facilities=False,
        match_phone_numbers=False,
        check_compte_bancaire=False,
        change_pro_no_context=False,
        change_pro_with_context=False,
    )
    assert expected[0] == "732829320"
    assert expected[1] == "73282932012345"


def test_match_phone_numbers():
    flair_sentences = [
        Sentence("Son numéro de tél. est le +33612121212.", use_tokenizer=tokenizer),
        Sentence("0101010101", use_tokenizer=tokenizer),
    ]
    ml_pred = []
    postpro = PostProcessFromSents(flair_sentences, ml_pred, manual_checklist=[])
    expected = postpro.apply_methods(
        match_against=False,
        match_cities=False,
        match_facilities=False,
        match_siren_and_siret=False,
        check_compte_bancaire=False,
        change_pro_no_context=False,
        change_pro_with_context=False,
    )
    assert len(expected) == 1
    assert expected[0] == "+33612121212"


def test_overlapping_entities():
    flair_sentences = [
        Sentence(
            "Il habite dans un hôtel particulier de Neuilly sur Seine.",
            use_tokenizer=tokenizer,
            start_position=0,
        )
    ]
    ml_pred = []
    postpro = PostProcessFromSents(flair_sentences, ml_pred, manual_checklist=[])
    expected = postpro.apply_methods(
        match_against=False,
        match_siren_and_siret=False,
        check_compte_bancaire=False,
        change_pro_no_context=False,
        change_pro_with_context=False,
    )
    assert postpro.entities == [
        NamedEntity(
            text="Neuilly sur Seine",
            start=39,
            end=56,
            label="localite",
            source="postprocess",
        )
    ]


def test_change_pro_to_physique_no_context():
    flair_sentences = [
        Sentence("Amaury Fouret,", use_tokenizer=tokenizer, start_position=0)
    ]
    flair_sentences[0][:1].set_label("ner", "professionnelMagistratGreffier")
    flair_sentences[0][1:2].set_label("ner", "professionnelMagistratGreffier")
    ml_pred = [
        NamedEntity(
            text="Amaury",
            start=0,
            end=6,
            label="professionnelMagistratGreffier",
            source="NER",
        ),
        NamedEntity(
            text="Fouret",
            start=7,
            end=13,
            label="professionnelMagistratGreffier",
            source="NER",
        ),
    ]

    postpro = PostProcessFromSents(flair_sentences, ml_pred, manual_checklist=[])
    expected = postpro.apply_methods(
        match_against=False,
        match_siren_and_siret=False,
        check_compte_bancaire=False,
        match_phone_numbers=False,
        match_cities=False,
        change_pro_no_context=True,
        change_pro_with_context=False,
    )
    assert expected == ["Amaury", "Fouret"]
    assert postpro.entities == [
        NamedEntity(
            text="Amaury",
            start=0,
            end=6,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="Fouret",
            start=7,
            end=13,
            label="personnePhysique",
            source="postprocess",
        ),
    ]


def test_match_cities_in_moral():

    flair_sentences = []
    ml_pred = [
        NamedEntity(
            text="Lyon",
            start=0,
            end=4,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="Nantes",
            start=5,
            end=11,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="Lyon Nantes Maçonnerie",
            start=12,
            end=34,
            label="personneMorale",
            source="NER model",
        ),
        NamedEntity(
            text="Nantes les bons gâteaux",
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
            text="Rennes",
            start=79,
            end=85,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="SCP Nantes-Rennes",
            start=86,
            end=103,
            label="personneMorale",
            source="NER model",
        ),
        NamedEntity(
            text="My little fabric RENNES",
            start=104,
            end=127,
            label="personneMorale",
            source="NER model",
        ),
    ]

    postpro = PostProcessFromSents(flair_sentences, ml_pred, manual_checklist=[])
    expected = postpro.match_cities_in_moral(False)
    print(postpro.entities)
    assert len(expected) == 3
    assert postpro.entities == [
        NamedEntity(
            text="Lyon",
            start=0,
            end=4,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="Nantes",
            start=5,
            end=11,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="Le café du Commerce",
            start=59,
            end=78,
            label="personneMorale",
            source="NER model",
        ),
        NamedEntity(
            text="Rennes",
            start=79,
            end=85,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="Lyon",
            start=12,
            end=16,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="Nantes",
            start=17,
            end=23,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="Nantes",
            start=35,
            end=41,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="Nantes",
            start=90,
            end=96,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="Rennes",
            start=97,
            end=103,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="Rennes",
            start=121,
            end=127,
            label="localite",
            source="postprocess",
        ),
    ]


def test_match_union_delegate():
    """Testing `union delegate` reassignment"""
    first_name = "Paul"
    last_name = "Déchorgnat"
    flair_sentences = [
        Sentence(
            f"Représenté par {first_name} {last_name} (Délégué syndical ouvrier)",
            use_tokenizer=tokenizer,
            start_position=0,
        ),
        # Sentence(
        #     f"Représentant : M. {first_name} {last_name} (Défenseur syndical ouvrier)",
        #     use_tokenizer=tokenizer,
        #     start_position=100
        # ),
        # Sentence(
        #     f"Représentant : M. {first_name} {last_name} (Délégué syndical ouvrier)",
        #     use_tokenizer=tokenizer,
        #     start_position=200
        # ),
        # Sentence(
        #     f"représentée par {first_name} {last_name}, défenseur syndical",
        #     use_tokenizer=tokenizer,
        #     start_position=300
        # ),
        # Sentence(
        #     f"représentée par M. {first_name} {last_name} en sa qualité de défenseur syndical",
        #     use_tokenizer=tokenizer,
        #     start_position=400
        # )
    ]

    ml_predictions = []
    exepected_postprocessing_entitities = []

    for sentence in flair_sentences:
        for token in sentence:
            if token.text in [first_name, last_name]:
                token.set_label("ner", "professionnelMagistratGreffier")
                ml_predictions.append(
                    NamedEntity(
                        text=token.text,
                        start=token.idx,
                        end=token.idx + len(token.text),
                        label="professionnelMagistratGreffier",
                        source="NER",
                    )
                )
                exepected_postprocessing_entitities.append(
                    NamedEntity(
                        text=token.text,
                        start=token.idx,
                        end=token.idx + len(token.text),
                        label="personnePhysique",
                        source="postprocess",
                    )
                )

    postprocessing_result = PostProcessFromSents(
        flair_sentences=flair_sentences,
        entities=ml_predictions,
        manual_checklist=[],  # TODO: vérifier avec Amaury
    )

    postprocessing_entity_texts = postprocessing_result.apply_methods(
        match_against=False,
        match_siren_and_siret=False,
        check_compte_bancaire=False,
        match_phone_numbers=False,
        match_cities=False,
        change_pro_no_context=False,
        change_pro_with_context=True,
    )

    assert postprocessing_entity_texts == [first_name, last_name]
    assert postprocessing_result.entities == exepected_postprocessing_entitities
