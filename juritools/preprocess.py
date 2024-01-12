from jurispacy_tokenizer import JuriSpacyTokenizer
from flair.models import SequenceTagger
from flair.data import Sentence

from typing import Any

from juritools.type import Decision, JuricaPartie, JuriTJPartie, DecisionSourceNameEnum, TypePartie

import pandas as pd


def replace_specific_encoding(text):
    """Replace End of Line tokens"""
    return text.replace("\f", "\n").replace("\r", "\n")


class PreProcess:
    """Class in charge of preprocessing work"""

    def __init__(
        self,
        decision: Decision,
        tokenizer: JuriSpacyTokenizer,
        model: SequenceTagger,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.decision = decision
        self.text = replace_specific_encoding(decision.text)
        if decision.parties:
            if decision.sourceName == DecisionSourceNameEnum.jurinet:
                self._preprocess_jurinet_metadata(metadata=decision.parties)
            elif decision.sourceName == DecisionSourceNameEnum.jurica:
                self._preprocess_jurica_metadata(metadata=decision.parties)
            elif decision.sourceName == DecisionSourceNameEnum.juritj:
                self._preprocess_juritj_metadata(metadata=decision.parties)
            else:
                # the following will raise a ValidationError
                DecisionSourceNameEnum(decision.sourceName)
        else:
            self.metadata = None

    def _preprocess_jurinet_metadata(self, metadata: list[list[Any]]):
        """Preprocesses JURINET metadata

        Args:
            metadata (list[list[Any]]): list of parties
        """
        col_list = [
            "ID_DOCUMENT",
            "TYPE_PERSONNE",
            "ID_PARTIE",
            "NATURE_PARTIE",
            "TYPE_PARTIE",
            "ID_TITRE",
            "NOM",
            "PRENOM",
            "NOM_MARITAL",
            "AUTRE_PRENOM",
            "ALIAS",
            "SIGLE",
            "DOMICILIATION",
            "LIG_ADR1",
            "LIG_ADR2",
            "LIG_ADR3",
            "CODE_POSTAL",
            "NOM_COMMUNE",
            "NUMERO",
        ]
        self.metadata = pd.DataFrame(
            metadata,
            columns=col_list,
        )

    def _preprocess_jurica_metadata(self, metadata: list[JuricaPartie]):
        """Preprocesses JURICA metdata

        Args:
            metadata (list[JuricaPartie]): list of parties
        """
        # tokenizing parties
        flair_sentences = [
            Sentence(
                partie.identite,
                use_tokenizer=self.tokenizer,
            )
            for partie in metadata
            if partie.attributes.typePersonne == TypePartie.personne_phyisque
        ]
        
        self.metadata = self._parse_metadata(sentences=flair_sentences) 

    def _preprocess_juritj_metadata(self, metadata: list[JuriTJPartie]):
        """Preprocesses JURITJ metadata

        Args:
            metadata (list[JuriTJPartie]): list of parties
        """
        # tokenizing parties
        flair_sentences = [
            Sentence(
                f"{partie.civilite} {partie.prenom} {partie.nom}",
                use_tokenizer=self.tokenizer,
            )
            for partie in metadata
            if partie.type == TypePartie.personne_phyisque
        ]

        self.metadata = self._parse_metadata(sentences=flair_sentences) 

    def _parse_metadata(self, sentences: list[Sentence]) -> pd.DataFrame:
        """Parses flair sentences to get a pd.DataFrame of personnePhysique entities"""
        # predicting partie nature
        self.model.predict(sentences, verbose=False)
        metadata_entities = []

        for sent in sentences:
            for span in sent.get_spans(type="ner"):
                if span.get_label("ner").value in ["personnePhysique"]:
                    metadata_entities.append(
                        {
                            "text": span.text,
                            "entity": span.get_label("ner").value,
                        },
                    )
        return pd.DataFrame(metadata_entities).drop_duplicates()