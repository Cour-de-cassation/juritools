from juritools.type import NamedEntity
from juritools.postprocessing import PostProcess
from collections import Counter, defaultdict
from juritools.utils import deaccent, instantiate_flashtext
from flair.data import Sentence, Token
import itertools
from typing import List
import pandas as pd
import re
import pkg_resources


class PostProcessFromEntities(PostProcess):
    def __init__(
        self,
        entities: List[NamedEntity],
        manual_checklist: List[str],
        tokenizer,
        metadata: pd.core.frame.DataFrame = None,
    ):
        super().__init__(entities, manual_checklist, metadata)
        self.tokenizer = tokenizer
        self.voies = pd.read_csv(
            pkg_resources.resource_stream(__name__, "data/NATURE_VOIE.csv")
        )
        self.keyword_voies = instantiate_flashtext(False)
        self.keyword_voies.add_keywords_from_list(list(set(self.voies.voie.values)))

    def split_entity_multi_toks(self, categories: List[str] = None):
        """
        This method checks if an entity belonging to a specific category has two tokens
        seperate by a space. If so, and following certains conditions, it splits it into
        two entities

        Args:
            categories (List[str], optional): Defaults to ["personnePhysique"].
        """
        if categories is None:
            categories = ["personnePhysique"]
        index_to_delete = []
        ents = [
            (i, entity)
            for i, entity in enumerate(self.entities)
            if entity.label in categories
            and len(Sentence(entity.text, use_tokenizer=self.tokenizer)) > 1
        ]
        ents_text = [
            entity.text for entity in self.entities if entity.label in categories
        ]
        for i, entity in ents:
            entity_sent = Sentence(entity.text, use_tokenizer=self.tokenizer)
            for token in entity_sent:
                if token.text not in ents_text or len(token.text) < 3:
                    break
            else:
                index_to_delete.append(i)
                for token in entity_sent:
                    self.entities.append(
                        NamedEntity(
                            text=token.text,
                            start=entity.start + token.start_position,
                            end=entity.start + token.end_position,
                            label=entity.label,
                            source="postprocess",
                        )
                    )

        sorted_index_to_delete = sorted(index_to_delete, reverse=True)
        for index in sorted_index_to_delete:
            del self.entities[index]

    def match_address_in_moral(self):
        """
        This function checks if an address is present in a 'personnemorale' entity,
        if so, it changes the category 'personnemorale' to 'adresse'
        """
        match_address = []
        for entity in self.entities:
            if (
                entity.label.lower() == "personnemorale"
                and len(entity.text) > 1
                and self.keyword_voies.extract_keywords(entity.text)
            ):
                self._modify_entity_category("adresse", entity, match_address)

        return match_address

    def match_localite_in_adress(self):
        """
        This function checks if a localite is present in a 'adresse' entity,
        if so, it changes the part of 'adresse' to 'localite'
        """
        match_localite = []
        for entity in self.entities:
            if (
                entity.label.lower() == "adresse"
                and len(entity.text) > 1
                and re.match(r"^\d{5}\s", entity.text)
            ):
                self._modify_entity_category("localite", entity, match_localite)

        return match_localite

    # TODO Rename this here and in `match_address_in_moral` and `match_localite_in_adress`
    def _modify_entity_category(
        self, category: str, entity: NamedEntity, cat_list: List
    ):
        entity.label = category
        entity.source = "postprocess"
        cat_list.append(entity.text)

    def match_physicomorale(self):

        """
        This function checks if natural persons entities are present in the category 'personnemorale',
        if so, it changes the category 'personnemorale' to 'personnephysicomorale'
        """

        postpro_entities = set()
        natural_persons = set()
        moral_persons = set()
        # Iterate over entities found by statistical models to get them
        for entity in self.entities:
            if entity.label.lower() == "personnephysique" and len(entity.text) > 1:
                natural_persons.add(entity.text)
            elif entity.label.lower() == "personnemorale" and len(entity.text) > 1:
                moral_persons.add(entity.text)
        for natural, moral in itertools.product(natural_persons, moral_persons):
            if natural.lower() in moral.lower():
                postpro_entities.add((natural, moral))
                for ent in self.entities:
                    if (ent.text == moral) and (ent.label.lower() == "personnemorale"):
                        ent.label = "personnephysicomorale"
                        ent.source = "postprocess"

        return postpro_entities or "No match!"

    def match_natural_persons_in_moral(self, case_sensitive: bool = True):
        """
        This function matches natural persons and moral entities,
        it deletes the moral entity and add natural persons entities instead
        """

        keywords = instantiate_flashtext(case_sensitive)
        postpro_entities = set()
        moral_persons = []
        index_to_delete = []
        # Iterate over entities found by statistical models to get them
        for i, entity in enumerate(self.entities):
            if (
                entity.label.lower() == "personnephysique"
                and len(entity.text) > 1
                and entity.text not in keywords.get_all_keywords().keys()
            ):
                keywords.add_keyword(entity.text, (entity.text, entity.label))
            elif entity.label.lower() == "personnemorale" and len(entity.text) > 1:
                moral_persons.append((entity, i))

        for entity, index in moral_persons:
            for i, (match, start, end) in enumerate(
                keywords.extract_keywords(entity.text, span_info=True)
            ):
                if i == 0:
                    index_to_delete.append(index)
                self.entities.append(
                    NamedEntity(
                        text=match[0],
                        start=entity.start + start,
                        end=entity.start + end,
                        label=match[1],
                        source="postprocess",
                    )
                )
                postpro_entities.add(match[0])

        sorted_index_to_delete = sorted(index_to_delete, reverse=True)
        for index in sorted_index_to_delete:
            del self.entities[index]

        return postpro_entities

    def change_pro_to_physique(self, use_meta: bool = False):

        """
        This function check if an entity tagged as profesional and appears only one time is in fact
        a natural person that appears multiple times in the decision
        """

        postpro_entities = set()
        natural_persons = []
        natural_categories = []
        profesional_persons = []
        # Iterate overt entities found by statistical models to get them
        for entity in self.entities:
            if "personnephysique" in entity.label.lower() and len(entity.text) > 1:
                natural_persons.append(entity.text.lower())
                natural_categories.append(deaccent(entity.label))
            elif "professionnel" in entity.label.lower() and len(entity.text) > 1:
                profesional_persons.append(deaccent(entity.text.lower()))

        if intersection := set(natural_persons).intersection(profesional_persons):
            c_pro = Counter(profesional_persons)
            c_natural = Counter(natural_persons)
            for intersect in intersection:
                if c_pro[intersect] == 1 and c_natural[intersect] > 1:
                    postpro_entities.add(intersect)
                    for ent in self.entities:
                        if (deaccent(ent.text.lower()) == intersect) and (
                            "professionnel" in ent.label.lower()
                        ):
                            ent.label = natural_categories[
                                natural_persons.index(intersect)
                            ]
                            ent.source = "postprocess"

        # Use metadata to check if a natural person has been annotated as a profesional person
        if use_meta and self.metadata is not None and len(self.metadata) > 0:
            self.metadata["text_clean"] = (
                self.metadata["text"].apply(deaccent).str.lower()
            )
            df_natural = self.metadata[["text_clean", "entity"]].query(
                "entity == 'personnephysique'"
            )
            df_pro = self.metadata[["text_clean", "entity"]].query(
                "entity in ['professionnelavocat', 'professionnelmagistratgreffier']"
            )
            intersection_meta = set(df_natural.text_clean.values).intersection(
                set(df_pro.text_clean.values)
            )
            for nat, label in df_natural.values:
                if nat not in intersection_meta:
                    for ent in self.entities:
                        if (deaccent(ent.text.lower()) == nat) and (
                            "professionnel" in ent.label.lower()
                        ):
                            ent.label = label
                            ent.source = "postprocess"
                            postpro_entities.add(nat)

        return postpro_entities

    def manage_natural_persons(self):
        """
        DEPRECIATED
        This function find if a same entity is detected one time as a firstname and multiple times as a surname (and vice versa) to
        modify the category of the first to avoid raising manual check
        """

        postpro_entities = set()
        firstnames = []
        lastnames = []
        # Iterate overt entities found by statistical models to get them
        for entity in self.entities:
            if (
                "personnephysiqueprenom" in entity.label.lower()
                and len(entity.text) > 1
            ):
                firstnames.append(entity.text.lower())
            elif "personnephysiquenom" in entity.label.lower() and len(entity.text) > 1:
                lastnames.append(entity.text.lower())

        # Check if there is any intersection between those two lists
        intersection = set(firstnames).intersection(lastnames)
        if not intersection:
            return "No changes"

        c_firstnames = Counter(firstnames)
        c_lastnames = Counter(lastnames)
        for intersect in intersection:
            if c_firstnames[intersect] == 1 and c_lastnames[intersect] > 1:
                postpro_entities.add(intersect)
                for ent in self.entities:
                    if (
                        ent.text.lower() == intersect
                        and ent.label.lower() == "personnephysiqueprenom"
                    ):
                        ent.label = "personnephysiquenom"
                        ent.source = "postprocess"
            elif c_lastnames[intersect] == 1 and c_firstnames[intersect] > 1:
                postpro_entities.add(intersect)
                for ent in self.entities:
                    if (
                        ent.text.lower() == intersect
                        and ent.label.lower() == "personnephysiquenom"
                    ):
                        ent.label = "personnephysiqueprenom"
                        ent.source = "postprocess"

        return postpro_entities

    def manage_year_in_date(self):
        """
        This functions removes the year in dates
        """
        match_date = []
        index_to_delete = []
        for index, entity in enumerate(self.entities):
            if (
                "date" in entity.label
                and len(entity.text.split()) == 3
                and re.match(r"\d{4}", entity.text.split()[2]) is not None
            ):
                entity.text = entity.text[:-5]
                entity.end -= 5
                match_date.append(entity.text)
            elif (
                "date" in entity.label
                and entity.text.isdigit()
                and len(entity.text) == 4
            ):
                index_to_delete.append(index)
                match_date.append(entity.text)

        if index_to_delete:
            sorted_index_to_delete = sorted(index_to_delete, reverse=True)
            for index in sorted_index_to_delete:
                del self.entities[index]

        return match_date

    def check_entities(self, category: str = "personnephysique"):
        """
        This function checks if entities from a specific category is present in another one
        Inputs:
        - category: the name of the entity class
        """

        check_class = set()
        other_classes = defaultdict(list)
        for entity in self.entities:
            if entity.label.lower() == category and len(entity.text) > 1:
                check_class.add(entity.text)
            elif (len(entity.text) > 1) and (
                not (
                    ("personnephysique" in category.lower())
                    and (entity.label.lower() == "personnephysicomorale")
                )
            ):
                other_classes[entity.text].append(entity.label)

        if multi_class_entities := [
            (specific_entity, category, other_classes[specific_entity])
            for specific_entity in check_class
            if specific_entity in other_classes
        ]:
            self.manual_check = True
            for entity in multi_class_entities:
                self.manual_checklist.append(
                    f"L'annotation '{entity[0]}' est de catégorie '{entity[1]}' mais on retrouve la même annotation dans une autre catégorie '{entity[2][0]}'. Les annotations sont-elles réellement de catégories différentes ?"
                )
            return multi_class_entities
        else:
            return "No same entity in two different categories found!"

    def check_len_entities(self, category: str = "personnephysique", length: int = 2):

        """
        This function checks if an entity has a minimum of characters
        Inputs:
        - category: the name of the entity class
        - len: minimal length of an entity corresponding to a doubt threshold
        """

        check_entities = [
            entity.text.lower()
            for entity in self.entities
            if entity.label.lower() == category
        ]

        if small_entities := [
            entity for entity in check_entities if len(entity) < length
        ]:
            self.manual_check = True
            for entity in small_entities:
                self.manual_checklist.append(
                    f"{entity} : cette annotation fait moins de 2 caractères. Est-ce normal ?"
                )


"""
    def check_similarities(
        self, category: str = "personnephysique", distance_threshold: int = 2
    ):
        '''
        This function checks if entities are closed from the Levenshtein distance point of view.
        It aims at identify typos in order to align the letters of the same entities with typos
        Inputs:
        - category: the name of the entity class
        - distance_threshold: if Levenshtein distance is below this value and greater than zero, raise a doubt
        '''

        similar_entities = []
        check_entities = [
            entity.text.lower()
            for entity in self.entities
            if entity.label.lower() == category
        ]
        c = Counter(check_entities)
        for entity_to_check in set(check_entities):
            for entity in check_entities:
                similarity = Levenshtein.distance(str(entity_to_check), str(entity))
                if (0 < similarity < distance_threshold) and (c[entity] == 1):
                    similar_entities.append((entity_to_check, entity))

        if similar_entities:
            self.manual_check = True
            detected_entities = set()
            for entity in similar_entities:
                if entity[0] not in detected_entities:
                    self.manual_checklist.append(
                        f"'{entity[0]}' est similaire à '{entity[1]}'. Est-ce une erreur de saisie ?"
                    )
                    detected_entities.add(entity[0])
                    detected_entities.add(entity[1])
        else:
            return "No similar entities found!"
"""
