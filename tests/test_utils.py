from juritools.utils import deaccent


def test_deacccent():
    text = "½ û œ 1 སྒྱ ÀÁÂÃÄàáâãäÈÉÊËèéêëÍÌÎÏíìîïÒÓÔÕÖòóôõöÙÚÛÜùúûüÑñÇç§³²¹…"
    deaccent_text = deaccent(text)

    assert deaccent_text == "½ u œ 1 སྒྱ AAAAAaaaaaEEEEeeeeIIIIiiiiOOOOOoooooUUUUuuuuNnCc§³²¹…"
    assert len(text) == len(deaccent_text)
