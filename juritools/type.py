from enum import Enum
from aenum import MultiValueEnum


from pydantic import BaseModel, computed_field, field_validator
from typing import Any, Optional, Union
from juritools.utils import deaccent


class SourceEnum(Enum):
    ner_model = "NER model"
    post_process = "postprocess"


class CategoryEnum(MultiValueEnum):
    adresse = "adresse"
    cadastre = "cadastre"
    email = "email"
    personneMorale = "personneMorale"
    personnePhysicoMorale = "personnePhysicoMorale"
    personnePhysique = "personnePhysique"
    professionnelAvocat = "professionnelAvocat"
    professionnelMagistratGreffier = "professionnelMagistratGreffier"
    dateNaissance = "dateNaissance"
    dateDeces = "dateDeces"
    dateMariage = "dateMariage"
    numeroIdentifiant = "numeroIdentifiant", "insee"
    plaqueImmatriculation = "plaqueImmatriculation"
    compteBancaire = "compteBancaire"
    localite = "localite"
    numeroSiretSiren = "numeroSiretSiren"
    annotationSupplementaire = "annotationSupplementaire"
    siteWebSensible = "siteWebSensible"
    etablissement = "etablissement"
    telephoneFax = "telephoneFax"


class NamedEntity(BaseModel):
    text: str
    start: int
    label: CategoryEnum
    source: SourceEnum
    score: float = 1.0

    @field_validator("text")
    @classmethod
    def text_should_not_be_empty(cls, value):
        if value == "":
            raise ValueError("text field is empty, a named entity cannot be an empty string")
        return value

    @computed_field
    @property
    def entityId(self) -> str:
        return f"{self.label.value}_{deaccent(self.text.lower())}"

    @computed_field
    @property
    def end(self) -> int:
        return self.start + len(self.text)

    def __lt__(self, other):
        return self.start < other.start

    def __gt__(self, other):
        return self.end > other.end

    def overlaps_with_other_entity(self, other):
        if other.end <= self.start:
            return False
        elif self.end <= other.start:
            return False
        return True

    def __hash__(self) -> int:
        return hash(f"{self.start}->{self.end}: {self.text} [{self.label} ({self.source}:{self.score})]")


class CheckTypeEnum(Enum):
    similar_writing = "similar_writing"
    different_categories = "different_categories"
    less_than_two_characters = "less_than_two_characters"
    missing_bank_account = "missing_bank_account"
    missing_cadatre = "missing_cadatre"
    incorrect_metadata = "incorrect_metadata"
    # used as a placeholder for initialization
    other_checklist = "other_checklist"


class SentenceIndexes(BaseModel):
    start: int
    end: int

    def __hash__(self) -> int:
        return hash(f"{self.start}->{self.end}")


