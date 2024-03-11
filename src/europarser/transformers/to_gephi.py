from typing import List

from ..models import Pivot
from ..transformers.transformer import Transformer

import pandas as pd


class GephiTransformer(Transformer):
    def __init__(self):
        super(GephiTransformer, self).__init__()

    def transform(self, pivot_list: List[Pivot], graph_type="skeletton") -> str:
        keyword_to_authors = {}
        res = "Source;Target;edge_label"
        for pivot in pivot_list:
            for keyword in pivot.keywords.split(','):
                if keyword.strip() == "":
                    continue
                keyword_to_authors[keyword] = keyword_to_authors.get(keyword, set())
                keyword_to_authors[keyword].add(pivot.auteur)
        # pour chaque mot clé
        for keyword, author_list in keyword_to_authors.items():
            # pour chaque auteur de la liste des auteurs
            for index in range(len(list(author_list))):
                author = list(author_list)[index]
                if author.lower() != "unknown":
                    # ce code là sert pour créer des liens entre auteurs, les résultats ne sont pas probants
                    # # pour chaque autre auteur de la liste des auteurs
                    # for sub_index, author in enumerate(list(author_list)[index:]):
                    #     if sub_index < len(list(author_list)[index:]) - 2:
                    #         # on créé un lien
                    #         res += f"\n{author};{list(author_list)[sub_index + 1]};{keyword}"
                    # celui ci pour créer des liens auteur -> mot clé
                    res += f"\n{author.lower()};{keyword};aucun"

        return res
        # code pour le graphe temporel si on le fait un jour
        # pivot_list.sort(key=lambda x: x.date)
        # first_date = pivot_list[0].date
        # last_date = pivot_list[-1].date

        # return df.to_csv(sep=",", index=False)
