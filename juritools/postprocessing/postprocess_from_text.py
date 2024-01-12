# Import modules
import re
from collections import defaultdict

import pandas as pd
from luhn import verify
from schwifty import IBAN

from juritools.postprocessing import PostProcess
from juritools.type import CategoryEnum, Check, NamedEntity, PostProcessOutput, SourceEnum, merge_entities
from juritools.utils import deaccent, instantiate_flashtext

REGEXES = {
    "email": r"(\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b)",
    # numero_identifiant: insee|passport
    "numero_identifiant": r"(\b(?:\d\s?(?:\d{2}\s?){3}(?:\d{3}\s?){2}(?:\d{2}|\d{0}))|(?:[0-9]{2}[A-z]{2}[0-9]{5})\b)",
    "license_plate": r"(\b[A-Z]{2}-\d{3}-[A-Z]{2}|\d{1,4}\s?[A-Z]{1,3}\s?(?:97[1-6]|[1-9][1-5]|2[AB])\b)",  # noqa: E501
    "iban": r"(\b(?:[A-Z]{2}[ \-]?[0-9]{2})(?=(?:[ \-]?[A-Z0-9]){9,30})(?:(?:[ \-]?[A-Z0-9]{3,5}){2,7})(?:[ \-]?[A-Z0-9]{1,3})?\b)",  # noqa: E501
    "credit_card_number": r"(\b(?:(?:4\d{3})|(?:5[0-5]\d{2})|(?:6\d{3})|(?:1\d{3})|(?:3\d{3}))[- ]?(?:\d{3,4})[- ]?(?:\d{3,4})[- ]?(?:\d{3,5})\b)",  # noqa: E501
    "website": r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))",  # noqa: E501
}


