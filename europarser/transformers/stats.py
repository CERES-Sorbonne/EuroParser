import json
from collections import defaultdict

import pandas as pd
import re
from datetime import datetime, date
import time
import zipfile
import io
from matplotlib import pyplot as plt

N_TOP = 5


class StatsTransformer:
    @staticmethod
    def clean(s: str) -> str:
        return re.sub(r"\s+", " ", s).strip()

    @staticmethod
    def to_date(s: str) -> date:
        return datetime.strptime(s, "%Y %m %d").date()

    @staticmethod
    def to_monthyear(d: datetime) -> str:
        return f"{d.year}-{d.month:02}"

    @staticmethod
    def int_to_datetime(i: int) -> datetime:
        return datetime.fromtimestamp(i)

    def int_to_monthyear(self, i: int) -> str:
        # return self.to_monthyear(self.int_to_datetime(i))
        dt = datetime.fromtimestamp(i)
        return f"{dt.year}-{dt.month:02}"

    def int_to_monthyear_intversion(self, i: int) -> int:
        dt = datetime.fromtimestamp(i)
        return dt.year * 100 + dt.month  # --> int(f"{dt.year}{dt.month:02}") equivalent

    def __init__(self):
        self.data = None

    def transform(self, pivot_list):
        self.data = {}  # defaultdict(set)

        df = pd.DataFrame.from_records([p.dict() for p in pivot_list])

        df['journal_clean'] = df['journal'].str.strip()
        df['mois'] = df['epoch'].map(self.int_to_monthyear_intversion)

        # journaux = df['journal_clean'].unique()
        # mois = df['mois'].unique()
        # auteurs = df['auteur'].unique()

        df['keywords'] = df['keywords'].str.split(", ")
        keywords = set(k for ks in df['keywords'] for k in ks)

        df['Index'] = df.index

        self.data["journal"] = {
            journal: list(group['Index'])
            for journal, group in df.groupby('journal_clean')
        }

        self.data["mois"] = {
            mois_val: list(group['Index'])
            for mois_val, group in df.groupby('mois')
        }

        self.data["auteur"] = {
            auteur: list(group['Index'])
            for auteur, group in df.groupby('auteur')
        }

        self.data["mot_cle"] = {}
        for kw in keywords:
            self.data["mot_cle"][kw] = list(df[df['keywords'].apply(lambda x: kw in x)]['Index'])

        self.data["journal_mois"] = {
            journal: {
                mois_val: list(group['Index'])
                for mois_val, group in group_df.groupby('mois')
            }
            for journal, group_df in df.groupby('journal_clean')
        }

        self.data["mois_kw"] = {}
        for mois_val, group_df in df.groupby('mois'):
            month_keywords = defaultdict(list)
            for _, row in group_df.iterrows():
                for kw in row['keywords']:
                    month_keywords[kw].append(row['Index'])
            self.data["mois_kw"][mois_val] = month_keywords

        return self.data

    def get_stats(self, pivot_list):
        if not self.data:
            self.transform(pivot_list)

        self.data["mot_cle"] = {k: v for k, v in self.data["mot_cle"].items() if v}
        self.data["mois_kw"] = {k: {k2: v2 for k2, v2 in v.items() if v2} for k, v in self.data["mois_kw"].items()}
        self.data["journal_mois"] = {k: {k2: v2 for k2, v2 in v.items() if v2} for k, v in
                                     self.data["journal_mois"].items()}

        index_data = {k: {key: len(val) for key, val in v.items()} for k, v in self.data.items()}
        self.data.update(index_data)

        self.data["mois_kw"] = {k: {k2: len(v2) for k2, v2 in v.items()} for k, v in self.data["mois_kw"].items()}
        self.data["journal_mois"] = {k: {k2: len(v2) for k2, v2 in v.items()} for k, v in
                                     self.data["journal_mois"].items()}

        self.data["quick_stats"] = {
            "nb_auteurs": len(self.data["auteur"]),
            "nb_journaux": len(self.data["journal"]),
            "nb_mots_cles": len(self.data["mot_cle"]),
        }

        self.data["monthly_stats"] = {
            mois: {
                "nb_articles": len(self.data["mois"].get(mois, [])),
                "nb_mots_cles": self.data["mois_kw"].get(mois, 0),
                "nb_journaux": len([k for k, v in self.data["journal_mois"].items() if mois in v]),
                "nb_auteurs": len(
                    [e for e in self.data["auteur"].values() if any(x in self.data["mois"][mois] for x in e)]),
            } for mois in self.data["mois"].keys()
        }

        self.data["journal_stats"] = {
            journal: {
                "nb_articles": len(self.data["journal"][journal]),
                "nb_mots_cles": self.data["journal_mois"][journal],
                "nb_mois": len(self.data["journal_mois"][journal]),
            } for journal in self.data["journal"].keys()
        }

        self.data["index_kw"] = self.data["mot_cle"]

        self.data["monthly_index_kw"] = {
            mois: {kw: len(self.data["mois_kw"][mois][kw]) for kw in self.data["mois_kw"][mois]}
            for mois in self.data["mois_kw"]
        }

        self.data["quick_stats"] = pd.DataFrame(self.data["quick_stats"], index=["Valeur"])
        self.data["monthly_stats"] = pd.DataFrame(self.data["monthly_stats"]).T
        self.data["journal_stats"] = pd.DataFrame(self.data["journal_stats"]).T
        self.data["index_kw"] = pd.DataFrame(self.data["index_kw"], index=["Valeur"]).T
        self.data["monthly_index_kw"] = pd.DataFrame(self.data["monthly_index_kw"])

        self.data["monthly_stats"] = self.data["monthly_stats"].sort_index()
        self.data["monthly_index_kw"] = self.data["monthly_index_kw"].reindex(
            sorted(self.data["monthly_index_kw"].columns), axis=1)

        with io.BytesIO() as zip_io:
            with zipfile.ZipFile(zip_io, mode='w', compression=zipfile.ZIP_DEFLATED) as temp_zip:
                temp_zip.writestr('quick_stats.csv', self.data["quick_stats"].to_csv())
                temp_zip.writestr('monthly_stats.csv', self.data["monthly_stats"].to_csv())
                temp_zip.writestr('journal_stats.csv', self.data["journal_stats"].to_csv())
                temp_zip.writestr('index_kw.csv', self.data["index_kw"].to_csv())
                temp_zip.writestr('monthly_index_kw.csv', self.data["monthly_index_kw"].to_csv())

                with io.BytesIO() as bytes_io:
                    with pd.ExcelWriter(bytes_io, engine='xlsxwriter') as writer:
                        self.data["quick_stats"].to_excel(writer, sheet_name='quick_stats')
                        self.data["monthly_stats"].to_excel(writer, sheet_name='monthly_stats')
                        self.data["journal_stats"].to_excel(writer, sheet_name='journal_stats')
                        self.data["index_kw"].to_excel(writer, sheet_name='index_kw')
                        self.data["monthly_index_kw"].to_excel(writer, sheet_name='monthly_index_kw')

                    with temp_zip.open("stats.xlsx", "w") as f:
                        f.write(bytes_io.getvalue())

            return zip_io.getvalue()

    def get_plots(self, pivot_list):
        if not self.data["monthly_index_kw"]:
            self.get_stats(pivot_list)

        self.data["sorted_months"] = sorted(self.data["mois"].keys())

        with io.BytesIO() as zip_io:
            with zipfile.ZipFile(zip_io, mode='w', compression=zipfile.ZIP_DEFLATED) as temp_zip:
                for key in self.data["monthly_stats"].keys():
                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.plot(self.data["sorted_months"],
                            [self.data["monthly_stats"][key][mois] for mois in self.data["sorted_months"]])
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

    def plot_kw(self, rank: int = 0):
        fig, ax = plt.subplots(figsize=(10, 5))

        start, end = (rank * N_TOP, (rank + 1) * N_TOP)

        for kw in self.data["index_kw"].index[start: end]:
            ax.plot(self.data["sorted_months"],
                    [self.data["monthly_index_kw"][mois][kw] for mois in self.data["sorted_months"]], label=kw)

        ax.set_title(f"Évolution des mots clés {start + 1} à {end} les plus utilisés")
        ax.set_xlabel("Mois")
        ax.set_ylabel("Nombre d'articles")
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

    # mode = "small"

    for mode in ["small", "medium", "large"]:
        with open(f"../../profiler/data/pivots{f'_{mode}' if mode else ''}.json", "r") as f:
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

        with open(f"../../profiler/results/{mode}/stats.json", "w") as f:
            json.dump(transformer.data, f, indent=4)

        with open(f"../../profiler/results/{mode}/profiler.tsv", "w") as f:
            profiler_res = s.getvalue().splitlines()

            print(f"{mode = }\n\tprofiler => {profiler_res[0].strip()}")

            f.write("\n".join(profiler_res[4:]))
