import itertools
import re
from collections import Counter

import pandas as pd
import pkg_resources
from flair.data import Sentence

from juritools.postprocessing import PostProcess
from juritools.type import CategoryEnum, Check, CheckTypeEnum, NamedEntity, PostProcessOutput, SourceEnum
from juritools.utils import azerty_levenshtein_similarity, deaccent, instantiate_flashtext
from jurispacy_tokenizer import JuriSpacyTokenizer


class PostProcessFromEntities(PostProcess):
    def __init__(
        self,
        entities: list[NamedEntity],
        checklist: list[str],
        tokenizer: JuriSpacyTokenizer,
        metadata: pd.core.frame.DataFrame = None,
    ):
        super().__init__(entities, checklist, metadata)
        self.tokenizer = tokenizer
        self.voies = pd.read_csv(pkg_resources.resource_stream(__name__, "data/NATURE_VOIE.csv"))
        self.keyword_voies = instantiate_flashtext(False)
        self.keyword_voies.add_keywords_from_list(list(set(self.voies.voie.values)))

    def split_entity_multi_toks(
        self,
        categories: list[CategoryEnum] = [CategoryEnum.personnePhysique],
    ) -> PostProcessOutput:
        """
        This method checks if an entity belonging to a specific category has two tokens
        seperate by a space. If so, and following certains conditions, it splits it into
        two entities

        Args:
            categories (list[str], optional): Defaults to ["personnePhysique"].
        """
        output = PostProcessOutput()

        entity_texts = set(entity.text for entity in self.get_entities_for_categories(categories))

        for entity in self.get_entities_for_categories(categories):
            tokens = Sentence(
                entity.text,
                use_tokenizer=self.tokenizer,
            )
            # if more than one token
            # if all token are in other entity texts
            # if tokens are all more than 2 characters
            if (
                (len(tokens) > 1)
                and all(t.text in entity_texts for t in tokens)
                and all(len(t.text) > 2 for t in tokens)
            ):
                label = entity.label
                output.add_deleted_entity(entity)
                self.delete_entity(entity)

                for token in tokens:
                    new_entity = NamedEntity(
                        text=token.text,
                        start=entity.start + token.start_position,
                        label=label,
                        source="postprocess",
                    )
                    self.insert_entity(new_entity)
                    output.add_added_entity(new_entity)

        return output

    def match_address_in_moral(
        self,
    ) -> PostProcessOutput:
        """
        This function checks if an address is present in a 'personnemorale' entity,
        if so, it changes the category 'personnemorale' to 'adresse'
        """
        output = PostProcessOutput()
        match_address = []
        for entity in self.entities_by_category[CategoryEnum.personneMorale]:
            if len(entity.text) > 1 and self.keyword_voies.extract_keywords(entity.text):
                self._modify_entity_category("adresse", entity, match_address)
                output.add_modified_entity(entity)

        return output

    def match_localite_in_adress(
        self,
    ) -> PostProcessOutput:
        """
        This function checks if a localite is present in a 'adresse' entity,
        if so, it changes the part of 'adresse' to 'localite'
        """
        output = PostProcessOutput()
        match_localite = []
        for entity in self.entities_by_category[CategoryEnum.adresse]:
            if len(entity.text) > 1 and re.match(r"^\d{5}\s", entity.text):
                self._modify_entity_category("localite", entity, match_localite)
                output.add_modified_entity(entity)

        return output

    # TODO Rename this here and in `match_address_in_moral` and `match_localite_in_adress`
    def _modify_entity_category(
        self,
        category: str,
        entity: NamedEntity,
        cat_list: list[str],
    ):
        entity.label = CategoryEnum(category)
        entity.source = SourceEnum.post_process
        cat_list.append(entity.text)

    def match_physicomorale(
        self,
    ) -> PostProcessOutput:
        """
        This function checks if natural persons entities are present in the category 'personneMorale',
        if so, it changes the category 'personnemorale' to 'personnephysicomorale'
        """
        output = PostProcessOutput()

        postpro_entities = set()
        natural_persons = set()
        moral_persons = set()
        # Iterate over entities found by statistical models to get them
        for entity in self.entities_by_category[CategoryEnum.personnePhysique]:
            if len(entity.text) > 1:
                natural_persons.add(entity.text)
        for entity in self.entities_by_category[CategoryEnum.personneMorale]:
            if len(entity.text) > 1:
                moral_persons.add(entity.text)
        for natural, moral in itertools.product(natural_persons, moral_persons):
            if natural.lower() in moral.lower():
                postpro_entities.add((natural, moral))
                for ent in self.entities:
                    if (ent.text == moral) and (ent.label == CategoryEnum.personneMorale):
                        ent.label = CategoryEnum.personnePhysicoMorale
                        ent.source = SourceEnum.post_process
                        output.add_modified_entity(ent)

        return output

    def match_natural_persons_in_moral(
        self,
        case_sensitive: bool = True,
    ) -> PostProcessOutput:
        """
        This function matches natural persons and moral entities,
        it deletes the moral entity and add natural persons entities instead
        """
        output = PostProcessOutput()

        keywords = instantiate_flashtext(case_sensitive)

        # iterate over personnePhysique to get keywords to look for in personneMorale
        for i, entity in enumerate(self.entities_by_category[CategoryEnum.personnePhysique]):
            if len(entity.text) > 1:
                keywords.add_keyword(entity.text)
                if len(entity.text.split("-")) > 1:
                    for ent in entity.text.split("-"):
                        keywords.add_keyword(ent)

        # iterate over personneMorale to get personnePhysique inside text
        entities_to_delete = []
        entities_to_add = []
        for entity in self.entities_by_category[CategoryEnum.personneMorale]:
            to_delete = False

            for text, start_match, end_match in keywords.extract_keywords(entity.text, span_info=True):
                entities_to_add.append(
                    NamedEntity(
                        text=text,
                        start=entity.start + start_match,
                        end=entity.start + end_match,
                        label=CategoryEnum.personnePhysique,
                        source="postprocess",
                    )
                )
                to_delete = True
            if to_delete:
                entities_to_delete.append(entity)

        for entity in entities_to_delete:
            output.add_deleted_entity(entity)
            self.delete_entity(entity)
        for entity in entities_to_add:
            output.add_added_entity(entity)
            self.insert_entity(entity)

        return output

    def change_pro_to_physique(
        self,
        use_meta: bool = False,
    ) -> PostProcessOutput:
        """
        This function check if an entity tagged as profesional and appears only one time
        is in fact a natural person that appears multiple times in the decision
        """
        output = PostProcessOutput()
        entity_data = {}
        postpro_entities = set()

        for natural_person_entity in self.entities_by_category[CategoryEnum.personnePhysique]:
            deaccented_lower_text = deaccent(natural_person_entity.text.lower())
            if deaccented_lower_text not in entity_data:
                entity_data[deaccented_lower_text] = {
                    "categories": ["personnePhysique"],
                    "entities": [natural_person_entity],
                }
            else:
                entity_data[deaccented_lower_text]["categories"].append("personnePhysique")
                entity_data[deaccented_lower_text]["entities"].append(natural_person_entity)

        for professional_person_entity in self.get_professional_entities():
            deaccented_lower_text = deaccent(professional_person_entity.text.lower())
            if deaccented_lower_text in entity_data:
                entity_data[deaccented_lower_text]["categories"].append("professionnel")
                entity_data[deaccented_lower_text]["entities"].append(professional_person_entity)

        for deaccented_lower_text in entity_data:
            counter = Counter(entity_data[deaccented_lower_text]["categories"])
            if (counter["personnePhysique"] > 1) and (counter["professionnel"] == 1):
                postpro_entities.add(deaccented_lower_text)
                for entity in entity_data[deaccented_lower_text]["entities"]:
                    # change only if NER predicted otherway
                    if entity.label != CategoryEnum.personnePhysique:
                        entity.label = CategoryEnum.personnePhysique
                        entity.source = SourceEnum.post_process
                        output.add_modified_entity(entity)

        # Use metadata to check if
        # a natural person has been annotated as a profesional person
        if use_meta and self.metadata is not None and len(self.metadata) > 0:
            self.metadata["text_clean"] = self.metadata["text"].apply(deaccent).str.lower()

            df_natural = self.metadata.loc[
                self.metadata["entity"] == "personnePhysique", ["text_clean", "entity"]
            ]  # .drop_duplicates(subset=["text_clean"])
            df_pro = self.metadata.loc[
                self.metadata["entity"].str[:12] == "professionnel",
                ["text_clean", "entity"],
            ]  # .drop_duplicates(subset=["text_clean"])

            intersection_meta = set(df_natural.text_clean.values).intersection(set(df_pro.text_clean.values))
            for nat, label in df_natural.values:
                if nat not in intersection_meta:
                    for ent in self.get_professional_entities():
                        if deaccent(ent.text.lower()) == nat:
                            ent.label = CategoryEnum(label)
                            ent.source = SourceEnum.post_process
                            output.add_modified_entity(ent)
                            postpro_entities.add(nat)
        return output

    def manage_year_in_date(
        self,
    ) -> PostProcessOutput:
        """
        This functions removes the year in dates
        """
        output = PostProcessOutput()
        entities_to_delete = []
        for entity in self.get_civil_date_entities():
            if len(entity.text.split()) == 3 and re.match(r"\d{4}", entity.text.split()[2]) is not None:
                entity.text = entity.text[:-5]
                entity.source = SourceEnum.post_process
                output.add_modified_entity(entity)
            elif entity.text.isdigit() and len(entity.text) == 4:
                entities_to_delete.append(entity)

        for entity_to_delete in entities_to_delete:
            output.add_deleted_entity(entity_to_delete)
            self.delete_entity(entity_to_delete)

        return output

    def check_entities(
        self,
        category: CategoryEnum = CategoryEnum.personnePhysique,
    ) -> PostProcessOutput:
        """
        This function checks if entities from a specific category is present in others
        Inputs:
        - category: the name of the entity class
        """
        output = PostProcessOutput()

        entities_by_text = {}
        # listing entities by entity text
        for entity in self.entities:
            text = deaccent(entity.text.lower())
            entities_by_text[text] = entities_by_text.get(text, []) + [entity]

        # checking number of categories by entity text
        for entity_text in entities_by_text:
            unique_categories = set(e.label for e in entities_by_text[entity_text])
            if (len(unique_categories) > 1) and (category in unique_categories):
                new_checklist = Check(
                    check_type=CheckTypeEnum.different_categories,
                    entities=entities_by_text[entity_text],
                )
                self.checklist.append(new_checklist)
                output.add_added_checklist(new_checklist)

        return output

    def check_len_entities(
        self,
        category: CategoryEnum = CategoryEnum.personnePhysique,
        length: int = 2,
    ) -> PostProcessOutput:
        """
        This function checks if an entity has a minimum of characters
        Inputs:
        - category: the name of the entity class
        - len: minimal length of an entity corresponding to a doubt threshold
        """
        output = PostProcessOutput()
        for entity in self.entities_by_category[category]:
            if len(entity.text) < length:
                new_checklist = Check(
                    check_type="less_than_two_characters",
                    entities=[entity],
                )
                self.checklist.append(new_checklist)
                output.add_added_checklist(new_checklist)

        return output

    def check_similarities(
        self,
        category: CategoryEnum = CategoryEnum.personnePhysique,
        ratio_threshold: int = 0.8,
    ) -> PostProcessOutput:
        """
        This function checks if entities are closed from the Levenshtein distance point of view.
        It aims at identify typos in order to align the letters of the same entities with typos
        Inputs:
        - category: the name of the entity class
        - ratio_threshold: if Levenshtein distance is above this value, raise a doubt
        """
        output = PostProcessOutput()

        similar_entities = []
        check_entities = {}
        c = Counter()
        for entity in self.entities_by_category[category]:
            c[deaccent(entity.text.lower())] += 1
            if deaccent(entity.text.lower()) not in check_entities:
                check_entities[deaccent(entity.text.lower())] = entity
        for ent1, ent2 in itertools.combinations(check_entities, 2):
            similarity = azerty_levenshtein_similarity(check_entities[ent1].text, check_entities[ent2].text)
            if (similarity > ratio_threshold) and (c[ent1] == 1 or c[ent2] == 1):
                similar_entities.append((check_entities[ent1], check_entities[ent2]))

        for ent1, ent2 in similar_entities:
            new_checklist = Check(
                check_type=CheckTypeEnum.similar_writing,
                entities=[ent1, ent2],
            )
            self.checklist.append(new_checklist)
            output.add_added_checklist(new_checklist)

        return output
