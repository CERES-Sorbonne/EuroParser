import sys

# if sys.version_info < (3, 9):
#     from __future__ import annotations

from europarser.models import Pivot
from europarser.transformers.transformer import Transformer

import re
from datetime import datetime, date
import time
from typing import List
import json
import zipfile
import io

import pandas as pd
# import matplotlib
# matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

spaces = re.compile(r"\s+")


def clean(s: str) -> str:
    return re.sub(spaces, " ", s).strip()


def to_date(s: str) -> date:
    return datetime.strptime(s, "%Y %m %d").date()


def to_datetime(i: int) -> datetime:
    return datetime.fromtimestamp(i)


def to_monthyear(d: datetime) -> str:
    return f"{d.year}-{d.month:02}"


def make_index(data, key):
    x = sorted([(k, len(v)) for k, v in data[key].items()], key=lambda x: x[1], reverse=True)
    return {k: v for k, v in x if v}


N_TOP = 5


class StatsTransformer(Transformer):
    def __init__(self):
        super(StatsTransformer, self).__init__()
        self.sorted_months = None
        self.monthly_index_kw = None
        self.monthly_stats = None
        self.journal_stats = None
        self.index_kw = None
        self.index_data = None
        self.quick_stats = None
        self.data = None

    def transform(self, pivot_list: List[Pivot]) -> dict:
        self._logger.warning("Starting to compute stats")
        t1 = time.time()

        df = pd.DataFrame.from_records([p.dict() for p in pivot_list])

        df["journal"] = df.journal.map(clean)
        df["titre"] = df.titre.map(clean)
        df["auteur"] = df.auteur.map(clean)
        df["epoch"] = df.epoch.map(to_datetime)
        df["mois"] = df.epoch.map(to_monthyear)

        df["journal_clean"] = df.journal.str.strip()

        journaux = df.journal_clean.unique()
        mois = df.mois.unique()
        auteurs = df.auteur.unique()
        keywords = {k for ks in df.keywords.str.split(", ") for k in ks if k}

        index_journal = {
            journal: [
                e.Index for e in df[df["journal_clean"] == journal].itertuples()
            ] for journal in journaux
        }
        index_mois = {moi: [e.Index for e in df[df["mois"] == moi].itertuples()] for moi in mois}
        index_auteur = {auteur: [e.Index for e in df[df["auteur"] == auteur].itertuples()] for auteur in auteurs}

        index_journal_mois = {
            journal: {
                moi: [
                    e.Index for e in df[
                        (df["journal_clean"] == journal) & (df["mois"] == moi)
                        ].itertuples()
                ] for moi in mois
            } for journal in journaux
        }

        kw_index = {kw: [] for kw in keywords}
        for row in df.itertuples():
            for kw in row.keywords.split(", "):
                if not kw:
                    continue
                kw_index[kw].append(row.Index)

        kw_index = {kw: ls for kw, ls in kw_index.items() if ls}

        index_mois_kw = {
            moi: {
                kw: [
                    e.Index for e in df[
                        (df["mois"] == moi) & df.index.isin(kw_index[kw])].itertuples()
                ] for kw in keywords
            } for moi in mois
        }

        # index_mois_kw = {moi: {kw: e for kw, e in index_mois_kw[moi].items() if e} for moi in mois}
        # index_journal_mois = {journal: {moi: e for moi, e in index_journal_mois[journal].items() if e} for journal in journaux}

        self.data = {
            "journal": index_journal,
            "mois": index_mois,
            "auteur": index_auteur,
            "journal_mois": index_journal_mois,
            "mois_kw": index_mois_kw,
            "mot_cle": kw_index,
        }
        self._logger.warning(f"Computed stats in {time.time() - t1} s")
        return self.data

    def get_stats(self, pivot_list: List[Pivot]) -> bytes:

        if not self.data:
            self.transform(pivot_list)

        self.data["mois_kw"] = {k: {k2: v2 for k2, v2 in v.items() if v2} for k, v in self.data["mois_kw"].items()}
        self.data["journal_mois"] = {k: {k2: v2 for k2, v2 in v.items() if v2} for k, v in
                                     self.data["journal_mois"].items()}

        self.index_data = {
            k: make_index(self.data, k) for k in self.data.keys()
        }

        self.quick_stats = {
            "nb_auteurs": len(self.index_data["auteur"]),
            "nb_journaux": len(self.index_data["journal"]),
            "nb_mots_cles": len(self.index_data["mot_cle"]),
        }

        self.monthly_stats = {
            mois: {
                "nb_articles": len(self.data["mois"].get(mois, [])),
                "nb_mots_cles": self.index_data["mois_kw"].get(mois, 0),
                "nb_journaux": len([k for k, v in self.data["journal_mois"].items() if mois in v]),
                "nb_auteurs": len(
                    [e for e in self.data["auteur"].values() if any(x in self.data["mois"][mois] for x in e)]),
            } for mois in self.data["mois"].keys()
        }

        self.journal_stats = {
            journal: {
                "nb_articles": len(self.data["journal"][journal]),
                "nb_mots_cles": self.index_data["journal_mois"][journal],
                "nb_mois": len(self.data["journal_mois"][journal]),
            } for journal in self.data["journal"].keys()
        }

        self.index_kw = self.index_data["mot_cle"]

        self.monthly_index_kw = {
            mois: make_index(self.data["mois_kw"], mois) for mois in self.data["mois_kw"].keys()
        }

        self.quick_stats = pd.DataFrame(self.quick_stats, index=["Valeur"])
        self.monthly_stats = pd.DataFrame(self.monthly_stats).T
        self.journal_stats = pd.DataFrame(self.journal_stats).T
        self.index_kw = pd.DataFrame(self.index_kw, index=["Valeur"]).T
        self.monthly_index_kw = pd.DataFrame(self.monthly_index_kw)

        self.monthly_stats = self.monthly_stats.sort_index()
        self.monthly_index_kw = self.monthly_index_kw.reindex(sorted(self.monthly_index_kw.columns), axis=1)

        with io.BytesIO() as zip_io:
            with zipfile.ZipFile(zip_io, mode='w', compression=zipfile.ZIP_DEFLATED) as temp_zip:
                temp_zip.writestr('quick_stats.csv', self.quick_stats.to_csv())
                temp_zip.writestr('monthly_stats.csv', self.monthly_stats.to_csv())
                temp_zip.writestr('journal_stats.csv', self.journal_stats.to_csv())
                temp_zip.writestr('index_kw.csv', self.index_kw.to_csv())
                temp_zip.writestr('monthly_index_kw.csv', self.monthly_index_kw.to_csv())

                with io.BytesIO() as bytes_io:
                    with pd.ExcelWriter(bytes_io, engine='xlsxwriter') as writer:
                        self.quick_stats.to_excel(writer, sheet_name='quick_stats')
                        self.monthly_stats.to_excel(writer, sheet_name='monthly_stats')
                        self.journal_stats.to_excel(writer, sheet_name='journal_stats')
                        self.index_kw.to_excel(writer, sheet_name='index_kw')
                        self.monthly_index_kw.to_excel(writer, sheet_name='monthly_index_kw')

                    with temp_zip.open("stats.xlsx", "w") as f:
                        f.write(bytes_io.getvalue())
            return zip_io.getvalue()

    def get_plots(self, pivot_list: List[Pivot]) -> bytes:
        if not self.monthly_index_kw:
            self.get_stats(pivot_list)

        self.sorted_months = sorted(self.data["mois"].keys())

        with io.BytesIO() as zip_io:
            with zipfile.ZipFile(zip_io, mode='w', compression=zipfile.ZIP_DEFLATED) as temp_zip:
                for key in self.monthly_stats.keys():
                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.plot(self.sorted_months, [self.monthly_stats[key][mois] for mois in self.sorted_months])
                    ax.set_title(f"Nombre de {key[3:]} par mois")
                    ax.set_xlabel("Mois")
                    ax.set_ylabel(f"{key = }")

                    plt.xticks(rotation=45)

                    temp_bytes_io = io.BytesIO()
                    plt.savefig(temp_bytes_io, format="png")
                    temp_bytes_io.seek(0)

                    temp_zip.writestr(f'{key}.png', temp_bytes_io.getvalue())
                    plt.close()

                for rank in range(3):
                    temp_zip.writestr(f'top_{N_TOP}_kw_{rank}.png', self.plot_kw(rank))

            zip_io.seek(0)
            return zip_io.getvalue()

    def plot_kw(self, rank: int = 0) -> bytes:
        fig, ax = plt.subplots(figsize=(10, 5))

        start, end = (rank * N_TOP, (rank + 1) * N_TOP)

        for kw in self.index_kw.index[start: end]:
            ax.plot(self.sorted_months, [self.monthly_index_kw[mois][kw] for mois in self.sorted_months], label=kw)

        ax.set_title(f"Évolution des mots clés {start + 1} à {end} les plus utilisés")
        ax.set_xlabel("Mois")
        ax.set_ylabel(f"Nombre d'articles")
        plt.legend()

        plt.xticks(rotation=45)

        temp_bytes_io = io.BytesIO()
        plt.savefig(temp_bytes_io, format="png")
        temp_bytes_io.seek(0)
        plt.close()
        return temp_bytes_io.getvalue()


if __name__ == '__main__':
    import cProfile
    import pstats
    import io

    from europarser.models import Pivot

    with open("../../profiler/data/pivots_large.json", "r") as f:
        dict_ = json.load(f)
        dict_ = list(dict_.values())
        pivot_list = [Pivot(**d) for d in dict_]

    transformer = StatsTransformer()

    pr = cProfile.Profile()
    pr.enable()

    transformer.transform(pivot_list)

    pr.disable()
    s = io.StringIO()
    sortby = 'cumulative'
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats()

    print(s.getvalue())


