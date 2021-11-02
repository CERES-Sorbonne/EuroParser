import re
from typing import Tuple

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


def find_date(txt: str) -> Tuple[str, str, str]:
    """
    Utility function to extract a date from a given string
    :return: a 3 strings tuple: day number, month, year
    """
    day = month = year = ""
    match = None
    index = 0
    while not match and index < len(date_regex):
        match = date_regex[index].search(txt)
        index += 1
    if not match:
        print("No valid date was found for " + txt)
    else:
        match = match[0]
        index -= 1

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
    return day, month, year
