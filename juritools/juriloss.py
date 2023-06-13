from juritools.predict import JuriTagger
from jurispacy_tokenizer import JuriSpacyTokenizer
from flair.data import Sentence
from flair.models import SequenceTagger
import torch.nn
import torch
import numpy as np
from operator import itemgetter
from typing import Dict


class JuriLoss:
    """This class computes the loss of a court decision after it has been
       corrected by an annotator. It could be used to raise potential mistakes.
    Args:
        json_decision (Dict): annotation JSON from the mongodb SDER database
        model (SequenceTagger): Named entity recognition model trained from Flair
        tokenizer (JuriSpacyTokenizer): Tokenizer used for the predictions on court decisions
    Returns:
        loss (torch.tensor): return the loss
    """

    def __init__(
        self,
        json_decision: Dict,
        model: SequenceTagger,
        tokenizer: JuriSpacyTokenizer,
        only_model_category: bool = True,
    ):
        # Tokenize the court decision
        self.model = model
        self.tokenizer = tokenizer
        self.juritag = JuriTagger(self.tokenizer, self.model)
        self.text = json_decision["text"]
        self.flair_sentences = self.tokenizer.get_tokenized_sentences(self.text)

        # Put annotation labels on flair tokens
        gold = sorted(
            json_decision["treatments"][-1]["annotations"],
            key=itemgetter("start"),
        )
        pred = json_decision["treatments"][0]["annotations"]
        if only_model_category:
            model_category = [
                cat.split("-")[1]
                for cat in self.model.label_dictionary.get_items()
                if len(cat.split("-")) == 2 and cat.startswith("B")
            ]
            gold = [g for g in gold if g["category"] in model_category]
            pred = [p for p in pred if p["category"] in model_category]
        for sentence in self.flair_sentences:
            for token in sentence:
                for entity in gold:
                    if token.start_position == entity["start"]:
                        token.set_label("annotator", "B-" + entity["category"])
                        break
                    elif (
                        entity["start"]
                        < token.start_position
                        < entity["start"] + len(entity["text"])
                    ):
                        token.set_label("annotator", "I-" + entity["category"])
                        break
                else:
                    token.set_label("annotator", "O")

                for entity in pred:
                    if token.start_position == entity["start"]:
                        token.set_label("ner", "B-" + entity["category"])
                        break
                    elif (
                        entity["start"]
                        < token.start_position
                        < entity["start"] + len(entity["text"])
                    ):
                        token.set_label("ner", "I-" + entity["category"])
                        break
                else:
                    token.set_label("ner", "O")

    def categorical_cross_entropy(self, y_pred, y_true):
        y_true = torch.eye(len(self.model.label_dictionary.get_items()))[
            torch.LongTensor(y_true)
        ]
        y_pred = torch.clamp(torch.FloatTensor(y_pred), 1e-9, 1 - 1e-9)
        return -(y_true * torch.log(y_pred)).sum(dim=1).mean()

    def get_sentences_loss(self):
        sentences_loss = []
        for sent in self.flair_sentences:
            tag_list = [
                self.model.label_dictionary.get_idx_for_item(
                    token.get_label("annotator").value
                )
                for token in sent
            ]
            proba_list = np.zeros(
                (len(sent), len(self.model.label_dictionary.get_items()))
            )
            for i, token in enumerate(sent):
                proba_list[i][
                    self.model.label_dictionary.get_idx_for_item(
                        token.get_label("ner").value
                    )
                ] = token.get_label("ner").score
                loss_tensor = self.categorical_cross_entropy(proba_list, tag_list)
            sentences_loss.append(loss_tensor.item())

        return sentences_loss, max(sentences_loss)

    def get_document_loss(self):
        # Compute loss
        tag_list = [
            self.model.label_dictionary.get_idx_for_item(
                token.get_label("annotator").value
            )
            for sent in self.flair_sentences
            for token in sent
        ]
        proba_list = np.zeros(
            (
                sum(1 for sent in self.flair_sentences for tok in sent),
                len(self.model.label_dictionary.get_items()),
            )
        )
        i = 0
        for sent in self.flair_sentences:
            for token in sent:
                proba_list[i][
                    self.model.label_dictionary.get_idx_for_item(
                        token.get_label("ner").value
                    )
                ] = token.get_label("ner").score
                i += 1

        loss_tensor = self.categorical_cross_entropy(proba_list, tag_list)

        return loss_tensor.item()

    def get_document_loss_from_model(self):
        flair_text = Sentence(self.text, use_tokenizer=self.tokenizer)
        return self.model.predict(
            flair_text, force_token_predictions=True, return_loss=True
        )

    def get_sentences_loss_from_model(self):
        return [
            self.model.predict(sent, force_token_predictions=True, return_loss=True)
            for sent in self.flair_sentences
        ]
