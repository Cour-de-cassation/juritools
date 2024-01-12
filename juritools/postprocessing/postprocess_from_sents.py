import re

import pandas as pd
import pkg_resources
from flair.data import Sentence, Span

from juritools.postprocessing import PostProcess
from juritools.type import CategoryEnum, Check, NamedEntity, PostProcessOutput, SentenceIndexes, SourceEnum
from juritools.utils import deaccent, instantiate_flashtext
from juritools.utils.regular_expressions import PRO_TO_PHYSIQUE_RE


class PostProcessFromSents(PostProcess):
    def __init__(
        self,
        flair_sentences: list[Sentence],
        entities: list[NamedEntity],
        checklist: list[str],
        metadata: pd.core.frame.DataFrame = None,
    ):
        super().__init__(entities, checklist, metadata)
        self.sentences = flair_sentences
        self.cities = pd.read_csv(pkg_resources.resource_stream(__name__, "data/communes.csv"))
        self.cities.nom_commune_complet = self.cities.nom_commune_complet.str.replace("-", " ")
        self.keyword_cities = instantiate_flashtext(True)
        self.keyword_cities.add_keywords_from_list(list(set(self.cities.nom_commune_complet.apply(deaccent).values)))
        self.keyword_cities.add_keywords_from_list(
            list(set(self.cities.nom_commune_complet.str.upper().apply(deaccent).values))
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
        self.facilities = pd.read_csv(pkg_resources.resource_stream(__name__, "data/etablissements.txt"))
        self.keyword_facilities = instantiate_flashtext(False)
        self.keyword_facilities.add_keywords_from_list(list(self.facilities.etablissement.values))
        self.keyword_compte_bancaire = instantiate_flashtext(False)
        self.keyword_compte_bancaire.add_keywords_from_list(
            ["compte bancaire", "livret A", "compte courant", "compte de depot"]
        )

        self.keyword_find_context = instantiate_flashtext(False)
        self.keyword_find_context.add_keywords_from_dict(
            {
                "ti": ["travailleur independant"],
                "phone": ["portable", "tel", "tel.", "telephone", "mobile"],
                "cni": ["carte d'identite", "carte nationale d'identite", "cni"],
                "sejour": ["carte de sejour", "titre de sejour", "visa long sejour", "AGDREF"],
                "clef_bdf": ["clef Banque de France", "clef BDF", "clé Banque de France", "clé BDF"],
                "siren_siret": ["siren", "siret", "RCS"],
            }
        )

    def match_against_case(
        self,
        sent_string: str,
        index_sentence: int,
    ) -> PostProcessOutput:
        output = PostProcessOutput()

        if sent_string.lower() == "c/":
            index_c = index_sentence
            if index_c > 1:
                against_sents = self.sentences[index_c - 2 : index_c + 3]
            else:
                against_sents = self.sentences[index_c - 1 : index_c + 2]
            for sent in against_sents:
                for span in sent.get_spans("ner"):
                    if "professionnel" in span.tag or ("adresse" in span.tag and len(span) < 3):
                        span.set_label("ner", "personnePhysique")
                        for entity in self.entities:
                            if entity.start == span.start_position:
                                entity.label = CategoryEnum.personnePhysique
                                entity.source = SourceEnum.post_process
                                output.add_modified_entity(entity)

                            if entity.start > sent.end_position:
                                break

        return output

    def _find_postal_code(
        self,
        sent_string: str,
        idx_start_sentence: int,
    ) -> PostProcessOutput:
        output = PostProcessOutput()

        postal_code_regex = r"(?<=\(|\s)\d{5}(?=\)|\s|\.|,)"

        for match in re.finditer(postal_code_regex, sent_string):
            start_new_entity = idx_start_sentence + match.start()
            end_new_entity = idx_start_sentence + match.end()

            if self.check_overlap_entities_from_index(start_new_entity, end_new_entity):
                new_entity = NamedEntity(
                    text=match.group(),
                    start=start_new_entity,
                    end=end_new_entity,
                    label="localite",
                    source="postprocess",
                )
                self.insert_entity(new_entity)
                output.add_added_entity(new_entity)

        return output

    def match_cities(
        self,
        sent_string: str,
        idx_start_sentence: int,
    ) -> PostProcessOutput:
        """
        This function matches cities in the court decision
        using a CSV file of french cities
        """
        output = PostProcessOutput()

        # Search if a city is in the sentence
        cities_found = self.keyword_cities.extract_keywords(
            deaccent(sent_string.replace("-", " ")),
            span_info=True,
        )
        # Search if a specific keyword that discard the sentence is in it
        no_cities_found = self.keywords_no_cities.extract_keywords(sent_string)
        if not no_cities_found and cities_found:
            for keyword, start_keyword, end_keyword in cities_found:
                if deaccent(sent_string).replace("-", " ").startswith(keyword):
                    continue

                start_new_entity = idx_start_sentence + start_keyword
                end_new_entity = idx_start_sentence + end_keyword

                if self.check_overlap_entities_from_index(
                    start_new_entity,
                    end_new_entity,
                ):
                    postal_code_output = self._find_postal_code(
                        sent_string,
                        idx_start_sentence,
                    )
                    output.merge_output(postal_code_output)

                    new_entity = NamedEntity(
                        text=sent_string[start_keyword:end_keyword],
                        start=start_new_entity,
                        end=end_new_entity,
                        label="localite",
                        source="postprocess",
                    )
                    self.insert_entity(new_entity)
                    output.add_added_entity(new_entity)

        return output

    def match_cities_in_moral(
        self,
        case_sensitive: bool = True,
    ) -> PostProcessOutput:
        """
        This function matches cities and moral entities,
        it deletes the moral entity and add city entities instead
        """
        output = PostProcessOutput()

        keywords = instantiate_flashtext(case_sensitive)

        entities_to_delete = []
        # Iterate over entities found by statistical models to get them
        for entity in self.entities_by_category[CategoryEnum.localite]:
            if len(entity.text) > 1 and entity.text not in keywords.get_all_keywords().keys():
                keywords.add_keyword(entity.text, (entity.text, entity.label))
        for entity in self.entities_by_category[CategoryEnum.personneMorale]:
            if len(entity.text) > 1:
                to_delete = False

                for match, start, end in keywords.extract_keywords(entity.text, span_info=True):
                    to_delete = True

                    new_entity = NamedEntity(
                        text=match[0],
                        start=entity.start + start,
                        end=entity.start + end,
                        label=match[1],
                        source="postprocess",
                    )
                    self.insert_entity(new_entity)
                    output.add_added_entity(new_entity)

                if to_delete:
                    entities_to_delete.append(entity)

        for entity_to_delete in entities_to_delete:
            output.add_deleted_entity(entity_to_delete)
            self.delete_entity(entity_to_delete)

        return output

    def match_facilities(
        self,
        sentence: Sentence,
        sent_string: str,
        idx_start_sentence: int,
    ) -> PostProcessOutput:
        """
        This function matches the name of different types of
        facilities like airports, schools, churchs and so on
        """
        output = PostProcessOutput()
        match_facilities = []

        if facilities_found := self.keyword_facilities.extract_keywords(deaccent(sent_string), span_info=True):
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
                    if start_next_match is not None and token.start_position >= start_next_match:
                        continue
                    if (token.text.istitle() or token.text.isupper()) and token.text not in [
                        "Madame",
                        "Monsieur",
                        "M.",
                        "Mme",
                    ]:
                        if i_tok == 0:
                            span_entity = Span(possible_entity)
                        else:
                            span_entity = Span(possible_entity[:-i_tok])
                        end_entity = token.start_position + len(token.text)
                        start_entity = possible_entity[0].start_position
                        break

                if start_entity and end_entity and self.check_overlap_entities_from_index(start_entity, end_entity):
                    new_entity = NamedEntity(
                        text=span_entity.text.strip(),
                        start=start_entity,
                        label="etablissement",
                        source="postprocess",
                    )
                    self.insert_entity(new_entity)
                    output.add_added_entity(new_entity)
                    match_facilities.append(span_entity.text.strip())

        return output

    def match_regex_with_context(
        self,
        sent_string: str,
        idx_start_sentence: int,
    ) -> PostProcessOutput:
        """This function matches different regex with specific context
        Currently it matches:
        - Numéro de travailleur indépendant
        - Carte nationale d'identité française (cni)
        - french phone numbers
        - SIREN and SIRET numbers"""
        output = PostProcessOutput()
        regex_list = []
        group_dict = {}
        i = 0
        context_keywords = list(set(self.keyword_find_context.extract_keywords(deaccent(sent_string))))
        if not context_keywords:
            return output
        for keyword in set(context_keywords):
            if keyword == "ti":
                regex_list.append(r"(\b(?:\d{12,18})\b)")
                group_dict[i] = "numeroIdentifiant"
                i += 1
            elif keyword == "phone":
                regex_list.append(r"((?:(?:00|\+)33|0)\s?[\d](?:[\s.-]*\d{2}){4}\b)")
                group_dict[i] = "telephoneFax"
                i += 1
            elif keyword == "cni":
                regex_list.append(r"(\b(?:\d{12})|(?:\d{9})\b)")
                group_dict[i] = "numeroIdentifiant"
                i += 1
            elif keyword == "sejour":
                regex_list.append(r"(\b(?:\d{9,10})\b)")
                group_dict[i] = "numeroIdentifiant"
            elif keyword == "clef_bdf":
                regex_list.append(r"(\b(?:\d{6}[A-Z]{2,})\b)")
                group_dict[i] = "numeroIdentifiant"
            elif keyword == "siren_siret":
                regex_list.append(
                    r"((?:\b\d{3}[ \.]?\d{3}[ \.]?\d{3}[ \.]?\d{3}[ \.]?\d{2}\b)|(?:(?<=\b)|(?<=A|B))(\d{3}[ \.]?\d{3}[ \.]?\d{3}\b))"
                )  # noqa: E501
                group_dict[i] = "numeroSiretSiren"
                i += 1

        for match in re.finditer(rf"{'|'.join(regex_list)}", deaccent(sent_string)):
            category = group_dict[match.groups().index(match.group())]
            start_new_entity = idx_start_sentence + match.start()
            end_new_entity = idx_start_sentence + match.end()
            if self.check_overlap_entities_from_index(start_new_entity, end_new_entity):
                new_entity = NamedEntity(
                    text=match.group(),
                    start=start_new_entity,
                    label=category,
                    source="postprocess",
                )
                self.insert_entity(new_entity)
                output.add_added_entity(new_entity)

        return output

    def change_pro_to_physique_no_context(
        self,
        sentence: Sentence,
        idx_start_sentence: int,
        idx_end_sentence: int,
    ) -> PostProcessOutput:
        """
        This function change the category of the entity if there is
        only this entity in the sentence, no context
        """
        output = PostProcessOutput()
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
                    entity.label = CategoryEnum.personnePhysique
                    entity.source = SourceEnum.post_process

                    output.add_modified_entity(entity)
                    changed_entities.append(entity.text)

        return output

    def check_compte_bancaire(
        self,
        sentence: Sentence,
        sent_string: str,
    ) -> PostProcessOutput:
        """
        This function checks if we miss entities from comptebancaire category
        """
        output = PostProcessOutput()
        check_cb = []
        start_sent = sentence[0].start_position
        end_sent = sentence[-1].start_position + len(sentence[-1].text)
        cb_found = self.keyword_compte_bancaire.extract_keywords(deaccent(sent_string), span_info=True)
        if cb_found and re.search(r"\d{6,}", sent_string):
            add_check = not any(
                start_sent <= entity.start <= end_sent and entity.label == CategoryEnum.compteBancaire
                for entity in self.entities
            )

            if add_check:
                new_checklist = Check(
                    check_type="missing_bank_account",
                    sentences=[
                        SentenceIndexes(
                            start=sentence.start_position,
                            end=sentence.end_position,
                        )
                    ],
                )
                self.checklist.append(new_checklist)
                output.add_added_checklist(new_checklist)
                check_cb.append(sent_string)

        return output

    def change_pro_to_physique_with_context(
        self,
        sentence: Sentence,
        sent_string: str,
        regular_expressions: list = PRO_TO_PHYSIQUE_RE.values(),
        context_size: int = 60,
    ) -> PostProcessOutput:
        """Method that changes `professionnel` entities to `personnePhysique`
        if a regular expression is met in its context

        Args:
            sentence (Sentence): sentence that should be scanned
            sent_string (str): string of the sentence
            regular_expressions (list[str], optional): list of uncompiled regexes.
                Defaults to list(PRO_TO_PHYSIQUE_RE.values()).
            context_size (int, optional): size of the context to take into account.
                Defaults to 60.

        Returns:
            list[NamedEntity]: list of changed named entities
        """
        output = PostProcessOutput()

        regular_expressions = re.compile(rf"{'|'.join(regular_expressions)}")

        new_entities = []

        if regular_expressions.search(deaccent(sent_string.lower())):
            for entity in self.get_professional_entities():
                if entity.start > sentence.end_position:
                    break
                elif entity.start >= sentence.start_position:
                    entity_end = entity.end - sentence.start_position

                    clean_context = deaccent(sent_string)[entity_end : entity_end + context_size].lower()

                    if regular_expressions.search(clean_context):
                        entity.label = CategoryEnum.personnePhysique
                        entity.source = SourceEnum.post_process
                        output.add_modified_entity(entity)
                        new_entities.append(entity)

        return output

    def apply_methods(
        self,
        match_against=True,
        match_cities=True,
        match_facilities=True,
        match_regex_with_context=True,
        check_compte_bancaire=True,
        change_pro_no_context=True,
        change_pro_with_context=True,
    ):
        """
        This function apply methods on the whole document
        """
        output = PostProcessOutput()

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
                new_output = self.match_against_case(sent_string, i)
                output.merge_output(new_output)

            if match_regex_with_context:
                new_output = self.match_regex_with_context(sent_string, start_sentence)
                output.merge_output(new_output)

            if check_compte_bancaire:
                new_output = self.check_compte_bancaire(sent, sent_string)
                output.merge_output(new_output)

            if match_cities:
                new_output = self.match_cities(sent_string, start_sentence)
                output.merge_output(new_output)

            if match_facilities:
                new_output = self.match_facilities(sent, sent_string, start_sentence)
                output.merge_output(new_output)

            if change_pro_no_context:
                new_output = self.change_pro_to_physique_no_context(sent, start_sentence, end_sentence)
                output.merge_output(new_output)

            if change_pro_with_context:
                new_output = self.change_pro_to_physique_with_context(sent, sent_string)
                output.merge_output(new_output)

        return output
