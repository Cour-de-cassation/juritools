from flashtext import KeywordProcessor

def instantiate_flashtext(case_sensitive: bool):
    non_word_boundary_list = [
        "@",
        "é",
        "è",
        "ê",
        "ù",
        "û",
        "î",
        "ï",
        "ö",
        "ô",
        "É",
        "È",
        "Ê",
        "Î",
        "Ï",
        "Ö",
        "Ô",
        "Ú",
        "Û",
        "Ù",
        "Ü",
    ]
    keyword_processor = KeywordProcessor(case_sensitive)
    for non_word in non_word_boundary_list:
        keyword_processor.add_non_word_boundary(non_word)
    return keyword_processor