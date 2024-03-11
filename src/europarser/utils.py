import hashlib
import json
import sys

# if sys.version_info < (3, 9):
#     from __future__ import annotations

import re
from pathlib import Path
from typing import Tuple, Optional
from datetime import date, datetime
from dateutil import tz as tzutil

from .models import Pivot

date_regex = [
    find_french_date_1 := re.compile(
        r"(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche) [0-9]+ (?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre) [0-9]{4}"),
    find_french_date_2 := re.compile(r'\d{1,2}\s\w+\s\d{4}'),
    find_english_date_1 := re.compile(r'\w+,\s?\w+\s\d{1,2},\s?\d{4}'),
    find_english_date_2 := re.compile(r'\w+\s\d{1,2},\s?\d{4}')
]
dic_months = {"janvier": "01", "février": "02", "mars": "03", "avril": "04", "mai": "05", "juin": "06", "juillet": "07",
              "août": "08", "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12"}
trad_months = {"January": "janvier", "February": "février", "March": "mars", "April": "avril", "May": "mai",
               "June": "juin", "July": "juillet", "August": "août", "September": "septembre", "October": "octobre",
               "November": "novembre", "December": "décembre"}
time_regex = re.compile(r'\d{1,2}:\d{1,2}(?::\d{1,2})?(?:\s?[ap]\.?m\.?)?(?:\s?[GU][MT][TC]\s[+-]\d{1,2})?')


def find_date(txt: [str]) -> Optional[date]:
    """
    Utility function to extract a date from aa given string
    :return: a date object with the date
    """
    day = month = year = ""
    index = 0
    final_month = None
    while index < len(date_regex) and final_month not in dic_months:
        match = date_regex[index].search(txt)
        if match:
            match = match[0]

            if date_regex[index] is find_french_date_1:
                _, day, month, year = match.split()

            elif date_regex[index] is find_french_date_2:
                day, month, year = match.split()

            elif date_regex[index] is find_english_date_1:
                _, month, year = match.split(',')
                month, day = month.strip().split()
                month = trad_months[month]

            elif date_regex[index] is find_english_date_2:
                month_day, year = match.split(',')
                month, day = month_day.split(' ')
                month = trad_months[month]

            day, month, year = [x.strip() for x in [day, month, year]]
            final_month = month
            index += 1
        else:
            index += 1

    if final_month not in dic_months:
        print("No valid date was found for " + txt)
        # return "", "", ""
        return None
    else:
        if len(day) == 1:
            day = "0" + day
        real_month = dic_months[final_month]
        # return day, real_month, year
        return date(int(year), int(real_month), int(day))


def find_datetime(txt: [str]) -> Optional[datetime]:
    """
    Utility function to extract date and time from a given string
    :return: a datetime object with the date and time
    """

    day = month = year = hour = minute = second = ""
    index = 0
    final_month = tz = None

    while index < len(date_regex) and final_month not in dic_months:
        match = date_regex[index].search(txt)
        if match:
            match = match[0]

            if date_regex[index] is find_french_date_1:
                _, day, month, year = match.split()

            elif date_regex[index] is find_french_date_2:
                day, month, year = match.split()

            elif date_regex[index] is find_english_date_1:
                _, month, year = match.split(',')
                month, day = month.strip().split()
                month = trad_months[month]

            elif date_regex[index] is find_english_date_2:
                month_day, year = match.split(',')
                month, day = month_day.split(' ')
                month = trad_months[month]

            day, month, year = [x.strip() for x in [day, month, year]]
            final_month = month
            index += 1
        else:
            index += 1

    if final_month not in dic_months:
        print("No valid date was found for " + txt)
        return None
    else:
        if len(day) == 1:
            day = "0" + day
        real_month = dic_months[final_month]
        # return day, real_month, year

    match = time_regex.search(txt)
    file = open("test.txt", "a")
    if match:
        print(f"Found time {match[0]} in {txt}", file=file)
        match = match[0]
        if ":" in match:
            parts = match.split(":")

            if len(parts) == 2:
                hour, minute = parts
                minute = minute.split()[0]
            elif len(parts) == 3:
                hour, minute, second = parts
                second = second.split()[0]
        else:
            hour = match.split()[0]
            minute = "00"
            second = "00"

        if "p" in match.lower():
            hour = str(int(hour) + 12)
        elif "a" in match.lower():
            hour = str(int(hour) + 12)

        hour, minute, second = [x.strip() for x in [hour, minute, second]]

        if "+" in match:
            tz = f"UTC+{match.split('+')[1]}:00"
        elif "-" in match:
            tz = f"UTC-{match.split('-')[1]}:00"

        tz = tzutil.gettz(tz)  # if tz is None, gettz() returns tzlocal()

        if not second:
            second = 0

        try:
            assert int(hour) < 24
            assert int(minute) < 60
            assert int(second) < 60
        except AssertionError:
            raise

        dt = datetime(int(year), int(real_month), int(day), int(hour), int(minute), int(second), tzinfo=tz)
    else:
        print(f"No time found in {txt}", file=file)
        # dt = datetime(int(year), int(real_month), int(day))
        dt = datetime(int(year), int(real_month), int(day), tzinfo=tz)

    file.close()
    return dt


