import py3langid


def detect_lang(text: str) -> str:
    return py3langid.classify(text)[0]
