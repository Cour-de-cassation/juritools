import bisect
import json
from typing import Dict, Optional
import heapq
import pandas as pd

from juritools.type import CategoryEnum, NamedEntity


class PostProcess:
    def __init__(
        self,
        entities: list[NamedEntity],
        checklist: list[str],
        metadata: Optional[pd.core.frame.DataFrame],
    ):
        self.entities: list[NamedEntity] = []
        self.start_ents: list[int] = []
        self.end_ents: list[int] = []
        self.entities_by_category: dict[CategoryEnum, list[NamedEntity]] = {c: [] for c in CategoryEnum}

        for e in entities:
            self.entities.append(e)
            self.start_ents.append(e.start)
            self.end_ents.append(e.end)
            self.entities_by_category[e.label].append(e)

        self.checklist = checklist
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
    def checklist(self):
        """
        This function returns a list contains warnings requiring manual verification
        """
        return self._checklist

    @checklist.setter
    def checklist(self, value):
        self._checklist = value

    @staticmethod
    def _entities_to_dict(entities: list[NamedEntity]) -> list[Dict]:
        """
        This function returns
        """
        return [entity.model_dump(mode="json") for entity in entities]

    def sort_entities(self, reverse=False):
        entities = []
        entities_by_category = {c: [] for c in CategoryEnum}
        entities_starts = []
        entities_ends = []

        for entity in sorted(self.entities, reverse=reverse):
            entities.append(entity)
            entities_by_category[entity.label].append(entity)
            entities_starts.append(entity.start)
            entities_ends.append(entity.end)

        self.entities = entities
        self.entities_by_category = entities_by_category
        self.start_ents = entities_starts
        self.end_ents = entities_ends

    def ordered_entities(self, reverse=False):
        """
        This function put in order entities after using multiple postprocessing methods
        Inputs:
        - reverse: if true, get order entities in reverse order
        """
        if not reverse:
            return self.entities
        else:
            return self.entities[::-1]

    def get_entities_for_categories(
        self,
        categories: list[CategoryEnum] = [],
        ordered: bool = False,
    ) -> list[NamedEntity]:
        if not ordered:
            return list(e for c in categories for e in self.entities_by_category[c])
        else:
            return list(heapq.merge([self.entities_by_category[c] for c in categories]))

    def get_professional_entities(
        self,
        ordered: bool = False,
    ) -> list[NamedEntity]:
        return self.get_entities_for_categories(
            categories=[
                CategoryEnum.professionnelAvocat,
                CategoryEnum.professionnelMagistratGreffier,
            ],
            ordered=ordered,
        )

    def get_civil_date_entities(
        self,
        ordered: bool = False,
    ) -> list[NamedEntity]:
        return self.get_entities_for_categories(
            categories=[
                CategoryEnum.dateDeces,
                CategoryEnum.dateMariage,
                CategoryEnum.dateNaissance,
            ],
            ordered=ordered,
        )

    def output_json(self, camelcase=True):
        """
        This function returns a json with all the information needed.
        Information are:
        - entities
        - checks
        """
        output_json = {}

        output_json["entities"] = self._entities_to_dict(self.entities)
        output_json["checklist"] = list(set(c.get_message() for c in self.checklist))

        return json.dumps(output_json, ensure_ascii=False, indent=4)

    def check_overlap_entities(self, entity: NamedEntity) -> list[NamedEntity]:
        """
        This function checks if the new entity will overlap an existing entity

        Args:
            entity (NamedEntity): entity to compare to the already existing entities

        Returns:
            overlapping_entities (list[NamedEntity]): list of overlapping entities
        """
        overlapping_entities: list[NamedEntity] = []
        for other_entity in self.entities:
            if entity.overlaps_with_other_entity(other_entity):
                overlapping_entities.append(other_entity)
            else:
                if entity.end < other_entity.start:
                    break
        return overlapping_entities

    def check_overlap_entities_from_index(self, start_new_entity, end_new_entity):
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

        return check

    def insert_entity(self, entity: NamedEntity):
        index = bisect.bisect(self.entities, entity)
        self.entities.insert(index, entity)
        self.start_ents.insert(index, entity.start)
        self.end_ents.insert(index, entity.end)
        if entity.label not in self.entities_by_category:
            self.entities_by_category[entity.label] = [entity]
        else:
            category_index = bisect.bisect(self.entities_by_category[entity.label], entity)
            self.entities_by_category[entity.label].insert(category_index, entity)

    def delete_entity(self, entity: NamedEntity):
        self.entities.remove(entity)
        self.entities_by_category[entity.label].remove(entity)
        self.start_ents.remove(entity.start)
        self.end_ents.remove(entity.end)
