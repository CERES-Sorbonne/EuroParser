from europarser.models import Pivot
from europarser.transformers.transformer import Transformer

import re
from datetime import datetime, date
from typing import List
import json
import zipfile
import io

import pandas as pd


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def to_date(s: str) -> date:
    return datetime.strptime(s, "%Y %m %d").date()


def to_monthyear(d: datetime) -> str:
    return f"{d.month}-{d.year}"


def make_index(data, key):
    x = sorted([(k, len(v)) for k, v in data[key].items()], key=lambda x: x[1], reverse=True)
    return {k: v for k, v in x if v}


class StatsTransformer(Transformer):
    def __init__(self):
        super(StatsTransformer, self).__init__()

    def transform(self, pivot_list: List[Pivot]) -> dict:
        df = pd.DataFrame.from_records([p.dict() for p in pivot_list])

        df["journal"] = df.journal.map(clean)
        df["titre"] = df.titre.map(clean)
        df["auteur"] = df.auteur.map(clean)
        df["date"] = df.date.apply(to_date)
        df["mois"] = df.date.apply(to_monthyear)

        df["journal_clean"] = df.journal.str.strip()

        journaux = df.journal_clean.unique()
        mois = df.mois.unique()
        auteurs = df.auteur.unique()
        keywords = {k for ks in df.keywords.str.split(", ") for k in ks if k}

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
                if not kw:
                    continue
                kw_index[kw].append(row.Index)

        kw_index = {kw: ls for kw, ls in kw_index.items() if ls}

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
            "mot_cle": kw_index,
        }




    def get_stats(self, pivot_list: List[Pivot]) -> bytes:
        data = self.transform(pivot_list)

        data["mois_kw"] = {k: {k2: v2 for k2, v2 in v.items() if v2} for k, v in data["mois_kw"].items()}
        data["journal_mois"] = {k: {k2: v2 for k2, v2 in v.items() if v2} for k, v in data["journal_mois"].items()}
        index_data = {
            k: make_index(data, k) for k in data.keys()
        }
        quick_stats = {
            "nb_auteurs": len(index_data["auteur"]),
            "nb_journaux": len(index_data["journal"]),
            "nb_mots_cles": len(index_data["mot_cle"]),
        }

        monthly_stats = {
            mois: {
                "nb_articles": len(data["mois"][mois]),
                "nb_mots_cles": index_data["mois_kw"][mois],
                "nb_journaux": len(data["mois"][mois]),
            } for mois in data["mois"].keys()
        }

        journal_stats = {
            journal: {
                "nb_articles": len(data["journal"][journal]),
                "nb_mots_cles": index_data["journal_mois"][journal],
                "nb_mois": len(data["journal_mois"][journal]),
            } for journal in data["journal"].keys()
        }

        index_kw = index_data["mot_cle"]

        monthly_index_kw = {
            mois: make_index(data["mois_kw"], mois) for mois in data["mois_kw"].keys()
        }
        quick_stats = pd.DataFrame(quick_stats, index=["Valeur"])
        monthly_stats = pd.DataFrame(monthly_stats).T
        journal_stats = pd.DataFrame(journal_stats).T
        index_kw = pd.DataFrame(index_kw, index=["Valeur"]).T
        monthly_index_kw = pd.DataFrame(monthly_index_kw)

        with io.BytesIO() as zip_io:
            with zipfile.ZipFile(zip_io, mode='w', compression=zipfile.ZIP_DEFLATED) as temp_zip:
                temp_zip.writestr('quick_stats.csv', quick_stats.to_csv())
                temp_zip.writestr('monthly_stats.csv', monthly_stats.to_csv())
                temp_zip.writestr('journal_stats.csv', journal_stats.to_csv())
                temp_zip.writestr('index_kw.csv', index_kw.to_csv())
                temp_zip.writestr('monthly_index_kw.csv', monthly_index_kw.to_csv())

                with io.BytesIO() as bytes_io:
                    with pd.ExcelWriter(bytes_io, engine='xlsxwriter') as writer:
                        quick_stats.to_excel(writer, sheet_name='quick_stats')
                        monthly_stats.to_excel(writer, sheet_name='monthly_stats')
                        journal_stats.to_excel(writer, sheet_name='journal_stats')
                        index_kw.to_excel(writer, sheet_name='index_kw')
                        monthly_index_kw.to_excel(writer, sheet_name='monthly_index_kw')

                    with temp_zip.open("stats.xlsx", "w") as f:
                        f.write(bytes_io.getvalue())
            return zip_io.getvalue()
