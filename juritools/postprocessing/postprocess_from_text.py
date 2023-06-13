# Import modules
from juritools.type import NamedEntity
from juritools.postprocessing import PostProcess
from typing import List
from collections import defaultdict
from juritools.utils import deaccent, instantiate_flashtext
import re
import pandas as pd
from luhn import verify
from schwifty import IBAN


class PostProcessFromText(PostProcess):
    def __init__(
        self,
        text: str,
        entities: List[NamedEntity],
        manual_checklist: List[str],
        metadata: pd.core.frame.DataFrame = None,
    ):
        super().__init__(entities, manual_checklist, metadata)
        self.text = text

    def match_from_category(
        self,
        category_list: List[str] = ["personnephysique"],
        uppercase: bool = True,
        case_sensitive: bool = True,
        postpro_entities=set(),
    ):

        """
        This function takes entities found by the statistical model from a specific class
        and check in the text if we miss one.
        Inputs:
        - category: the name of the entity class
        """

        label_pos = []
        entity_dict = defaultdict(list)
        keywords = instantiate_flashtext(case_sensitive)
        # Iterate over entities found by statistical models to get them
        for entity in self.entities:
            if (
                entity.label.lower() in category_list
                and len(entity.text) > 1
                and entity.text not in entity_dict[entity.label]
            ):
                entity_dict[entity.label].append(entity.text)
                if uppercase and entity.text != entity.text.upper():
                    entity_dict[entity.label].append(entity.text.upper())
            label_pos.append(entity.label)
        keywords.add_keywords_from_dict(entity_dict)
        # Iterate over the text to match entities
        keywords_found = keywords.extract_keywords(self.text, span_info=True)
        for category, start_new_entity, end_new_entity in keywords_found:
            if self.check_overlap_entities(start_new_entity, end_new_entity):
                self.entities.append(
                    NamedEntity(
                        text=self.text[start_new_entity:end_new_entity],
                        start=start_new_entity,
                        end=end_new_entity,
                        label=category,
                        source="postprocess",
                    )
                )
                postpro_entities.add(self.text[start_new_entity:end_new_entity])

        return postpro_entities or "No match!"

    def match_regex(
        self,
        email=True,
        insee=True,
        license_plate=True,
        iban=True,
        credit_card_number=True,
    ):

        """
        This function apply regular expressions to the text to find following categories:
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
        i = 0
        # Iterate over entities to get start and end indexes
        for entity in self.entities:
            start_pos.append(entity.start)
            end_pos.append(entity.end)
        # Regex for email
        if email:
            like_email = r"(\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b)"
            regex_list.append(like_email)
            group_dict[i] = "email"
            category_dict["email"] = "email"
            i += 1
        # Regex for INSEE number
        if insee:
            like_insee = r"(\b(?:\d\s?(?:\d{2}\s?){3}(?:\d{3}\s?){2}(?:\d{2}|\d{0}))\b)"
            regex_list.append(like_insee)
            group_dict[i] = "insee"
            category_dict["insee"] = "noInsee"
            i += 1
        # Regex for license plate
        if license_plate:
            like_license_plate = r"(\b[A-Z]{2}-\d{3}-[A-Z]{2}|\d{1,4}\s?[A-Z]{1,3}\s?(?:97[1-6]|[1-9][1-5]|2[AB])\b)"
            regex_list.append(like_license_plate)
            group_dict[i] = "license_plate"
            category_dict["license_plate"] = "plaqueImmatriculation"
            i += 1
        # Regex for IBAN
        if iban:
            like_iban = r"(\b(?:[A-Z]{2}[ \-]?[0-9]{2})(?=(?:[ \-]?[A-Z0-9]){9,30})(?:(?:[ \-]?[A-Z0-9]{3,5}){2,7})(?:[ \-]?[A-Z0-9]{1,3})?\b)"
            regex_list.append(like_iban)
            group_dict[i] = "iban"
            category_dict["iban"] = "compteBancaire"
            i += 1

        # Regex for credit card number
        if credit_card_number:
            like_credit_card_number = r"(\b(?:(?:4\d{3})|(?:5[0-5]\d{2})|(?:6\d{3})|(?:1\d{3})|(?:3\d{3}))[- ]?(?:\d{3,4})[- ]?(?:\d{3,4})[- ]?(?:\d{3,5})\b)"
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

            if potential_entity and self.check_overlap_entities(
                match.start(), match.end()
            ):
                self.entities.append(
                    NamedEntity(
                        text=match.group(),
                        start=match.start(),
                        end=match.end(),
                        label=category_dict[group_matching],
                        source="regex",
                    )
                )

        return match_categories

    def match_name_in_website(self, legal_entity=False):
        """
        This function matches natural names in website addresses
        """
        match_name_in_website = []

        concerned_entities = {
            deaccent(entity.text.replace(" ", "").lower())
            for entity in self.entities
            if "personnephysique" in entity.label.lower()
        }
        if legal_entity:
            concerned_entities.update(
                [
                    deaccent(entity.text.replace(" ", "").lower())
                    for entity in self.entities
                    if "personnemorale" in entity.label.lower()
                ]
            )
        # Regex to find a website
        regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        for match in re.finditer(regex, self.text):
            for name in concerned_entities:
                if name in match.group() and self.check_overlap_entities(
                    match.start(), match.end()
                ):
                    website_split_list = re.split(r"\.|//", match.group())
                    for split in website_split_list:
                        if name in split:
                            sensitive_domain = re.search(
                                re.escape(split), match.group()
                            )
                            new_start = match.start() + sensitive_domain.start()
                            new_end = match.start() + sensitive_domain.end()
                            self.entities.append(
                                NamedEntity(
                                    text=split,
                                    start=new_start,
                                    end=new_end,
                                    label="siteWebSensible",
                                    source="regex",
                                )
                            )
                            match_name_in_website.append(split)

        return match_name_in_website

    def match_metadata_jurinet(self, legal=True):
        """
        This function uses the metadata from jurinet database to match entities or
        change an already detected entity with the wrong category
        """
        if self.metadata is None:
            return "No metadata collected"

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

        for ent in self.entities:
            # Change pro to natural and pro to pro based on metadata
            # Should we do it for natural to pro?
            if "professionnel" in ent.label and deaccent(ent.text) in party_name_uniq:
                ent.label = "personnePhysique"
                ent.source = "postprocess"
                match_meta.append(ent.text)
            elif (
                "professionnelAvocat" in ent.label
                and deaccent(ent.text) in pro_name_uniq
            ):
                ent.label = "professionnelMagistratGreffier"
                ent.source = "postprocess"
                match_meta.append(ent.text)
            elif (
                "professionnelMagistratGreffier" in ent.label
                and deaccent(ent.text) in lawyer_name_uniq
            ):
                ent.label = "professionnelAvocat"
                ent.source = "postprocess"
                match_meta.append(ent.text)

        if not_detected_party := party_name_uniq.difference(
            {
                deaccent(ent.text)
                for ent in self.entities
                if ent.label == "personnePhysique"
            }
        ):
            party_keywords = instantiate_flashtext(True)
            party_keywords.add_keywords_from_list(list(not_detected_party))
            party_found = party_keywords.extract_keywords(
                deaccent(self.text), span_info=True
            )
            start_pos = []
            end_pos = []
            for keyword, start_keyword, end_keyword in party_found:
                if self.check_overlap_entities(start_keyword, end_keyword):
                    self.entities.append(
                        NamedEntity(
                            text=self.text[start_keyword:end_keyword],
                            start=start_keyword,
                            end=end_keyword,
                            label="personnePhysique",
                            source="postprocess",
                        )
                    )
                    start_pos.append(start_keyword)
                    end_pos.append(end_keyword)
                    match_meta.append(keyword)

        return match_meta

    def match_metadata_jurica(self):
        """
        This function uses the dirty metadata from jurica database to match entities
        Should we raised a check when an already detected entity with another label is in the meta?
        """
        if self.metadata is None:
            return "No metadata collected"

        match_meta = []
        # Find meta not detected in the text
        party_name = set(self.metadata.text.apply(deaccent).values)
        if not_detected_party := party_name.difference(
            {
                deaccent(ent.text)
                for ent in self.entities
                if ent.label == "personnePhysique"
            }
        ):
            party_keywords = instantiate_flashtext(True)
            party_keywords.add_keywords_from_list(list(not_detected_party))
            party_found = party_keywords.extract_keywords(
                deaccent(self.text), span_info=True
            )
            start_pos = []
            end_pos = []

            for keyword, start_keyword, end_keyword in party_found:
                if self.check_overlap_entities(start_keyword, end_keyword):
                    self.entities.append(
                        NamedEntity(
                            text=self.text[start_keyword:end_keyword],
                            start=start_keyword,
                            end=end_keyword,
                            label="personnePhysique",
                            source="postprocess",
                        )
                    )
                    start_pos.append(start_keyword)
                    end_pos.append(end_keyword)
                    match_meta.append(keyword)

        return match_meta

    def check_metadata(self):
        """
        This function checks if metadata from jurinet and jurica are well detected in the text
        """

        if self.metadata is None:
            return "No metadata collected!"

        df_natural = self.metadata[["text", "entity"]].query(
            "entity in ['personnephysique']"
        )
        meta_not_detected = []
        physical_entities = {
            deaccent(entity.text.lower())
            for entity in self.entities
            if entity.label.lower() in ["personnephysique"]
        }

        for meta in df_natural.text.values:
            keyword = instantiate_flashtext(True)
            keyword.add_keyword(deaccent(meta))
            if deaccent(
                meta.lower()
            ) not in physical_entities and keyword.extract_keywords(
                deaccent(self.text)
            ):
                self.manual_checklist.append(
                    f"{meta} : La base données indique la présence de ce terme mais il n'a pas été annoté. Il y a potentiellement une sous-annotation."
                )
                meta_not_detected.append(meta)
        return meta_not_detected

    def check_cadastre(self):
        """
        This function check if we miss entities from cadastre category
        """
        cadastre_list = ["cadastré", "cadastrés", "cadastrée", "cadastrées"]
        keyword = instantiate_flashtext(False)
        for cad in cadastre_list:
            keyword.add_keyword(cad)

        cnt = sum(ent.label == "cadastre" for ent in self.entities)

        keyword_found = keyword.extract_keywords(self.text)
        if len(keyword_found) != 0 and len(keyword_found) >= cnt:
            self.manual_checklist.append(
                "Il semblerait qu'une ou plusieurs parcelles cadastrales n'aient pas été repérées."
            )

    def check_compte_bancaire(self):
        """
        This function check if we miss entities from comptebancaire category
        """
        keyword = instantiate_flashtext(False)
        keyword.add_keyword("compte bancaire")
        keyword_found = keyword.extract_keywords(self.text)

        cnt = sum(ent.label.lower() == "comptebancaire" for ent in self.entities)

        if len(keyword_found) > cnt:
            self.manual_checklist.append(
                "Il semblerait qu'un ou plusieurs numéros de comptes bancaires n'aient pas été repérées"
            )

    def juvenile_facility_entities(self):
        """
        This function captures specific juvenile facility entities
        """
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
            if self.check_overlap_entities(start_new_ent, end_new_ent):
                self.entities.append(
                    NamedEntity(
                        text=self.text[start_new_ent:end_new_ent],
                        start=start_new_ent,
                        end=end_new_ent,
                        label="etablissement",
                        source="postprocess",
                    )
                )

    def manage_le(self):
        """
        This function manages the specific case in which the pronoum 'le' is
        in uppercase and consider by the model as a natural or profesional person
        """
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
                if (
                    entity.start == keyword[1] + 3
                    and entity.end == keyword[1] + 5
                    and entity.text.lower() == "le"
                )
            )

        self.entities = [
            entity
            for index, entity in enumerate(self.entities)
            if index not in index_list_le
        ]

        return len(index_list_le)

    def manage_quote(self):
        """
        This function manages the specific case in which a quote is present in a natural person entity
        """
        nb_quotes_removed = 0
        index_list_quote = []
        for index, entity in enumerate(self.entities):
            if "personnephysique" in entity.label.lower():
                if entity.text.startswith(("'", '"', "’", "`", "‘", "«", "»")):
                    if len(entity.text) == 1:
                        index_list_quote.append(index)
                    else:
                        len_lstrip = len(
                            self.text[entity.start + 1 : entity.end]
                        ) - len(self.text[entity.start + 1 : entity.end].lstrip())
                        entity.start += 1 + len_lstrip
                        entity.text = self.text[entity.start : entity.end]
                    nb_quotes_removed += 1
                if len(entity.text) != 1 and entity.text.endswith(
                    ("'", '"', "’", "`", "‘", "«", "»")
                ):
                    len_rstrip = len(self.text[entity.start : entity.end - 1]) - len(
                        self.text[entity.start : entity.end - 1].rstrip()
                    )
                    entity.end -= 1 + len_rstrip
                    entity.text = self.text[entity.start : entity.end]
                    nb_quotes_removed += 1

        self.entities = [
            entity
            for index, entity in enumerate(self.entities)
            if index not in index_list_quote
        ]

        return nb_quotes_removed
