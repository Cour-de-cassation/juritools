from flair.data import Sentence, Token
from jurispacy_tokenizer import JuriSpacyTokenizer

from juritools.postprocessing import PostProcessFromSents
from juritools.type import Check, CheckTypeEnum, NamedEntity, PostProcessOutput, SentenceIndexes
from tests.testing_utils import assert_equality_between_entities, assert_equality_between_outputs

tokenizer = JuriSpacyTokenizer()


def test_match_against_case():
    # preparing data
    s = Sentence("")
    firstname = Token("Amaury", start_position=0)
    s._add_token(firstname)
    s[:1].set_label("ner", "professionnelAvocat")

    input_sentences = [
        Sentence(""),
        Sentence(""),
        Sentence(""),
        s,
        Sentence("C/"),
        Sentence("Urszula"),
    ]
    input_entities = [
        NamedEntity(
            text="Amaury",
            start=0,
            label="professionnelAvocat",
            source="NER model",
        )
    ]
    expected_entities = [
        NamedEntity(
            text="Amaury",
            start=0,
            label="personnePhysique",
            source="postprocess",
        )
    ]

    expected_output = PostProcessOutput(modified_entities=expected_entities)

    postpro = PostProcessFromSents(
        input_sentences,
        input_entities,
        checklist=[],
    )
    output = postpro.apply_methods(
        match_against=True,
        match_cities=False,
        match_facilities=False,
        match_regex_with_context=False,
        change_pro_no_context=False,
        change_pro_with_context=False,
        check_compte_bancaire=False,
    )

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_match_cities():
    input_sentences = [
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
            "Bienvenue à 92400 Courbevoie.",
            use_tokenizer=tokenizer,
            start_position=140,
        ),
        Sentence(
            "---==oO§Oo==---",
            use_tokenizer=tokenizer,
            start_position=170,
        ),
    ]
    input_entities = [
        NamedEntity(
            text="Courbevoie",
            start=152,
            label="localite",
            source="NER model",
        )
    ]

    expected_entities = [
        NamedEntity(
            text="L'Abergement-Clémenciat",
            start=10,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="92400",
            start=37,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="MARSEILLE",
            start=43,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="Bosc Roger sur Buchy",
            start=79,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="23488",
            start=101,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="Courbevoie",
            start=152,
            label="localite",
            source="NER model",
        ),
    ]

    expected_output = PostProcessOutput(
        added_entities=expected_entities[:-1],
    )

    postpro = PostProcessFromSents(input_sentences, input_entities, checklist=[])
    output = postpro.apply_methods(
        match_against=False,
        match_facilities=False,
        match_regex_with_context=False,
        check_compte_bancaire=False,
        change_pro_no_context=False,
        change_pro_with_context=False,
    )

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_match_facilities():
    input_sentences = [
        Sentence(
            "Il va à l'école Jules Ferry.",
            use_tokenizer=tokenizer,
        ),
        Sentence(
            "Son cours à lieu à l'Université Pierre et Marie Curie.",
            use_tokenizer=tokenizer,
            start_position=29,
        ),
        Sentence(
            "Bienvenue à Courbevoie.",
            use_tokenizer=tokenizer,
            start_position=82,
        ),
        Sentence(
            "Il a séjourné à l'hôpital de la Sainte Marie Madeleine.",
            use_tokenizer=tokenizer,
            start_position=140,
        ),
    ]
    for sent in input_sentences:
        if sent.start_position:
            for token in sent:
                token.start_position += sent.start_position

    input_entities = []

    expected_entities = [
        NamedEntity(
            text="Jules Ferry",
            start=16,
            label="etablissement",
            source="postprocess",
        ),
        NamedEntity(
            text="Pierre et Marie Curie",
            start=61,
            label="etablissement",
            source="postprocess",
        ),
        NamedEntity(
            text="Sainte Marie Madeleine",
            start=172,
            label="etablissement",
            source="postprocess",
        ),
    ]

    expected_output = PostProcessOutput(added_entities=expected_entities)

    postpro = PostProcessFromSents(
        input_sentences,
        input_entities,
        checklist=[],
    )
    output = postpro.apply_methods(
        match_against=False,
        match_cities=False,
        match_regex_with_context=False,
        check_compte_bancaire=False,
        change_pro_no_context=False,
        change_pro_with_context=False,
    )

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_check_compte_bancaire():
    input_sentences = [
        Sentence(
            "Son numéro de compte bancaire est 7457568743.",
            use_tokenizer=tokenizer,
        )
    ]
    input_entities = []
    expected_entities = []
    expected_output = PostProcessOutput(
        added_checklist=[
            Check(
                check_type=CheckTypeEnum.missing_bank_account,
                sentences=[SentenceIndexes(start=0, end=45)],
            ),
        ]
    )

    postpro = PostProcessFromSents(
        input_sentences,
        input_entities,
        checklist=[],
    )
    output = postpro.apply_methods(
        match_against=False,
        match_cities=False,
        match_facilities=False,
        match_regex_with_context=False,
        change_pro_no_context=False,
        change_pro_with_context=False,
    )
    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_match_regex_with_context():
    input_sentences = [
        Sentence(
            "Son numéro de travailleur indépendant est 527000000202726354.",
            use_tokenizer=tokenizer,
        ),
        Sentence(
            "Son numéro de tél. est le +33612121212.",
            use_tokenizer=tokenizer,
            start_position=100,
        ),
        Sentence(
            "0101010101",
            use_tokenizer=tokenizer,
            start_position=200,
        ),
        Sentence(
            "Son SIREN est 732829320 et son SIRET est 73282932012345.",
            use_tokenizer=tokenizer,
            start_position=300,
        ),
        Sentence(
            "Son numéro de titre de séjour est 1234567890.",
            use_tokenizer=tokenizer,
            start_position=400,
        ),
        Sentence(
            "Sa clef BdF est 111111ZOUZOU.",
            use_tokenizer=tokenizer,
            start_position=500,
        ),
    ]
    input_entities = []
    expected_entities = [
        NamedEntity(
            text="527000000202726354",
            start=42,
            source="postprocess",
            label="numeroIdentifiant",
        ),
        NamedEntity(
            start=126,
            text="+33612121212",
            source="postprocess",
            label="telephoneFax",
        ),
        NamedEntity(
            text="732829320",
            start=314,
            source="postprocess",
            label="numeroSiretSiren",
        ),
        NamedEntity(
            text="73282932012345",
            start=341,
            source="postprocess",
            label="numeroSiretSiren",
        ),
        NamedEntity(
            text="1234567890",
            start=434,
            source="postprocess",
            label="numeroIdentifiant",
        ),
        NamedEntity(
            text="111111ZOUZOU",
            start=516,
            source="postprocess",
            label="numeroIdentifiant",
        ),
    ]

    expected_output = PostProcessOutput(
        added_entities=expected_entities,
    )

    postpro = PostProcessFromSents(
        input_sentences,
        input_entities,
        checklist=[],
    )
    output = postpro.apply_methods(
        match_against=False,
        match_cities=False,
        match_facilities=False,
        check_compte_bancaire=False,
        change_pro_no_context=False,
        change_pro_with_context=False,
    )

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_overlapping_entities():
    input_sentences = [
        Sentence(
            "Il habite dans un hôtel particulier de Neuilly sur Seine.",
            use_tokenizer=tokenizer,
            start_position=0,
        )
    ]
    input_entities = []

    expected_entities = [
        NamedEntity(
            text="Neuilly sur Seine",
            start=39,
            label="localite",
            source="postprocess",
        )
    ]

    expected_output = PostProcessOutput(added_entities=expected_entities)

    postpro = PostProcessFromSents(
        input_sentences,
        input_entities,
        checklist=[],
    )
    output = postpro.apply_methods(
        match_against=False,
        match_regex_with_context=False,
        check_compte_bancaire=False,
        change_pro_no_context=False,
        change_pro_with_context=False,
    )
    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )
    # TODO: Verifier avec Amaury