class Check(BaseModel):
    check_type: CheckTypeEnum = CheckTypeEnum.other_checklist
    entities: list[NamedEntity] = []
    sentences: list[SentenceIndexes] = []
    metadata_text: list[str] = []

    def __init__(
        self,
        check_type: CheckTypeEnum = CheckTypeEnum.other_checklist,
        entities: list[NamedEntity] = [],
        sentences: list[SentenceIndexes] = [],
        metadata_text: list[str] = [],
        *args,
        **kwargs,
    ):
        BaseModel.__init__(self, *args, **kwargs)

        self.check_type = CheckTypeEnum(check_type)

        for e in entities:
            if not isinstance(e, NamedEntity):
                raise ValueError(f"entities should be a list of NamedEntity not {type(e)}")
            self.entities.append(e.model_copy())

        for s in sentences:
            if not isinstance(s, SentenceIndexes):
                raise ValueError(f"sentences should be a list of SentenceIndexes not {type(s)}")
            self.sentences.append(s)

        self.metadata_text = metadata_text

    def get_message(self):
        message = ""
        if self.check_type == CheckTypeEnum.similar_writing:
            # only two entities
            text1, text2 = [e.text for e in self.entities]
            message = f"'{text1}' est similaire à '{text2}'. Est-ce une erreur de saisie ?"
        elif self.check_type == CheckTypeEnum.different_categories:
            text = self.entities[0].text
            categories = list(set(e.label.value for e in self.entities))
            message = f"L'annotation '{text}' est présente dans différentes catégories: {categories}"
        elif self.check_type == CheckTypeEnum.less_than_two_characters:
            text = self.entities[0]
            message = f"'{text}' cette annotation fait moins de deux caratères. Est-ce normal ?"
        elif self.check_type == CheckTypeEnum.missing_bank_account:
            message = "Il semblerait qu'un ou plusieurs numéros de comptes bancaires n'aient pas été repérés."
        elif self.check_type == CheckTypeEnum.incorrect_metadata:
            message = "La base de données indique la présence de ces termes mais ils n'ont pas été annotés: "
            f"{self.metadata_text}. Il y a potentiellement une sous-annotation."
        elif self.check_type == CheckTypeEnum.missing_cadatre:
            message = "Il semblerait qu'une ou plusieurs parcelles cadastrales n'aient pas été repérées."

        return message

    def __hash__(self) -> int:
        entities = sorted([hash(e) for e in self.entities])
        sentences = sorted(hash(s) for s in self.sentences)
        metadata_text = sorted(self.metadata_text)

        return hash(
            f"Check: type: {self.check_type}; entities: {entities}; sentences: {sentences}; metadata: {metadata_text}"
        )


class PostProcessOutput(BaseModel):
    added_entities: list[NamedEntity] = []
    deleted_entities: list[NamedEntity] = []
    modified_entities: list[NamedEntity] = []

    added_checklist: list[Check] = []
    deleted_checklist: list[Check] = []
    modified_checklist: list[Check] = []

    def __init__(
        self,
        added_entities: list[NamedEntity] = [],
        deleted_entities: list[NamedEntity] = [],
        modified_entities: list[NamedEntity] = [],
        added_checklist: list[Check] = [],
        deleted_checklist: list[Check] = [],
        modified_checklist: list[Check] = [],
        *args,
        **kwargs,
    ):
        BaseModel.__init__(self, *args, **kwargs)

        for e in added_entities:
            if not isinstance(e, NamedEntity):
                raise ValueError(f"added_entities should be a list of NamedEntity not {type(e)}")
            self.added_entities.append(e.model_copy())

        for e in modified_entities:
            if not isinstance(e, NamedEntity):
                raise ValueError(f"modified_entities should be a list of NamedEntity not {type(e)}")
            self.modified_entities.append(e.model_copy())
        for e in deleted_entities:
            if not isinstance(e, NamedEntity):
                raise ValueError(f"deleted_entities should be a list of NamedEntity not {type(e)}")
            self.deleted_entities.append(e.model_copy())

        for c in added_checklist:
            if not isinstance(c, Check):
                raise ValueError(f"added_checklist should be a list of Check not {type(c)}")
            self.add_added_checklist(c.model_copy())

        for c in modified_checklist:
            if not isinstance(c, Check):
                raise ValueError(f"modified_checklist should be a list of Check not {type(c)}")
            self.modified_checklist.append(c.model_copy())

        for c in deleted_checklist:
            if not isinstance(c, Check):
                raise ValueError(f"deleted_checklist should be a list of Check not {type(c)}")
            self.deleted_checklist.append(c.model_copy())

    def add_added_entity(self, entity: NamedEntity):
        self.added_entities.append(entity.model_copy())

    def add_modified_entity(self, entity: NamedEntity):
        self.modified_entities.append(entity.model_copy())

    def add_deleted_entity(self, entity: NamedEntity):
        self.deleted_entities.append(entity.model_copy())

    def add_added_checklist(self, checklist: Check):
        self.added_checklist.append(checklist.model_copy())

    def add_modified_checklist(self, checklist: Check):
        self.modified_checklist.append(checklist.model_copy())

    def add_deleted_checklist(self, checklist: Check):
        self.deleted_checklist.append(checklist.model_copy())

    def __eq__(self, other):
        return (
            (set(self.added_entities) == set(other.added_entities))
            and (set(self.deleted_entities) == set(other.deleted_entities))
            and (set(self.modified_entities) == set(other.modified_entities))
            and (set(self.added_checklist) == set(other.added_checklist))
            and (set(self.deleted_checklist) == set(other.deleted_checklist))
            and (set(self.modified_checklist) == set(other.modified_checklist))
        )

    def merge_output(self, other):
        self.deleted_entities = self.deleted_entities + other.deleted_entities
        self.deleted_checklist = self.deleted_checklist + other.deleted_checklist
        # TODO: consulter Amaury pour voir si on a intérêt à être plus subtils pour les champs suivants
        self.added_entities = self.added_entities + other.added_entities
        self.added_checklist = self.added_checklist + other.added_checklist
        self.modified_entities = self.modified_entities + other.modified_entities
        self.modified_checklist = self.modified_checklist + other.modified_checklist


