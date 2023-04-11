import langid


def detect_lang(text):
    return langid.classify(text)[0]