def test_change_pro_to_physique_no_context():
    input_sentences = [
        Sentence(
            "Amaury Fouret,",
            use_tokenizer=tokenizer,
            start_position=0,
        )
    ]
    input_sentences[0][:1].set_label("ner", "professionnelMagistratGreffier")
    input_sentences[0][1:2].set_label("ner", "professionnelMagistratGreffier")

    input_entities = [
        NamedEntity(
            text="Amaury",
            start=0,
            label="professionnelMagistratGreffier",
            source="NER model",
        ),
        NamedEntity(
            text="Fouret",
            start=7,
            label="professionnelMagistratGreffier",
            source="NER model",
        ),
    ]

    expected_entities = [
        NamedEntity(
            text="Amaury",
            start=0,
            label="personnePhysique",
            source="postprocess",
        ),
        NamedEntity(
            text="Fouret",
            start=7,
            label="personnePhysique",
            source="postprocess",
        ),
    ]

    expected_output = PostProcessOutput(modified_entities=expected_entities)

    postpro = PostProcessFromSents(
        input_sentences,
        input_entities,
        checklist=[],
    )
    output = postpro.apply_methods(
        match_against=False,
        match_regex_with_context=False,
        match_cities=False,
        change_pro_no_context=True,
        change_pro_with_context=False,
    )

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_match_cities_in_moral():
    input_sentences = []
    input_entities = [
        NamedEntity(
            text="Lyon",
            start=0,
            label="localite",
            source="NER model",
        ),
        NamedEntity(
            text="Nantes",
            start=5,
            label="localite",
            source="NER model",
        ),
        NamedEntity(
            text="Lyon Nantes Maçonnerie",
            start=12,
            label="personneMorale",
            source="NER model",
        ),
        NamedEntity(
            text="Nantes les bons gâteaux",
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
            text="Rennes",
            start=79,
            label="localite",
            source="NER model",
        ),
        NamedEntity(
            text="SCP Nantes-Rennes",
            start=86,
            label="personneMorale",
            source="NER model",
        ),
        NamedEntity(
            text="My little fabric RENNES",
            start=104,
            label="personneMorale",
            source="NER model",
        ),
    ]

    expected_entities = [
        NamedEntity(
            text="Lyon",
            start=0,
            label="localite",
            source="NER model",
        ),
        NamedEntity(
            text="Nantes",
            start=5,
            label="localite",
            source="NER model",
        ),
        NamedEntity(
            text="Lyon",
            start=12,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="Nantes",
            start=17,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="Nantes",
            start=35,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="Le café du Commerce",
            start=59,
            label="personneMorale",
            source="NER model",
        ),
        NamedEntity(
            text="Rennes",
            start=79,
            label="localite",
            source="NER model",
        ),
        NamedEntity(
            text="Nantes",
            start=90,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="Rennes",
            start=97,
            label="localite",
            source="postprocess",
        ),
        NamedEntity(
            text="Rennes",
            start=121,
            label="localite",
            source="postprocess",
        ),
    ]

    expected_output = PostProcessOutput(
        added_entities=[
            NamedEntity(
                text="Lyon",
                start=12,
                label="localite",
                source="postprocess",
            ),
            NamedEntity(
                text="Nantes",
                start=17,
                label="localite",
                source="postprocess",
            ),
            NamedEntity(
                text="Nantes",
                start=35,
                label="localite",
                source="postprocess",
            ),
            NamedEntity(
                text="Nantes",
                start=90,
                label="localite",
                source="postprocess",
            ),
            NamedEntity(
                text="Rennes",
                start=97,
                label="localite",
                source="postprocess",
            ),
            NamedEntity(
                text="Rennes",
                start=121,
                label="localite",
                source="postprocess",
            ),
        ],
        deleted_entities=[
            NamedEntity(
                text="Lyon Nantes Maçonnerie",
                start=12,
                label="personneMorale",
                source="NER model",
            ),
            NamedEntity(
                text="Nantes les bons gâteaux",
                start=35,
                label="personneMorale",
                source="NER model",
            ),
            NamedEntity(
                text="SCP Nantes-Rennes",
                start=86,
                label="personneMorale",
                source="NER model",
            ),
            NamedEntity(
                text="My little fabric RENNES",
                start=104,
                label="personneMorale",
                source="NER model",
            ),
        ],
    )

    postpro = PostProcessFromSents(
        input_sentences,
        input_entities,
        checklist=[],
    )
    output = postpro.match_cities_in_moral(False)

    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )


