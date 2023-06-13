from juritools.type import NamedEntity
from juritools.postprocessing import PostProcess
from juritools.utils import deaccent, instantiate_flashtext
from juritools.utils.regular_expressions import PRO_TO_PHYSIQUE_RE
from typing import List
from flair.data import Sentence, Span
import pandas as pd
import pkg_resources
import re


class PostProcessFromSents(PostProcess):
    def __init__(
        self,
        flair_sentences: List[Sentence],
        entities: List[NamedEntity],
        manual_checklist: List[str],
        metadata: pd.core.frame.DataFrame = None,
    ):
        super().__init__(entities, manual_checklist, metadata)
        self.sentences = flair_sentences
        self.cities = pd.read_csv(
            pkg_resources.resource_stream(__name__, "data/communes.csv")
        )
        self.cities.nom_commune_complet = self.cities.nom_commune_complet.str.replace(
            "-", " "
        )
        self.keyword_cities = instantiate_flashtext(True)
        self.keyword_cities.add_keywords_from_list(
            list(set(self.cities.nom_commune_complet.apply(deaccent).values))
        )
        self.keyword_cities.add_keywords_from_list(
            list(
                set(self.cities.nom_commune_complet.str.upper().apply(deaccent).values)
            )
        )
        self.keywords_no_cities = instantiate_flashtext(False)
        # List of keywords we do not want in the same sentence of a city
        self.keywords_no_cities.add_keywords_from_list(
            [
                "tribunal",
                "SCI",
                "SCP",
                "cour d'appel",
                "arrêt attaqué",
                "barreau",
                "registre",
                "conseil de prud'hommes",
                "palais",
            ]
        )
        self.facilities = pd.read_csv(
            pkg_resources.resource_stream(__name__, "data/etablissements.txt")
        )
        self.keyword_facilities = instantiate_flashtext(False)
        self.keyword_facilities.add_keywords_from_list(
            list(self.facilities.etablissement.values)
        )
        self.keyword_compte_bancaire = instantiate_flashtext(False)
        self.keyword_compte_bancaire.add_keyword("compte bancaire")

        self.keyword_siren_siret = instantiate_flashtext(False)
        self.keyword_siren_siret.add_keywords_from_list(["siren", "siret", "RCS"])

        self.keyword_phone = instantiate_flashtext(False)
        self.keyword_phone.add_keywords_from_list(
            ["portable", "tel", "tel.", "telephone", "mobile"]
        )

    def match_against_case(self, sent_string: str, index_sentence: int):
        match_against = []
        if sent_string.lower() == "c/":
            index_c = index_sentence
            if index_c > 1:
                against_sents = self.sentences[index_c - 2 : index_c + 3]
            else:
                against_sents = self.sentences[index_c - 1 : index_c + 2]
            for sent in against_sents:
                for span in sent.get_spans("ner"):
                    if "professionnel" in span.tag or (
                        "adresse" in span.tag and len(span) < 3
                    ):
                        span.set_label("ner", "personnePhysique")
                        for entity in self.entities:
                            if entity.start == span.start_position:
                                entity.label = span.tag
                                match_against.append(span.text)

        return match_against

    def _find_postal_code(
        self, sent_string: str, idx_start_sentence: int, match_cities
    ):
        postal_code_regex = r"(?<=\(|\s)\d{5}(?=\)|\s|\.|,)"
        for match in re.finditer(postal_code_regex, sent_string):
            start_new_entity = idx_start_sentence + match.start()
            end_new_entity = idx_start_sentence + match.end()
            if self.check_overlap_entities(start_new_entity, end_new_entity):
                self.entities.append(
                    NamedEntity(
                        text=match.group(),
                        start=start_new_entity,
                        end=end_new_entity,
                        label="localite",
                        source="postprocess",
                    )
                )
                match_cities.append(match.group())
        return match_cities

    def match_cities(
        self, sentence: Sentence, sent_string: str, idx_start_sentence: int
    ):
        """
        This function matches cities in the court decision using a CSV file of french cities
        """
        match_cities = []

        # Search if a city is in the sentence
        cities_found = self.keyword_cities.extract_keywords(
            deaccent(sent_string.replace("-", " ")), span_info=True
        )
        # Search if a specific keyword that discard the sentence is in it
        no_cities_found = self.keywords_no_cities.extract_keywords(sent_string)
        if not no_cities_found and cities_found:
            for keyword, start_keyword, end_keyword in cities_found:
                if deaccent(sent_string).replace("-", " ").startswith(keyword):
                    continue

                start_new_entity = idx_start_sentence + start_keyword
                end_new_entity = idx_start_sentence + end_keyword

                if self.check_overlap_entities(start_new_entity, end_new_entity):
                    match_cities = self._find_postal_code(
                        sent_string, idx_start_sentence, match_cities
                    )
                    self.entities.append(
                        NamedEntity(
                            text=sent_string[start_keyword:end_keyword],
                            start=start_new_entity,
                            end=end_new_entity,
                            label="localite",
                            source="postprocess",
                        )
                    )
                    match_cities.append(keyword)

        return match_cities

    def match_cities_in_moral(self, case_sensitive: bool = True):
        """
        This function matches cities and moral entities,
        it deletes the moral entity and add city entities instead
        """

        keywords = instantiate_flashtext(case_sensitive)
        postpro_entities = set()
        moral_persons = []
        index_to_delete = []
        # Iterate over entities found by statistical models to get them
        for i, entity in enumerate(self.entities):
            if (
                entity.label == "localite"
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

    def match_facilities(
        self, sentence: Sentence, sent_string: str, idx_start_sentence: int
    ):
        """
        This function matches the name of different types of
        facilities like airports, schools, churchs and so on
        """
        match_facilities = []

        if facilities_found := self.keyword_facilities.extract_keywords(
            deaccent(sent_string), span_info=True
        ):
            for i, (_, _, end_keyword) in enumerate(facilities_found):
                start_entity = None
                end_entity = None
                if len(facilities_found) > 1 and i < len(facilities_found) - 1:
                    start_next_match = idx_start_sentence + facilities_found[i + 1][1]
                else:
                    start_next_match = None
                possible_entity = next(
                    (
                        sentence[i_tok : i_tok + 5]
                        for i_tok, token in enumerate(sentence)
                        if (
                            (token.start_position > idx_start_sentence + end_keyword)
                            and (token.text.istitle() or token.text.isupper())
                            and token.text not in ["Madame", "Monsieur", "M.", "Mme"]
                        )
                    ),
                    [],
                )

                for i_tok, token in enumerate(possible_entity[::-1]):
                    if (
                        start_next_match is not None
                        and token.start_position >= start_next_match
                    ):
                        continue
                    if (
                        token.text.istitle() or token.text.isupper()
                    ) and token.text not in ["Madame", "Monsieur", "M.", "Mme"]:
                        if i_tok == 0:
                            span_entity = Span(possible_entity)
                        else:
                            span_entity = Span(possible_entity[:-i_tok])
                        end_entity = token.start_position + len(token.text)
                        start_entity = possible_entity[0].start_position
                        break

                if (
                    start_entity
                    and end_entity
                    and self.check_overlap_entities(start_entity, end_entity)
                ):
                    self.entities.append(
                        NamedEntity(
                            text=span_entity.text.strip(),
                            start=start_entity,
                            end=end_entity,
                            label="etablissement",
                            source="postprocess",
                        )
                    )
                    match_facilities.append(span_entity.text.strip())

        return match_facilities

    def match_siren_and_siret(self, sent_string: str, idx_start_sentence: int):
        """This function matches siren and siret numbers"""
        match_siren_siret = []
        if siren_siret_found := self.keyword_siren_siret.extract_keywords(sent_string):
            siren_siret_regex = r"(\b\d{3}[ \.]?\d{3}[ \.]?\d{3}[ \.]?\d{3}[ \.]?\d{2}\b)|(?:(?<=\b)|(?<=A|B))(\d{3}[ \.]?\d{3}[ \.]?\d{3}\b)"

            for match in re.finditer(siren_siret_regex, sent_string):
                start_new_entity = idx_start_sentence + match.start()
                end_new_entity = idx_start_sentence + match.end()
                if self.check_overlap_entities(start_new_entity, end_new_entity):
                    self.entities.append(
                        NamedEntity(
                            text=match.group(),
                            start=start_new_entity,
                            end=end_new_entity,
                            label="numeroSiretSiren",
                            source="postprocess",
                        )
                    )
                    match_siren_siret.append(match.group())

        return match_siren_siret

    def match_phone_numbers(self, sent_string: str, idx_start_sentence: int):
        """This function matches phone numbers"""

        match_phone_number = []
        if phone_found := self.keyword_phone.extract_keywords(deaccent(sent_string)):
            phone_number_regex = r"(?:(?:00|\+)33|0)\s?[\d](?:[\s.-]*\d{2}){4}\b"

            for match in re.finditer(phone_number_regex, sent_string):
                start_new_entity = idx_start_sentence + match.start()
                end_new_entity = idx_start_sentence + match.end()
                if self.check_overlap_entities(start_new_entity, end_new_entity):
                    self.entities.append(
                        NamedEntity(
                            text=match.group(),
                            start=start_new_entity,
                            end=end_new_entity,
                            label="telephoneFax",
                            source="postprocess",
                        )
                    )
                    match_phone_number.append(match.group())

        return match_phone_number

    def change_pro_to_physique_no_context(
        self, sentence: Sentence, idx_start_sentence: int, idx_end_sentence: int
    ):
        """
        This function change the category of the entity if there is
        only this entity in the sentence, no context
        """
        # Assign label to each token
        # Ugly and temporary
        for entity in sentence.get_spans("ner"):
            prefix = "B-"
            for token in entity:
                token.set_label("ner", prefix + entity.tag, entity.score)
                prefix = "I-"

        changed_entities = []
        for token in sentence:
            if token.text.isalpha() and "professionnel" not in token.tag:
                break
        else:
            for entity in self.entities:
                if idx_start_sentence <= entity.start <= idx_end_sentence:
                    entity.label = "personnePhysique"
                    entity.source = "postprocess"
                    changed_entities.append(entity.text)

        return changed_entities

    def check_compte_bancaire(self, sentence: Sentence, sent_string: str):
        """
        This function checks if we miss entities from comptebancaire category
        """
        check_cb = []
        start_sent = sentence[0].start_position
        end_sent = sentence[-1].start_position + len(sentence[-1].text)
        cb_found = self.keyword_compte_bancaire.extract_keywords(
            sent_string, span_info=True
        )
        if cb_found and re.search(r"\d{5,}", sent_string):
            add_check = not any(
                start_sent <= entity.start <= end_sent
                and entity.label == "compteBancaire"
                for entity in self.entities
            )

            if add_check:
                self.manual_checklist.append(
                    "Il semblerait qu'un ou plusieurs numéros de comptes bancaires n'aient pas été repérées"
                )
                check_cb.append(sent_string)

        return check_cb

    def change_pro_to_physique_with_context(
        self,
        sentence: Sentence,
        regular_expressions: list = PRO_TO_PHYSIQUE_RE.values(),
        context_size: int = 60,
    ):
        """Method that changes `professionnel` entities to `personnePhysique` if a regular expression is met in its context

        Args:
            sentence (Sentence): sentence that should be scanned
            regular_expressions (list[str], optional): list of uncompiled regular expressions.
                Defaults to list(PRO_TO_PHYSIQUE_RE.values()).
            context_size (int, optional): size of the context to take into account.
                Defaults to 60.

        Returns:
            list[NamedEntity]: list of changed named entities
        """

        regular_expressions = re.compile(rf"{'|'.join(regular_expressions)}")

        new_entities = []

        for entity in self.entities:
            entity_end = entity.start + len(entity.text)

            clean_context = deaccent(sentence.to_original_text())[
                entity_end : entity_end + context_size
            ].lower()

            if (
                (entity.start >= sentence.start_position)
                and (entity_end <= sentence.end_position)
                and ("professionnel" in entity.label)
                # Union delegates
                and (regular_expressions.search(clean_context))
            ):

                entity.label = "personnePhysique"
                entity.source = "postprocess"

                new_entities.append(entity)

        return [e.text for e in new_entities]

    def apply_methods(
        self,
        match_against=True,
        match_cities=True,
        match_facilities=True,
        match_siren_and_siret=True,
        match_phone_numbers=True,
        check_compte_bancaire=True,
        change_pro_no_context=True,
        change_pro_with_context=True,
    ):
        """
        This function apply methods on the whole document
        """
        detected_entities = []
        for i, sent in enumerate(self.sentences):
            # Get position of the first word of the sentence in the whole document
            if not sent:
                continue
            sent_string = sent.to_plain_string()
            start_sentence = sent[0].start_position
            if sent.start_position and sent.start_position > start_sentence:
                start_sentence = sent.start_position
            end_sentence = sent[-1].start_position + len(sent[-1].text)
            if match_against:
                detected_entities.extend(self.match_against_case(sent_string, i))
            if match_siren_and_siret:
                detected_entities.extend(
                    self.match_siren_and_siret(sent_string, start_sentence)
                )
            if match_phone_numbers:
                detected_entities.extend(
                    self.match_phone_numbers(sent_string, start_sentence)
                )
            if check_compte_bancaire:
                detected_entities.extend(self.check_compte_bancaire(sent, sent_string))
            if match_cities:
                detected_entities.extend(
                    self.match_cities(sent, sent_string, start_sentence)
                )
            if match_facilities:
                detected_entities.extend(
                    self.match_facilities(sent, sent_string, start_sentence)
                )
            if change_pro_no_context:
                detected_entities.extend(
                    self.change_pro_to_physique_no_context(
                        sent, start_sentence, end_sentence
                    )
                )
            if change_pro_with_context:
                detected_entities.extend(self.change_pro_to_physique_with_context(sent))

        return detected_entities
