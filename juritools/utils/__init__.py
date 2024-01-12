from .readers import xml_jurinet_reader, html_jurica_reader
from .instantiate_flashtext import instantiate_flashtext
from .deaccent import deaccent
from .azertypo import azerty_levenshtein_similarity
from .is_punctuation import is_punctuation
import logging.config

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)-15s %(message)s",
                "datefmt": "%Y-%m-%d %H:%M",
            }
        },
        "handlers": {
            "console": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            }
        },
        "loggers": {
            "openjustice": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            }
        },
        "root": {"handlers": ["console"], "level": "WARNING"},
    }
)

logger = logging.getLogger("openjustice")
