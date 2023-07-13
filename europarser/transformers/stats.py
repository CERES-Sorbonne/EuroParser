import pandas as pd
import re
from datetime import datetime, date
from typing import List

from europarser.models import Pivot
from europarser.transformers.transformer import Transformer


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s)


def to_date(s: str) -> date:
    return datetime.strptime(s, "%Y %m %d").date()


def to_monthyear(d: datetime) -> str:
    return f"{d.month}-{d.year}"


class StatsTransformer(Transformer):
    def __init__(self):
        super(StatsTransformer, self).__init__()

    def transform(self, pivot_list: List[Pivot]) -> dict:
        df = pd.DataFrame.from_records([p.dict() for p in pivot_list])

        df["journal"] = df.journal.map(clean)
        df["titre"] = df.titre.map(clean)
        df["date"] = df.date.apply(to_date)
        df["mois"] = df.date.apply(to_monthyear)

        journaux = df.journal_clean.unique()
        mois = df.mois.unique()
        auteurs = df.auteur.unique()
        keywords = {k for ks in df.keywords.str.split(", ") for k in ks}

        index_journal = {journal: [e.Index for e in df[df["journal_clean"] == journal].itertuples()] for journal in
                         journaux}
        index_mois = {moi: [e.Index for e in df[df["mois"] == moi].itertuples()] for moi in mois}
        index_auteur = {auteur: [e.Index for e in df[df["auteur"] == auteur].itertuples()] for auteur in auteurs}

        index_journal_mois = {
            journal: {moi: [e.Index for e in df[(df["journal_clean"] == journal) & (df["mois"] == moi)].itertuples()]
                      for moi in mois} for journal in journaux}

        kw_index = {kw: [] for kw in keywords}
        for row in df.itertuples():
            for kw in row.keywords.split(", "):
                kw_index[kw].append(row.Index)

        index_mois_kw = {
            moi: {kw: [e.Index for e in df[(df["mois"] == moi) & df.index.isin(kw_index[kw])].itertuples()] for kw in
                  keywords} for moi in mois}

        # index_mois_kw = {moi: {kw: e for kw, e in index_mois_kw[moi].items() if e} for moi in mois}
        # index_journal_mois = {journal: {moi: e for moi, e in index_journal_mois[journal].items() if e} for journal in journaux}

        return {
            "journal": index_journal,
            "mois": index_mois,
            "auteur": index_auteur,
            "journal_mois": index_journal_mois,
            "mois_kw": index_mois_kw,
        }
