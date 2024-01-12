from jurispacy_tokenizer import JuriSpacyTokenizer
from flair.models import SequenceTagger
from juritools.type import Decision, CategoryEnum
from juritools.postprocessing import PostProcessFromEntities, PostProcessFromSents, PostProcessFromText
from juritools.preprocess import PreProcess
from juritools.predict import JuriTagger


def ner(
    decision: Decision,
    tokenizer: JuriSpacyTokenizer,
    model: SequenceTagger,
):
    """Returns the predictions of the NER Model

    Args:
        decision (Decision): the decision to analyze
        tokenizer (JuriSpacyTokenizer): tokenizer to create tokens and sentences
        model (SequenceTagger): a trained NER model

    Raises:
        HTTPException: _description_

    Returns:
        _type_: _description_
    """

    response = {}

    # preprocessing metadata
    preprocess = PreProcess(
        decision=decision,
        tokenizer=tokenizer,
        model=model,
    )
    metadata = preprocess.metadata
    text = preprocess.text

    # SequenceTagger predictions
    juritag = JuriTagger(tokenizer, model)
    juritag.predict(text, verbose=False)
    prediction_jsonified = juritag.get_entity_json_from_flair_sentences()

    # Postprocessing on court decision text
    postpro_text = PostProcessFromText(
        text=text,
        entities=prediction_jsonified,
        checklist=[],
        metadata=metadata,
    )
    # Postprocessing on text
    postpro_text.manage_quote()
    postpro_text.manage_le()
    # Postprocessing on entities
    postpro_entities = PostProcessFromEntities(
        entities=postpro_text.entities,
        checklist=[],
        metadata=metadata,
        tokenizer=tokenizer,
    )
    # postpro_entities.match_physicomorale()
    postpro_entities.match_address_in_moral()
    if decision.categories and CategoryEnum.personneMorale not in decision.categories:
        postpro_entities.match_natural_persons_in_moral(False)
    postpro_entities.change_pro_to_physique()
    # postpro_entities.manage_natural_persons()
    postpro_entities.manage_year_in_date()
    postpro_entities.check_len_entities()  # personnephysique by default
    postpro_entities.check_entities()  # personnephysique by default
    postpro_entities.match_localite_in_adress()
    postpro_entities.split_entity_multi_toks()  # personnePhysique by default
    postpro_entities.check_similarities()  # personnePhysique by default

    # Go back on postprocessing on text
    postpro_text.entities = postpro_entities.entities
    postpro_text.checklist = postpro_entities.checklist
    postpro_text.match_from_category(
        [
            CategoryEnum.personnePhysique,
            CategoryEnum.professionnelAvocat,
            CategoryEnum.professionnelMagistratGreffier,
            CategoryEnum.dateDeces,
        ]
    )
    postpro_text.match_regex()
    postpro_text.juvenile_facility_entities()
    postpro_text.match_name_in_website()
    try:
        if metadata is not None:
            if decision.sourceName == "jurinet":
                postpro_text.match_metadata_jurinet()
            elif decision.sourceName == "jurica":
                postpro_text.match_metadata_jurica()
    except Exception:
        pass
    postpro_text.check_cadastre()

    # Postprocessing on flair sentences
    postpro_sents = PostProcessFromSents(
        flair_sentences=juritag.flair_sentences,
        entities=postpro_text.entities,
        checklist=postpro_text.checklist,
        metadata=metadata,
    )
    postpro_sents.apply_methods(change_pro_no_context=False)

    if decision.categories and (CategoryEnum.personneMorale not in decision.categories):
        postpro_sents.match_cities_in_moral(False)

    entities = postpro_sents.ordered_entities()

    # Handle categories parameter
    if isinstance(decision.categories, list):
        filter_entities = []
        for category in decision.categories:
            filter_entities.extend(postpro_sents.entities_by_category[category])
        response["entities"] = filter_entities
    else:
        response["entities"] = entities
    response["checklist"] = [c.get_message() for c in postpro_sents.checklist]

    return response