STOP_WORDS = [
    "ans", "faire", "a", "abord", "absolument", "afin", "ah", "ai", "aie", "aient", "aies", "ailleurs",
    "ainsi", "ait",
    "allaient", "allo", "allons", "allô", "alors", "anterieur", "anterieure", "anterieures", "apres", "après",
    "as",
    "assez", "attendu", "au", "aucun", "aucune", "aucuns", "aujourd", "aujourd'hui", "aupres", "auquel",
    "aura", "aurai",
    "auraient", "aurais", "aurait", "auras", "aurez", "auriez", "aurions", "aurons", "auront", "aussi",
    "autant", "autre",
    "autrefois", "autrement", "autres", "autrui", "aux", "auxquelles", "auxquels", "avaient", "avais",
    "avait", "avant",
    "avec", "avez", "aviez", "avions", "avoir", "avons", "ayant", "ayez", "ayons", "b", "bah", "bas", "basee",
    "bat", "beau", "beaucoup",
    "bien", "bigre", "bon", "boum", "bravo", "brrr", "c", "car", "ce", "ceci", "cela", "celle", "celle-ci",
    "celle-là", "celles", "celles-ci",
    "celles-là", "celui", "celui-ci", "celui-là", "celà", "cent", "cependant", "certain", "certaine",
    "certaines", "certains", "certes", "ces",
    "cet", "cette", "ceux", "ceux-ci", "ceux-là", "chacun", "chacune", "chaque", "cher", "chers", "chez",
    "chiche", "chut", "chère", "chères", "ci",
    "cinq", "cinquantaine", "cinquante", "cinquantième", "cinquième", "clac", "clic", "combien", "comme",
    "comment", "comparable", "comparables", "compris", "concernant",
    "contre", "couic", "crac", "d", "da", "dans", "de", "debout", "dedans", "dehors", "deja", "delà",
    "depuis", "dernier", "derniere", "derriere", "derrière", "des",
    "desormais", "desquelles", "desquels", "dessous", "dessus", "deux", "deuxième", "deuxièmement", "devant",
    "devers", "devra", "devrait",
    "different", "differentes", "differents", "différent", "différente", "différentes", "différents", "dire",
    "directe", "directement",
    "dit", "dite", "dits", "divers", "diverse", "diverses", "dix", "dix-huit", "dix-neuf", "dix-sept",
    "dixième", "doit", "doivent",
    "donc", "dont", "dos", "douze", "douzième", "dring", "droite", "du", "duquel", "durant", "dès", "début",
    "désormais", "e", "effet",
    "egale", "egalement", "egales", "eh", "elle", "elle-même", "elles", "elles-mêmes", "en", "encore",
    "enfin", "entre", "envers",
    "environ", "es", "essai", "est", "et", "etant", "etc", "etre", "eu", "eue", "eues", "euh", "eurent",
    "eus", "eusse", "eussent",
    "eusses", "eussiez", "eussions", "eut", "eux", "eux-mêmes", "exactement", "excepté", "extenso",
    "exterieur", "eûmes", "eût", "eûtes",
    "f", "fais", "faisaient", "faisant", "fait", "faites", "façon", "feront", "fi", "flac", "floc", "fois",
    "font", "force", "furent", "fus", "fusse",
    "fussent", "fusses", "fussiez", "fussions", "fut", "fûmes", "fût", "fûtes", "g", "gens", "h", "ha",
    "haut", "hein", "hem", "hep", "hi", "ho", "holà",
    "hop", "hormis", "hors", "hou", "houp", "hue", "hui", "huit", "huitième", "hum", "hurrah", "hé", "hélas",
    "i", "ici", "il", "ils", "importe", "j", "je",
    "jusqu", "jusque", "juste", "k", "l", "la", "laisser", "laquelle", "las", "le", "lequel", "les",
    "lesquelles", "lesquels", "leur", "leurs", "longtemps",
    "lors", "lorsque", "lui", "lui-meme", "lui-même", "là", "lès", "m", "ma", "maint", "maintenant", "mais",
    "malgre", "malgré", "maximale", "me", "meme",
    "memes", "merci", "mes", "mien", "mienne", "miennes", "miens", "mille", "mince", "mine", "minimale",
    "moi", "moi-meme", "moi-même", "moindres", "moins",
    "mon", "mot", "moyennant", "multiple", "multiples", "même", "mêmes", "n", "na", "naturel", "naturelle",
    "naturelles", "ne", "neanmoins", "necessaire",
    "necessairement", "neuf", "neuvième", "ni", "nombreuses", "nombreux", "nommés", "non", "nos", "notamment",
    "notre", "nous", "nous-mêmes", "nouveau",
    "nouveaux", "nul", "néanmoins", "nôtre", "nôtres", "o", "oh", "ohé", "ollé", "olé", "on", "ont", "onze",
    "onzième", "ore", "ou", "ouf", "ouias", "oust",
    "ouste", "outre", "ouvert", "ouverte", "ouverts", "o|", "où", "p", "paf", "pan", "par", "parce",
    "parfois", "parle", "parlent", "parler", "parmi",
    "parole", "parseme", "partant", "particulier", "particulière", "particulièrement", "pas", "passé",
    "pendant", "pense", "permet", "personne",
    "personnes", "peu", "peut", "peuvent", "peux", "pff", "pfft", "pfut", "pif", "pire", "pièce", "plein",
    "plouf", "plupart", "plus", "plusieurs",
    "plutôt", "possessif", "possessifs", "possible", "possibles", "pouah", "pour", "pourquoi", "pourrais",
    "pourrait", "pouvait", "prealable",
    "precisement", "premier", "première", "premièrement", "pres", "probable", "probante", "procedant",
    "proche", "près", "psitt", "pu", "puis", "puisque",
    "pur", "pure", "q", "qu", "quand", "quant", "quant-à-soi", "quanta", "quarante", "quatorze", "quatre",
    "quatre-vingt", "quatrième", "quatrièmement", "que",
    "quel", "quelconque", "quelle", "quelles", "quelqu'un", "quelque", "quelques", "quels", "qui",
    "quiconque", "quinze", "quoi", "quoique", "r", "rare",
    "rarement", "rares", "relative", "relativement", "remarquable", "rend", "rendre", "restant", "reste",
    "restent", "restrictif", "retour", "revoici",
    "revoilà", "rien", "s", "sa", "sacrebleu", "sait", "sans", "sapristi", "sauf", "se", "sein", "seize",
    "selon", "semblable", "semblaient", "semble",
    "semblent", "sent", "sept", "septième", "sera", "serai", "seraient", "serais", "serait", "seras", "serez",
    "seriez", "serions", "serons", "seront",
    "ses", "seul", "seule", "seulement", "si", "sien", "sienne", "siennes", "siens", "sinon", "six",
    "sixième", "soi", "soi-même", "soient", "sois",
    "soit", "soixante", "sommes", "son", "sont", "sous", "souvent", "soyez", "soyons", "specifique",
    "specifiques", "speculatif", "stop", "strictement",
    "subtiles", "suffisant", "suffisante", "suffit", "suis", "suit", "suivant", "suivante", "suivantes",
    "suivants", "suivre", "sujet", "superpose",
    "sur", "surtout", "t", "ta", "tac", "tandis", "tant", "tardive", "te", "tel", "telle", "tellement",
    "telles", "tels", "tenant", "tend", "tenir",
    "tente", "tes", "tic", "tien", "tienne", "tiennes", "tiens", "toc", "toi", "toi-même", "ton", "touchant",
    "toujours", "tous", "tout", "toute",
    "toutefois", "toutes", "treize", "trente", "tres", "trois", "troisième", "troisièmement", "trop", "très",
    "tsoin", "tsouin", "tu", "té", "u", "un",
    "une", "unes", "uniformement", "unique", "uniques", "uns", "v", "va", "vais", "valeur", "vas", "vers",
    "via", "vif", "vifs", "vingt", "vivat",
    "vive", "vives", "vlan", "voici", "voie", "voient", "voilà", "voire", "vont", "vos", "votre", "vous",
    "vous-mêmes", "vu", "vé", "vôtre", "vôtres",
    "w", "x", "y", "z", "zut", "à", "â", "ça", "ès", "étaient", "étais", "était", "étant", "état", "étiez",
    "étions", "été", "étée", "étées", "étés", "êtes", "être", "ô",
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "has", "her", "his", "if", "in",
    "into", "is", "it", "no",
    "not", "of", "on", "or", "such", "that", "the", "their", "then", "there", "these", "they", "this", "to",
    "was", "will", "with"
]

