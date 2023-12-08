import sys

# if sys.version_info < (3, 9):
#     from __future__ import annotations

import re
from europarser.utils import STOP_WORDS


def filter_KW(liste):
    out = set()
    liste = set(liste).difference(STOP_WORDS)
    for x in liste:
        numbers = re.findall("[0-9]", x)
        if x.lower() in STOP_WORDS:
            continue
        elif len(x) < 2:
            continue
        elif len(re.findall("[A-Za-z]", x)) == 0:
            continue
        elif len(numbers) > 0:
            if len(numbers[0]) == len(x):
                continue
        out.add(x.lower().replace(',', '').strip())
    return out


def tokenize(chaine):
    chaine = re.sub(r"\.|'|\?|»|«|\"", " ", chaine)
    chaine = re.sub(" {2,}", " ", chaine)
    mots = chaine.split()
    return mots


def is_subsequence(needle, haystack):
    return any(haystack[i:i + len(needle)] == needle
               for i in range(len(haystack) - len(needle) + 1))


def get_ngrams(inter, word_titre, word_body):
    selected = [x for x in inter]
    haystack = [x.lower() for x in word_body]
    for i, word in enumerate(word_titre):
        if word in inter or word.lower() in inter:
            n_gram = [word]
            last = i
            for j, w in enumerate(word_titre[i + 1:]):
                if w in inter:
                    last = j
                n_gram.append(w)
            if len(n_gram) > 1 and len(n_gram) < 5 and last != i:
                needle = [x.lower() for x in n_gram]
                if is_subsequence(needle, haystack):
                    selected.append("_".join(n_gram[:last + 2]))
    ## TODO: régler le problème des n-grammes
    ##  if "gilets" in haystack and "jaunes in haystack":
    ##    if "gilets_jaunes" not in selected:
    ##      print(selected)
    ##      x = haystack.index("gilets")
    ##      print(haystack[x:x+10])
    ##      print(word_titre[word_titre.index("gilets"):])
    return selected


def get_KW(titre, text):
    body = text
    chapeau = ""
    if len(titre) < 100:
        chapeau = text[:200]
        body = text[200:]
    word_titre = set(tokenize(titre) + tokenize(chapeau))
    word_body = set(tokenize(body))
    inter = word_titre.intersection(word_body)
    inter = filter_KW(inter)
    inter = get_ngrams(inter, tokenize(titre), tokenize(body))
    return inter