def merge_entities(left, right):
    if left.label != right.label:
        raise ValueError("Cannot merge entities from different categories")
    if left.source != right.source:
        raise ValueError("Cannot merge entities from different sources")

    if left.start <= right.start:
        if left.end < right.start:
            raise ValueError("Cannot merge disjointed entities")
        elif left.end >= right.end:
            # the left entity encapsulates the right: return the current
            text = left.text
            start = left.start
            end = left.end
        else:
            text = left.text + right.text[left.end - right.start : right.end - right.start]
            start = left.start
            end = right.end
    else:
        if left.start > right.end:
            raise ValueError("Cannot merge disjointed entities")
        elif right.end >= left.end:
            # the right entity encapsulates the left: return the right
            text = right.text
            start = right.start
            end = right.end
        else:
            text = right.text + left.text[right.end - left.start : left.end - left.start]
            start = right.start
            end = left.end

    return NamedEntity(
        text=text,
        start=start,
        end=end,
        source=left.source,
        label=left.label,
    )


class TypePartie(Enum):
    """Type que les parties peuvent prendre pour Jurica et JuriTJ"""

    personne_morale = "PM"
    personne_phyisque = "PP"
    autorite_administrative = "AA"


class QualitePartie(Enum):
    """Qualité que les parties peuvent prendre pour Jurica et JuriTJ"""

    personne_physique_autre_partie = "F"
    personne_physique_demandeur = "I"
    personne_physique_defendeur = "K"
    personne_physique_partie_intervenante = "M"
    personne_morale_autre_partie = "G"
    personne_morale_demandeur = "J"
    personne_morale_defendeur = "L"
    personne_morale_partie_intervenante = "N"


class JuriTJPartie(BaseModel):
    """Classe représentant les parties pour les décisions de TJ émises par Label"""

    type: TypePartie
    qualite: QualitePartie
    nom: str
    prenom: Optional[str] = ""
    civilite: Optional[str] = ""


class JuricaPartieAttributes(BaseModel):
    """Classe représentant les attributs des parties pour les décisions de CA émises par Label"""

    qualitePartie: QualitePartie
    typePersonne: TypePartie


class JuricaPartie(BaseModel):
    """Classe représentant les parties pour les décisions de CA émises par Label"""

    attributes: JuricaPartieAttributes
    identite: str


class DecisionSourceNameEnum(Enum):
    """Énumération des sources que peuvent prendre les décisions émises par Label"""

    jurinet = "jurinet"
    jurica = "jurica"
    juritj = "juritj"


class Decision(BaseModel):
    """Classe représentant les décisions émises par Label"""

    idLabel: str
    idDecision: str
    sourceId: int
    sourceName: DecisionSourceNameEnum
    text: str
    parties: Union[list[JuriTJPartie], list[JuricaPartie], list[list[Any]], None] = []
    categories: Optional[list[CategoryEnum]] = [CategoryEnum.personnePhysique]

    @field_validator("text")
    @classmethod
    def text_should_not_be_empty(cls, v):
        if v == "":
            raise ValueError("text field is empty")
        return v