def test_match_union_delegate():
    """Testing `union delegate` reassignment"""
    first_name = "Paul"
    last_name = "Déchorgnat"
    input_sentences = [
        Sentence(
            f"Représenté par {first_name} {last_name} (Délégué syndical ouvrier)",
            use_tokenizer=tokenizer,
            start_position=0,
        ),
        Sentence(
            f"Représentant : M. {first_name} {last_name} (Défenseur syndical ouvrier)",
            use_tokenizer=tokenizer,
            start_position=100,
        ),
        Sentence(
            f"Représentant : M. {first_name} {last_name} (Délégué syndical ouvrier)",
            use_tokenizer=tokenizer,
            start_position=200,
        ),
        Sentence(
            f"représentée par {first_name} {last_name}, défenseur syndical",
            use_tokenizer=tokenizer,
            start_position=300,
        ),
        Sentence(
            f"représentée par M. {first_name} {last_name} en sa qualité de défenseur syndical",
            use_tokenizer=tokenizer,
            start_position=400,
        ),
    ]

    input_entities = []
    expected_entities = []

    for sentence in input_sentences:
        for token in sentence:
            if token.text in [first_name, last_name]:
                token.set_label("ner", "professionnelMagistratGreffier")
                input_entities.append(
                    NamedEntity(
                        text=token.text,
                        start=token.start_position + sentence.start_position,
                        end=token.end_position + sentence.start_position,
                        label="professionnelMagistratGreffier",
                        source="NER model",
                    )
                )
                expected_entities.append(
                    NamedEntity(
                        text=token.text,
                        start=token.start_position + sentence.start_position,
                        end=token.end_position + sentence.start_position,
                        label="personnePhysique",
                        source="postprocess",
                    )
                )

    expected_output = PostProcessOutput(
        modified_entities=expected_entities,
    )
    postpro = PostProcessFromSents(
        flair_sentences=input_sentences,
        entities=input_entities,
        checklist=[],
    )

    output = postpro.apply_methods(
        match_against=False,
        match_regex_with_context=False,
        match_cities=False,
        match_facilities=False,
        change_pro_no_context=False,
        change_pro_with_context=True,
    )
    assert_equality_between_outputs(
        actual_output=output,
        expected_output=expected_output,
    )
    assert_equality_between_entities(
        expected_entities=expected_entities,
        actual_entities=postpro.entities,
    )
