"""Processor that attaches a sentiment score to a sentence

The model used is a generally a model trained on the Stanford
Sentiment Treebank or some similar dataset.  When run, this processor
attachs a score in the form of a string to each sentence in the
document.

TODO: a possible way to generalize this would be to make it a
ClassifierProcessor and have "sentiment" be an option.
"""

import stanza.models.classifier as classifier
import stanza.models.classifiers.cnn_classifier as cnn_classifier

from stanza.models.common import doc
from stanza.models.common.char_model import CharacterLanguageModel
from stanza.models.common.pretrain import Pretrain
from stanza.pipeline._constants import *
from stanza.pipeline.processor import UDProcessor, register_processor

@register_processor(SENTIMENT)
class SentimentProcessor(UDProcessor):
    # set of processor requirements this processor fulfills
    PROVIDES_DEFAULT = set([SENTIMENT])
    # set of processor requirements for this processor
    REQUIRES_DEFAULT = set([TOKENIZE])

    def _set_up_model(self, config, use_gpu):
        # get pretrained word vectors
        self._pretrain = Pretrain(config['pretrain_path'])
        forward_charlm_path = config.get('forward_charlm_path', None)
        charmodel_forward = CharacterLanguageModel.load(forward_charlm_path, finetune=False) if forward_charlm_path else None
        backward_charlm_path = config.get('backward_charlm_path', None)
        charmodel_backward = CharacterLanguageModel.load(backward_charlm_path, finetune=False) if backward_charlm_path else None

        elmo_path = config.get('elmo_path', None)
        if elmo_path is not None:
            # TODO: remove this so we can remove the import of classifier.py
            elmo_model = classifier.load_elmo(elmo_path)
        else:
            elmo_model = None

        # set up model
        self._model = cnn_classifier.load(filename=config['model_path'],
                                          pretrain=self._pretrain,
                                          elmo_model=elmo_model,
                                          charmodel_forward=charmodel_forward,
                                          charmodel_backward=charmodel_backward)
        self._batch_size = config.get('batch_size', None)

        # TODO: move this call to load()
        if use_gpu:
            self._model.cuda()

    def process(self, document):
        sentences = document.sentences
        text = [" ".join(token.text for token in sentence.tokens) for sentence in sentences]
        labels = cnn_classifier.label_text(self._model, text, batch_size=self._batch_size)
        # TODO: allow a classifier processor for any attribute, not just sentiment
        document.set(SENTIMENT, labels, to_sentence=True)
        return document
