import re


def deaccent(text):
    """Remove letter accents from the given string.
    Parameters
    ----------
    text : str
        Input string.
    Returns
    -------
    str
        Unicode string without accents.
    Examples
    --------
        >>> from juritools.utils import deaccent
        >>> deaccent("ÀÁÂÃÄàáâãäÈÉÊËèéêëÍÌÎÏíìîïÒÓÔÕÖòóôõöÙÚÛÜùúûüÑñÇç")
        u'AAAAAaaaaaEEEEeeeeIIIIiiiiOOOOOoooooUUUUuuuuNnCc'
    """
    mapping = {
        "A": "ÀÁÂÃÄÅÆ",
        "C": "Ç",
        "E": "ÈÉÊË",
        "I": "ÌÍÎÏ",
        "N": "Ñ",
        "O": "ÒÓÔÕÖ",
        "U": "ÙÚÛÜ",
        "Y": "Ý",
        "a": "àáâãäåæ",
        "c": "ç",
        "e": "èéêë",
        "i": "ìíîï",
        "n": "ñ",
        "o": "òóôõö",
        "u": "ùúûüũ",
        "y": "ýŷÿ",
    }
    if not isinstance(text, str):
        # assume utf8 for byte strings, use default (strict) error handling
        text = text.decode("utf8")
    for letter, letter_accent in mapping.items():
        text = re.sub(rf"[{letter_accent}]", letter, text)
    return text
