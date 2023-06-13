from typing import List, Dict
from juritools.type import NamedEntity
from flashtext import KeywordProcessor
from operator import itemgetter
import string
import random


class Anonymizer:
    def __init__(self, text: str, entities: List[NamedEntity]):
        self.text = text
        self.entities = entities

    def replace_person_entities(self, category: list):

        """
        This function takes a list of physical person categories as input
        and replace every entity from those categories by a random letter
        Inputs:
        - category: list of entity classes
        Example: ['personnephysique']
        """

        entities_to_replace: Dict[str, str] = {}
        capital_letters = string.ascii_uppercase
        check_letters = set()
        index = 1
        keyword_processor = self._instantiate_flashtext(True)
        for entity in self.entities:
            if entity.label in category:
                # Dealing with replacement letters
                if entity.text.lower() not in entities_to_replace.keys():
                    if index <= 26:
                        replacement = f"{random.choice(capital_letters)}."
                        while replacement in check_letters:
                            replacement = f"{random.choice(capital_letters)}."
                    elif index <= 26**2:
                        replacement = (
                            random.choice(capital_letters)
                            + random.choice(capital_letters)
                            + "."
                        )
                        while replacement in check_letters:
                            replacement = (
                                random.choice(capital_letters)
                                + random.choice(capital_letters)
                                + "."
                            )
                    elif index <= 26**3:
                        replacement = (
                            random.choice(capital_letters)
                            + random.choice(capital_letters)
                            + random.choice(capital_letters)
                            + "."
                        )
                        while replacement in check_letters:
                            replacement = (
                                random.choice(capital_letters)
                                + random.choice(capital_letters)
                                + random.choice(capital_letters)
                                + "."
                            )
                    else:
                        return "Too much people to replace!"
                    index += 1
                    check_letters.add(replacement)
                    entities_to_replace[entity.text.lower()] = replacement

                else:
                    replacement = entities_to_replace[entity.text.lower()]

                # Replacing physical person entities by letters
                keyword_processor.add_keyword(entity.text, replacement)

        return keyword_processor.replace_keywords(self.text)

    def replace_other_entities(self, category: list, text=None, replace_by_label=False):

        """
        This function takes a list of address categories as input
        and replace every entity from those categories by '[...]'
        Inputs:
        - category: list of entity classes
        Example: ['adresse']
        - text: if we already have started to replace entities, use pseudonymised text instead of original one
        """

        keyword_processor = self._instantiate_flashtext(True)
        for entity in self.entities:
            if entity.label in category:
                if replace_by_label:
                    keyword_processor.add_keyword(entity.text, f"[{entity.label}]")
                else:
                    keyword_processor.add_keyword(entity.text, "[...]")
        if text:
            return keyword_processor.replace_keywords(text)
        return keyword_processor.replace_keywords(self.text)

    def replace_entities_from_indexes(self, category: list):
        """
        This function takes a list of categories as input and replace every
        entity from those categories using its indexes by '[categoryname]'
        It has to be apply only on original text because it uses indexes of entities
        Inputs:
        - category: list of entity classes
        Example: ['adresse']
        """

        ordered_entities = self._ordered_entities(reverse=True)
        text = self.text
        for entity in ordered_entities:
            if entity.label in category:
                text = f"{text[:entity.start]}[{entity.label}]{text[entity.end:]}"
        return text

    def _ordered_entities(self, reverse=False):
        """
        This function put in order entities after using multiple postprocessing methods
        Inputs:
        - reverse: if true, get order entities in reverse order
        """
        if reverse:
            return sorted(self.entities, key=itemgetter("start"), reverse=True)
        return sorted(self.entities, key=itemgetter("start"))

    @staticmethod
    def _instantiate_flashtext(case_sensitive: bool):
        non_word_boundary_list = [
            "é",
            "è",
            "ê",
            "ù",
            "û",
            "î",
            "ï",
            "ö",
            "ô",
            "É",
            "È",
            "Ê",
            "Î",
            "Ï",
            "Ö",
            "Ô",
            "Ú",
            "Û",
            "Ù",
            "Ü",
            "-",
        ]
        keyword_processor = KeywordProcessor(case_sensitive)
        for non_word in non_word_boundary_list:
            keyword_processor.add_non_word_boundary(non_word)
        return keyword_processor