class PostProcessFromText(PostProcess):
    def __init__(
        self,
        text: str,
        entities: list[NamedEntity],
        checklist: list[str],
        metadata: pd.core.frame.DataFrame = None,
    ):
        super().__init__(entities, checklist, metadata)
        self.text = text
        self._deaccented_text = deaccent(text=text)

    def match_from_category(
        self,
        category_list: list[CategoryEnum] = [CategoryEnum.personnePhysique],
        uppercase: bool = True,
        case_sensitive: bool = True,
    ) -> PostProcessOutput:
        """
        Takes entities found by the statistical model from a specific class
        and check in the text if we miss one.
        Inputs:
        - category: the name of the entity class
        """

        label_pos = []
        entity_dict = defaultdict(list)
        keywords = instantiate_flashtext(case_sensitive)
        output = PostProcessOutput()
        # Iterate over entities found by statistical models to get them
        for entity in self.get_entities_for_categories(categories=category_list):
            if len(entity.text) > 1 and entity.text not in entity_dict[entity.label]:
                entity_dict[entity.label].append(deaccent(entity.text))
                if uppercase and entity.text != entity.text.upper():
                    entity_dict[entity.label].append(deaccent(entity.text.upper()))
            label_pos.append(entity.label)
        keywords.add_keywords_from_dict(entity_dict)
        # Iterate over the text to match entities
        keywords_found = keywords.extract_keywords(self._deaccented_text, span_info=True)
        for category, start_new_entity, end_new_entity in keywords_found:
            if self.check_overlap_entities_from_index(start_new_entity, end_new_entity):
                new_entity = NamedEntity(
                    text=self.text[start_new_entity:end_new_entity],
                    start=start_new_entity,
                    end=end_new_entity,
                    label=category,
                    source="postprocess",
                )
                self.insert_entity(new_entity)
                output.add_added_entity(new_entity)

        return output

    def match_regex(
        self,
        email=True,
        numero_identifiant=True,
        license_plate=True,
        iban=True,
        credit_card_number=True,
    ) -> PostProcessOutput:
        """
        Applies regular expressions to the text to find following categories:
        - email
        - INSEE number
        - license plate
        - IBAN
        - SIREN
        - SIRET
        - credit card number
        """
        start_pos = []
        end_pos = []
        match_categories = []
        regex_list = []
        group_dict = {}
        category_dict = {}
        output = PostProcessOutput()

        i = 0
        # Iterate over entities to get start and end indexes
        for entity in self.entities:
            start_pos.append(entity.start)
            end_pos.append(entity.end)
        # Regex for email
        if email:
            like_email = REGEXES["email"]
            regex_list.append(like_email)
            group_dict[i] = "email"
            category_dict["email"] = "email"
            i += 1
        # Regex for INSEE number
        if numero_identifiant:
            like_numero_identifiant = REGEXES["numero_identifiant"]
            regex_list.append(like_numero_identifiant)
            group_dict[i] = "numero_identifiant"
            category_dict["numero_identifiant"] = "numeroIdentifiant"
            i += 1
        # Regex for license plate
        if license_plate:
            like_license_plate = REGEXES["license_plate"]
            regex_list.append(like_license_plate)
            group_dict[i] = "license_plate"
            category_dict["license_plate"] = "plaqueImmatriculation"
            i += 1
        # Regex for IBAN
        if iban:
            like_iban = REGEXES["iban"]
            regex_list.append(like_iban)
            group_dict[i] = "iban"
            category_dict["iban"] = "compteBancaire"
            i += 1

        # Regex for credit card number
        if credit_card_number:
            like_credit_card_number = REGEXES["credit_card_number"]
            regex_list.append(like_credit_card_number)
            group_dict[i] = "credit_card_number"
            category_dict["credit_card_number"] = "compteBancaire"
            i += 1

        # Add entities to the final list after several checks
        for match in re.finditer(rf"{'|'.join(regex_list)}", self.text):
            potential_entity = False
            group_matching = group_dict[match.groups().index(match.group())]
            if group_matching == "iban":
                # Use ISO 13616 to validate IBAN number
                if IBAN(match.group(), allow_invalid=True).is_valid:
                    match_categories.append(match)
                    potential_entity = True
            elif group_matching == "credit_card_number":
                # Use Luhn algorithm to validate credit card number
                if verify(re.sub("[^0-9]", "", match.group())):
                    match_categories.append(match)
                    potential_entity = True
            else:
                match_categories.append(match)
                potential_entity = True

            if potential_entity and self.check_overlap_entities_from_index(match.start(), match.end()):
                new_entity = NamedEntity(
                    text=match.group(),
                    start=match.start(),
                    end=match.end(),
                    label=category_dict[group_matching],
                    source="postprocess",
                )
                self.insert_entity(new_entity)
                output.add_added_entity(new_entity)

        return output

    def match_name_in_website(
        self,
        legal_entity=False,
    ) -> PostProcessOutput:
        """
        This function matches natural names in website addresses
        """
        output = PostProcessOutput()
        match_name_in_website = []

        concerned_entities = {
            deaccent(entity.text.replace(" ", "").lower())
            for entity in self.entities_by_category[CategoryEnum.personnePhysique]
        }
        if legal_entity:
            concerned_entities.update(
                [
                    deaccent(entity.text.replace(" ", "").lower())
                    for entity in self.entities_by_category[CategoryEnum.personneMorale]
                ]
            )
        # Regex to find a website
        regex = REGEXES["website"]
        for match in re.finditer(regex, self.text):
            for name in concerned_entities:
                if name in match.group() and self.check_overlap_entities_from_index(match.start(), match.end()):
                    website_split_list = re.split(r"\.|//", match.group())
                    for split in website_split_list:
                        if name in split:
                            sensitive_domain = re.search(re.escape(split), match.group())
                            new_start = match.start() + sensitive_domain.start()
                            new_end = match.start() + sensitive_domain.end()
                            new_entity = NamedEntity(
                                text=split,
                                start=new_start,
                                end=new_end,
                                label="siteWebSensible",
                                source="postprocess",
                            )
                            self.insert_entity(new_entity)
                            output.add_added_entity(new_entity)
                            match_name_in_website.append(split)

        return output

    def match_metadata_jurinet(
        self,
        legal=True,
    ) -> PostProcessOutput:
        """
        This function uses the metadata from jurinet database to match entities or
        change an already detected entity with the wrong category
        """
        output = PostProcessOutput()
        if self.metadata is None:
            return output

        match_meta = []
        # Collect and organize metadata of interest
        party_name = set()
        party_address = set()
        for tup in self.metadata.query('TYPE_PARTIE=="PP"').itertuples():
            if isinstance(tup.PRENOM, str):
                party_name.add(deaccent(tup.PRENOM))
            if isinstance(tup.AUTRE_PRENOM, str):
                party_name.add(deaccent(tup.PRENOM))
            if isinstance(tup.ALIAS, str):
                party_name.add(deaccent(tup.ALIAS))
            if isinstance(tup.NOM, str):
                party_name.add(deaccent(tup.NOM))
            if isinstance(tup.NOM_MARITAL, str):
                party_name.add(deaccent(tup.NOM_MARITAL))
            if isinstance(tup.LIG_ADR2, str):
                party_address.add(deaccent(tup.LIG_ADR2))

        pro_name = set()
        for tup in self.metadata.query("ID_PARTIE==0").itertuples():
            if isinstance(tup.PRENOM, str):
                pro_name.add(deaccent(tup.PRENOM))
            if isinstance(tup.AUTRE_PRENOM, str):
                pro_name.add(deaccent(tup.PRENOM))
            if isinstance(tup.ALIAS, str):
                pro_name.add(deaccent(tup.ALIAS))
            if isinstance(tup.NOM, str):
                pro_name.add(deaccent(tup.NOM))
            if isinstance(tup.NOM_MARITAL, str):
                pro_name.add(deaccent(tup.NOM_MARITAL))

        lawyer_name = {
            deaccent(tup.NOM)
            for tup in self.metadata.query("TYPE_PERSONNE=='AVOCAT'").itertuples()
            if isinstance(tup.NOM, str)
        }

        if legal:
            noms_pm = set()
            adresses_pm = set()
            for tup in self.metadata.query('TYPE_PARTIE=="PM"').itertuples():
                if isinstance(tup.NOM, str):
                    noms_pm.add(tup.NOM)
                if isinstance(tup.LIG_ADR2, str):
                    adresses_pm.add(tup.LIG_ADR2)

        party_name_uniq = party_name - pro_name - lawyer_name
        party_name_uppercase = {name.upper() for name in party_name_uniq}
        party_name_uniq.update(party_name_uppercase)
        pro_name_uniq = pro_name - party_name - lawyer_name
        pro_name_uppercase = {name.upper() for name in pro_name_uniq}
        pro_name_uniq.update(pro_name_uppercase)
        lawyer_name_uniq = lawyer_name - pro_name - party_name
        lawyer_name_uppercase = {name.upper() for name in lawyer_name_uniq}
        lawyer_name_uniq.update(lawyer_name_uppercase)

        # Collect entities already detected

        for ent in self.get_professional_entities():
            # Change pro to natural and pro to pro based on metadata
            # Should we do it for natural to pro?
            if "professionnel" in ent.label.value and deaccent(ent.text) in party_name_uniq:
                ent.label = CategoryEnum.personnePhysique
                ent.source = SourceEnum.post_process
                output.add_modified_entity(ent)
                match_meta.append(ent.text)
            elif "professionnelAvocat" in ent.label.value and deaccent(ent.text) in pro_name_uniq:
                ent.label = CategoryEnum.professionnelMagistratGreffier
                ent.source = SourceEnum.post_process
                output.add_modified_entity(ent)
                match_meta.append(ent.text)
            elif "professionnelMagistratGreffier" in ent.label.value and deaccent(ent.text) in lawyer_name_uniq:
                ent.label = CategoryEnum.professionelAvocat
                ent.source = SourceEnum.post_process
                output.add_modified_entity(ent)
                match_meta.append(ent.text)

        if not_detected_party := party_name_uniq.difference(
            {deaccent(ent.text) for ent in self.entities if ent.label == CategoryEnum.personnePhysique}
        ):
            party_keywords = instantiate_flashtext(True)
            party_keywords.add_keywords_from_list(list(not_detected_party))
            party_found = party_keywords.extract_keywords(deaccent(self.text), span_info=True)
            start_pos = []
            end_pos = []
            for keyword, start_keyword, end_keyword in party_found:
                if self.check_overlap_entities_from_index(start_keyword, end_keyword):
                    new_entity = NamedEntity(
                        text=self.text[start_keyword:end_keyword],
                        start=start_keyword,
                        end=end_keyword,
                        label="personnePhysique",
                        source="postprocess",
                    )
                    self.insert_entity(new_entity)
                    output.add_added_entity(new_entity)
                    start_pos.append(start_keyword)
                    end_pos.append(end_keyword)
                    match_meta.append(keyword)

        return output

    def match_metadata_jurica(
        self,
    ) -> PostProcessOutput:
        """
        This function uses the dirty metadata from jurica database to match entities
        Should we raised a check when an already detected entity with another label
        is in the meta?
        """
        output = PostProcessOutput()
        if self.metadata is None:
            return output

        match_meta = []
        # Find meta not detected in the text
        party_name = set(self.metadata.text.apply(deaccent).values)

        not_detected_party = party_name.difference(
            {deaccent(ent.text) for ent in self.entities_by_category[CategoryEnum.personnePhysique]}
        )

        if len(not_detected_party) > 0:
            party_keywords = instantiate_flashtext(True)
            party_keywords.add_keywords_from_list(list(not_detected_party))
            party_found = party_keywords.extract_keywords(self._deaccented_text, span_info=True)

            party_found = list(party_found)
            start_pos = []
            end_pos = []

            for keyword, start_keyword, end_keyword in party_found:
                if self.check_overlap_entities_from_index(start_keyword, end_keyword):
                    new_entity = NamedEntity(
                        text=self.text[start_keyword:end_keyword],
                        start=start_keyword,
                        end=end_keyword,
                        label="personnePhysique",
                        source="postprocess",
                    )
                    self.insert_entity(new_entity)
                    output.add_added_entity(new_entity)
                    start_pos.append(start_keyword)
                    end_pos.append(end_keyword)
                    match_meta.append(keyword)

        return output

    def check_metadata(
        self,
    ) -> PostProcessOutput:
        """
        Checks if metadata from jurinet and jurica are well detected in the text
        """
        output = PostProcessOutput()

        if self.metadata is None:
            return output

        df_natural = self.metadata[["text", "entity"]].query("entity in ['personnePhysique']")
        meta_not_detected = []
        physical_entities = {
            deaccent(entity.text.lower()) for entity in self.entities_by_category[CategoryEnum.personnePhysique]
        }

        for meta in df_natural.text.values:
            keyword = instantiate_flashtext(True)
            keyword.add_keyword(deaccent(meta))
            if deaccent(meta.lower()) not in physical_entities and keyword.extract_keywords(self._deaccented_text):
                new_checklist = Check(
                    check_type="incorrect_metadata",
                    metadata_text=[meta],
                )
                self.checklist.append(new_checklist)
                output.add_added_checklist(new_checklist)
                meta_not_detected.append(meta)

        return output

    def check_cadastre(
        self,
    ) -> PostProcessOutput:
        """
        This function check if we miss entities from cadastre category
        """
        output = PostProcessOutput()
        cadastre_list = ["cadastré", "cadastrés", "cadastrée", "cadastrées"]
        keyword = instantiate_flashtext(False)
        for cad in cadastre_list:
            keyword.add_keyword(cad)

        cnt = sum(ent.label == CategoryEnum.cadastre for ent in self.entities)

        keyword_found = keyword.extract_keywords(self.text)
        if len(keyword_found) != 0 and len(keyword_found) >= cnt:
            new_checklist = Check(check_type="missing_cadatre")
            self.checklist.append(new_checklist)
            output.add_added_checklist(new_checklist)
        return output

    def check_compte_bancaire(
        self,
    ) -> PostProcessOutput:
        """
        This function check if we miss entities from comptebancaire category
        """
        output = PostProcessOutput()
        keyword = instantiate_flashtext(False)
        keyword.add_keyword("compte bancaire")
        keyword_found = keyword.extract_keywords(self.text)
        # if `compte bancaire` appears more than there are compteBancaire entities
        cnt = len(self.entities_by_category[CategoryEnum.compteBancaire])

        if len(keyword_found) > cnt:
            new_checklist = Check(check_type="missing_bank_account")
            self.checklist.append(new_checklist)
            output.add_added_checklist(new_checklist)

        return output

    def juvenile_facility_entities(
        self,
    ) -> PostProcessOutput:
        """
        This function captures specific juvenile facility entities
        """
        output = PostProcessOutput()
        # Add juvenile facility entities to catch
        keyword = instantiate_flashtext(False)
        juvenile_facility = "etablissement penitentiaire specialise pour mineurs"
        location = [
            "de quievrechain",
            "de lavaur",
            "d'orvault",
            "de porcheville",
            "du rhone",
            "de marseille",
        ]
        for loc in location:
            keyword.add_keyword(f"{juvenile_facility} {loc}")
        # Find entities in the text without accents
        keyword_found = keyword.extract_keywords(deaccent(self.text), span_info=True)
        for new_ent, start_new_ent, end_new_ent in keyword_found:
            if self.check_overlap_entities_from_index(start_new_ent, end_new_ent):
                new_entity = NamedEntity(
                    text=self.text[start_new_ent:end_new_ent],
                    start=start_new_ent,
                    end=end_new_ent,
                    label="etablissement",
                    source="postprocess",
                )
                self.insert_entity(new_entity)
                output.add_added_entity(new_entity)
        return output

    def manage_le(
        self,
    ) -> PostProcessOutput:
        """
        This function manages the specific case in which the pronoum 'le' is
        in uppercase and consider by the model as a natural or profesional person
        """
        output = PostProcessOutput()
        # Add juvenile facility entities to catch
        keyword = instantiate_flashtext(False)
        le_after_sir = "m. le"
        titles = ["prefet", "directeur", "procureur", "president"]
        for title in titles:
            keyword.add_keyword(f"{le_after_sir} {title}")
        # Find entities in the text without accents
        keyword_found = keyword.extract_keywords(deaccent(self.text), span_info=True)

        index_list_le = []
        for keyword in keyword_found:
            index_list_le.extend(
                index
                for index, entity in enumerate(self.entities)
                if (entity.start == keyword[1] + 3 and entity.end == keyword[1] + 5 and entity.text.lower() == "le")
            )

        for index in index_list_le:
            entity_to_delete = self.entities[index]
            output.add_deleted_entity(entity_to_delete)
            self.delete_entity(entity_to_delete)

        return output

    def manage_quote(
        self,
        quotes_list: tuple[str] = ("'", '"', "’", "`", "‘", "«", "»"),
    ) -> PostProcessOutput:
        """
        Manages the specific case in which a quote is present in a natural person entity
        """
        output = PostProcessOutput()
        quote_only_entities = []

        for entity in self.entities_by_category[CategoryEnum.personnePhysique]:
            modified_entity = False
            if entity.text.startswith(quotes_list):
                if len(entity.text) == 1:
                    quote_only_entities.append(entity)
                else:
                    n_whitespaces = len(entity.text[1:]) - len(entity.text[1:].lstrip())
                    entity.text = entity.text[1 + n_whitespaces :]
                    entity.start = entity.start + 1 + n_whitespaces
                    entity.source = SourceEnum.post_process
                    modified_entity = True

            if (len(entity.text) != 1) and (entity.text.endswith(quotes_list)):
                new_text = entity.text[:-1].rstrip()
                entity.text = new_text
                entity.source = SourceEnum.post_process
                modified_entity = True

            if modified_entity:
                output.add_modified_entity(entity)

        for entity_to_delete in quote_only_entities:
            output.add_deleted_entity(entity_to_delete)
            self.delete_entity(entity_to_delete)

        return output

    def match_additional_terms(
        self,
        additional_terms_str: str = "",
        separators: list[str] = ["/"],
        ignore_accents: bool = True,
        ignore_case: bool = True,
    ) -> PostProcessOutput:
        """Computes additional entities based on input string.
        The category will be `annotationSupplementaire`.

        If an additional term is in conflict with another entity, this function will
        split the additional term so that the entity still appears.
        ex:
            text = "Le cheval blanc d'Henri IV"
            additional_terms_str = "Le cheval blanc d'Henri IV"
            # if "Henri VI" is a personnePhysique, entities will be:
             - "Le cheval blanc d'" (annotationSupplementaire)
             - "Henri VI" (personnePhysique)

        Args:
            additional_terms_str (str, optional): list of additional terms as a string.
                Defaults to "".
            separators (list[str], optional): list of separators to use.
                Defaults to ["/"].
            ignore_accents (bool, optional): whether to ignore accents
                while looking for additional terms to annotate.
                Defaults to True.
            ignore_case (bool, optional): whether to ignore case while
            while looking for additional terms to annotate.
                Defaults to True.
        """
        output = PostProcessOutput()
        additional_terms = []
        websites_placeholders = {}
        entities = []

        # parsing additional terms
        if len(separators) == 1:
            s = separators[0]
        else:
            s = rf"({'|'.join(separators)})"

        separator_re = re.compile(s)

        # extraction of websites
        website = re.compile(REGEXES["website"])
        for i, w in enumerate(website.finditer(additional_terms_str)):
            placeholder = f"WEBSITE_PLACEHOLDER_{i}"
            additional_terms_str = additional_terms_str.replace(w.group(), placeholder)
            websites_placeholders[placeholder] = w.group()

        additional_terms_tmp = separator_re.split(string=additional_terms_str)

        for term in additional_terms_tmp:
            for placeholder, website in websites_placeholders.items():
                term = term.replace(placeholder, website)
            if (len(term) > 0) and (term not in separators):
                additional_terms.append(term.strip())

        # text settings
        text = self.text
        if ignore_accents:
            text = deaccent(text=text)
        if ignore_case:
            additional_terms = [a.upper() for a in additional_terms]
            text = text.upper()

        for term in additional_terms:
            for instance in re.finditer(pattern=term, string=text):
                if instance.group():
                    entities.append(
                        NamedEntity(
                            start=instance.start(),
                            end=instance.end(),
                            text=self.text[instance.start() : instance.end()],
                            label="annotationSupplementaire",
                            source="postprocess",
                        )
                    )
        if len(entities) > 0:
            entities = sorted(entities)
            entities_to_add = []

            left = entities[0]
            entities = entities[1:]

            while len(entities) > 0:
                right = entities[0]
                entities = entities[1:]

                if left.end >= right.start:
                    left = merge_entities(left=left, right=right)
                else:
                    entities_to_add.append(left)
                    left = right

            entities_to_add.append(left)

            for new_entity in entities_to_add:
                self.insert_entity(new_entity)
                output.add_added_entity(new_entity)

        return output
