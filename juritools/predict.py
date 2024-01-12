import logging

import flair
from flair.data import Sentence
from flair.models import SequenceTagger

from juritools.type import NamedEntity

# Remove warning on empty Sentence from flair
logging.getLogger("flair").setLevel(logging.ERROR)


# Load NER model
def load_ner_model(path: str) -> flair.models.sequence_tagger_model.SequenceTagger:
    return SequenceTagger.load(path)


# Class JuriTagger to get statistical predictions
class JuriTagger:
    def __init__(self, tokenizer, model: SequenceTagger):
        self.tokenizer = tokenizer
        self.model = model

    def predict(
        self,
        text: str,
        mini_batch_size: int = 32,
        all_tags: bool = True,
        verbose: bool = True,
    ) -> list[Sentence]:
        """
        Inputs:
        - text: decision court on which the SequenceClassifier will make some predictions
        - mini_batch_size: size of the minibatch, usually bigger is more rapid but consume more memory
        - all_tags: get probability distribution across categories for each token
        - verbose: if True verbose is applied to the model

        Returns a generator containing flair sentences with NER predicted tags
        """

        self.text = text
        # Transform text to sentences
        self.flair_sentences = self.tokenizer.get_tokenized_sentences(self.text)

        # Make predictions
        self.model.predict(
            self.flair_sentences,
            mini_batch_size=mini_batch_size,
            return_probabilities_for_all_classes=all_tags,
            verbose=verbose,
        )

        return self.flair_sentences

    def get_entity_json_from_flair_sentences(self) -> list[NamedEntity]:
        """
        Returns a list containing dictionaries formatted to be the input of
        the class PostProcess to enhance the predictions and check irregularities.
        Built from flair sentence and span objects.
        """
        entity_spans = []
        for sent in self.flair_sentences:
            entity_spans.extend(list(sent.get_spans("ner")))
        return [
            NamedEntity(
                text=self.text[entity.start_position : entity.end_position],
                start=entity.start_position,
                end=entity.end_position,
                label=entity.tag,
                source="NER model",
                score=entity.score,
            )
            for entity in entity_spans
        ]
