from juritools.type import NamedEntity
import pandas as pd
from typing import List, Optional, Dict
from operator import attrgetter
import json


class PostProcess:
    def __init__(
        self,
        entities: List[NamedEntity],
        manual_checklist: List[str],
        metadata: Optional[pd.core.frame.DataFrame],
    ):
        self.entities = entities
        self.start_ents = [entity.start for entity in self.entities]
        self.end_ents = [entity.end for entity in self.entities]
        self.manual_checklist = manual_checklist
        self.metadata = metadata

    @property
    def entities(self):
        """
        This function returns a list containing NamedEntity objects
        """
        return self._entities

    @entities.setter
    def entities(self, value):
        self._entities = value

    @property
    def manual_checklist(self):
        """
        This function returns a list contains warnings requiring manual verification
        """
        return self._manual_checklist

    @manual_checklist.setter
    def manual_checklist(self, value):
        self._manual_checklist = value

    @staticmethod
    def _entities_to_dict(entities: List[NamedEntity]) -> List[Dict]:
        """
        This function returns
        """
        return [entity.dict() for entity in entities]

    def ordered_entities(self, reverse=False):
        """
        This function put in order entities after using multiple postprocessing methods
        Inputs:
        - reverse: if true, get order entities in reverse order
        """
        if reverse:
            return sorted(self.entities, key=attrgetter("start"), reverse=True)
        return sorted(self.entities, key=attrgetter("start"))

    def map_category_to_camelcase(self, list_of_entities):
        """
        This function returns the list of entities with the label
        in camelCase. Example: PersonnePhysicoMorale
        """
        camelCaseCategories = {
            "adresse": "adresse",
            "cadastre": "cadastre",
            "personnemorale": "personneMorale",
            "personnephysicomorale": "personnePhysicoMorale",
            "personnephysiqueprenom": "personnePhysique",
            "personnephysiquenom": "personnePhysique",
            "personnephysique": "personnePhysique",
            "professionnelavocat": "professionelAvocat",
            "professionnelmagistratgreffier": "professionnelMagistratGreffier",
            "datedenaissance": "dateNaissance",
            "datededeces": "dateDeces",
            "datedemariage": "dateMariage",
            "telephonefaxemail": "telephoneFaxEmail",
            "noinsee": "noInsee",
            "plaquedimmatriculation": "plaqueImmatriculation",
            "comptebancaire": "compteBancaire",
            "etablissementmineur": "etablissementMineur",
            "autrenumero": "autreNumero",
            "autrelieu": "autreLieu",
        }

        for entity in list_of_entities:
            if entity.label in camelCaseCategories:
                entity.label = camelCaseCategories[entity.label]
        return list_of_entities

    def output_json(self, camelcase=True):
        """
        This function returns a json with all the information needed.
        Information are:
        - entities
        - checks
        """
        output_json = {}
        ordered_entities = self.ordered_entities()
        if camelcase:
            output_json["entities"] = self._entities_to_dict(
                self.map_category_to_camelcase(ordered_entities)
            )
        else:
            output_json["entities"] = self._entities_to_dict(ordered_entities)
        output_json["checklist"] = list(set(self.manual_checklist))
        # output_json_formatted = json.dumps(output_json, ensure_ascii=False).encode('utf8')

        return json.dumps(output_json, ensure_ascii=False, indent=4)

    def check_overlap_entities(self, start_new_entity, end_new_entity):
        """
        This function checks if the new entity will overlap an existing entity

        Args:
            start_new_entity (int): Start index of the new entity
            end_new_entity (int): End index of the next entity
        """
        if start_new_entity in self.start_ents or end_new_entity in self.end_ents:
            return False
        check = not any(
            start <= start_new_entity < end
            or start < end_new_entity <= end
            or start_new_entity <= start <= end_new_entity
            for start, end in zip(self.start_ents, self.end_ents)
        )
        if check:
            self.start_ents.append(start_new_entity)
            self.end_ents.append(end_new_entity)

        return check
