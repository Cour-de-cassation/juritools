from collections import defaultdict
from strsimpy.weighted_levenshtein import WeightedLevenshtein
from scipy.spatial.distance import euclidean

AZERTY = {
    "é": [1, 2],
    "è": [1, 2],
    "ê": [1, 2],
    "ë": [1, 2],
    "ù": [1, 6],
    "û": [1, 6],
    "î": [1, 7],
    "ï": [1, 7],
    "ô": [1, 8],
    "ö": [1, 8],
    "a": [1, 0],
    "à": [1, 0],
    "â": [1, 0],
    "z": [1, 1],
    "e": [1, 2],
    "r": [1, 3],
    "t": [1, 4],
    "y": [1, 5],
    "ÿ": [1, 5],
    "u": [1, 6],
    "i": [1, 7],
    "o": [1, 8],
    "p": [1, 9],
    "q": [2, 0],
    "s": [2, 1],
    "d": [2, 2],
    "f": [2, 3],
    "g": [2, 4],
    "h": [2, 5],
    "j": [2, 6],
    "k": [2, 7],
    "l": [2, 8],
    "m": [2, 9],
    "w": [3, 0],
    "x": [3, 1],
    "c": [3, 2],
    "ç": [3, 2],
    "v": [3, 3],
    "b": [3, 4],
    "n": [3, 5],
    "ñ": [3, 5],
}

AZERTY_NO_ACCENT = {
    "a": [1, 0],
    "z": [1, 1],
    "e": [1, 2],
    "r": [1, 3],
    "t": [1, 4],
    "y": [1, 5],
    "u": [1, 6],
    "i": [1, 7],
    "o": [1, 8],
    "p": [1, 9],
    "q": [2, 0],
    "s": [2, 1],
    "d": [2, 2],
    "f": [2, 3],
    "g": [2, 4],
    "h": [2, 5],
    "j": [2, 6],
    "k": [2, 7],
    "l": [2, 8],
    "m": [2, 9],
    "w": [3, 0],
    "x": [3, 1],
    "c": [3, 2],
    "v": [3, 3],
    "b": [3, 4],
    "n": [3, 5],
}


azerty_typo_dict = defaultdict(set)

for key, value in AZERTY_NO_ACCENT.items():
    for other_key, other_value in AZERTY_NO_ACCENT.items():
        distance = euclidean(value, other_value)
        if distance <= 1 and key != other_key:
            azerty_typo_dict[key].add(other_key)


def insertion_cost(char):
    return 1.0


def deletion_cost(char):
    return 1.0


def substitution_cost(char_a, char_b):
    return 0.5 if char_b in azerty_typo_dict[char_a] else 1.0


weighted_levenshtein = WeightedLevenshtein(
    substitution_cost_fn=substitution_cost,
    insertion_cost_fn=insertion_cost,
    deletion_cost_fn=deletion_cost,
)


def azerty_levenshtein_similarity(tok1, tok2):
    """
    Inputs:
    - tok1 (str)
    - tok2 (str)
    Returns the weighted levenshtein similarity adapted to AZERTY keyboard
    """

    return 1 - (
        weighted_levenshtein.distance(tok1, tok2) / float(max(len(tok1), len(tok2)))
    )
