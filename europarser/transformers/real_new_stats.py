import re, json, time, zipfile, locale
from datetime import datetime, date
from typing import List, Tuple, Any

import polars as pl

import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from europarser.transformers.transformer import Transformer
from europarser.models import Pivot

locale.setlocale(locale.LC_ALL, "fr_FR")
pio.templates.default = "plotly_dark"

class StatsTransformer(Transformer):
    mois = (
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"
    )

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

    def for_display(self, mois_int: int) -> str:
        return f"{mois_int // 100}-{mois_int % 100}"
        # ## TODO : compare performance with this
        # mois_str = str(mois_int)
        # return f"{mois_str[:-2]}-{mois_str[-2:]}"

    def __init__(self):
        super().__init__()
        self.df = None
        self.data = None
        self.res = None
        self.stats_processed = False
        self.pivot_list = None

    def transform(self, pivot_list: List[Pivot]):
        self._logger.warning("Starting to compute stats")
        t1 = time.time()

        self.pivot_list = pivot_list
        self.df = pl.from_records([p.dict() for p in self.pivot_list])

        self.df = self.df.with_columns(
            pl.col('journal_clean').str.strip_chars().alias('journal_clean'),

            pl.col('epoch').map_elements(self.int_to_monthyear_intversion).alias('mois'),

            pl.col('keywords')
            .str.replace_all(r"[(\[\])']", "")
            .str.split(',')
            .list.eval(pl.element().filter(pl.element() != ""))
            .list.eval(pl.element().str.strip_chars(" ,\n\t"))
            .list.drop_nulls(),
        ).with_row_count()

        self.list_mois = list(self.df.select("mois").to_series().unique().map_elements(self.for_display))

        self.data = {
            "journal": (
                self.df
                .group_by("journal_clean")
                .agg(pl.col("row_nr").agg_groups())
                .sort("journal_clean")
                .select(pl.col("journal_clean").alias("journal"), pl.col("row_nr").alias("index_list"))
            ),
            "mois": (
                self.df
                .group_by("mois")
                .agg(pl.col("row_nr").agg_groups())
                .sort("mois")
                .select(pl.col("mois").alias("mois"), pl.col("row_nr").alias("index_list"))
                .with_columns(pl.col("mois").map_elements(self.for_display))
            )
            ,
            "auteur": (
                self.df
                .group_by("auteur")
                .agg(pl.col("row_nr").agg_groups())
                .sort("auteur")
                .select(pl.col("auteur").alias("auteur"), pl.col("row_nr").alias("index_list"))
            ),
            "mot_cle": (
                self.df
                .explode("keywords")
                .drop_nulls()
                .group_by("keywords")
                .agg(pl.col("row_nr").agg_groups())
                .sort("keywords")
                .select(pl.col("keywords").alias("mot_cle"), pl.col("row_nr").alias("index_list"))
            ),

            "mois_journal": (
                self.df
                .group_by(["mois", "journal_clean"])
                .agg(pl.col("row_nr").agg_groups())
                .sort(["journal_clean", "mois"])
                .select(pl.col("journal_clean").alias("journal"), pl.col("mois").alias("mois"),
                        pl.col("row_nr").alias("index_list"))
                .with_columns(
                    pl.col("mois").map_elements(self.for_display)
                )
            ),
            "mois_kw": (
                self.df
                .explode("keywords")
                .group_by(["mois", "keywords"])
                .agg(pl.col("row_nr").agg_groups())
                .sort(["mois", "keywords"])
                .select(pl.col("mois").alias("mois"), pl.col("keywords").alias("mot_cle"),
                        pl.col("row_nr").alias("index_list"))
                .with_columns(
                    pl.col("mois").map_elements(self.for_display)
                )
            ),
            "mois_auteur": (
                self.df
                .group_by(["mois", "auteur"])
                .agg(pl.col("row_nr").agg_groups())
                .sort(["auteur", "mois"])
                .select(pl.col("auteur").alias("auteur"), pl.col("mois").alias("mois"),
                        pl.col("row_nr").alias("index_list"))
                .with_columns(
                    pl.col("mois").map_elements(self.for_display)
                )
            ),
        }

        self.res = {
            key: {
                key2: val2
                for key2, val2 in list(zip(*val.to_dict(as_series=False).values()))
            }
            for key, val in self.data.items() if len(val.columns) == 2
        }

        self.res.update({
            key: {
                f"{key2}_{key2_bis}": val2
                for key2, key2_bis, val2 in list(zip(*val.to_dict(as_series=False).values()))
            }
            for key, val in self.data.items() if len(val.columns) == 3
        })

        self._logger.warning(f"Time to compute stats: {time.time() - t1:.2f}s")
        self.stats_processed = True

        return self.res

    def get_plots(self, pivot_list: List[Pivot] = None):
        if not self.stats_processed:
            self.transform(pivot_list)

        self._logger.warning("Starting to compute plots")
        t1 = time.time()

        with io.BytesIO() as zip_io:
            with zipfile.ZipFile(zip_io, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
                self._get_plots(zip_file)

            self._logger.warning(f"Time to compute plots: {time.time() - t1:.2f}s")
            return zip_io.getvalue()

    def _get_plots(self, zip_file):
        self._get_plots_journal(zip_file)
        self._get_plots_mois(zip_file)
        self._get_plots_auteur(zip_file)
        self._get_plots_mot_cle(zip_file)

        self.create_index_mois()

        self._get_plots_mois_journal(zip_file)
        self._get_plots_mois_kw(zip_file)
        self._get_plots_mois_auteur(zip_file)

    def _get_plots_journal(self, zip_file):
        tobar = (
            self.data["journal"]
            .select("journal", pl.col("index_list").map_elements(lambda x: len(x)))
            .sort("index_list", descending=True)
        )
        self.journal_order = tobar.select(pl.col("journal")).to_series().to_list()
        fig = px.bar(
            x=tobar.select("journal").to_series(),
            y=tobar.select("index_list").to_series(),
            labels={"x": "Journal", "y": "Nombre d'articles"},
            title="Nombre d'articles par journal",
            range_color="blues"
        )
        zip_file.writestr("journal.html", fig.to_html())

    def _get_plots_mois(self, zip_file):
        tobar = (
            self.data["mois"]
            .select("mois", pl.col("index_list").map_elements(lambda x: len(x)))
            .sort("mois")
        )
        fig = px.bar(
            x=tobar.select("mois").to_series(),
            y=tobar.select("index_list").to_series(),
            labels={"x": "Mois", "y": "Nombre d'articles"},
            title="Nombre d'articles par mois",
            range_color="blues",
        )
        fig.update_layout(
            xaxis_tickformat="%B %Y",
        )
        zip_file.writestr("mois.html", fig.to_html())

    def _get_plots_auteur(self, zip_file):
        tobar = (
            self.data["auteur"]
            .select(pl.col("auteur").cast(pl.Utf8), pl.col("index_list").map_elements(lambda x: len(x)))
            .sort("index_list", descending=True)
            .filter(pl.col("index_list") > 1)
            .filter(pl.col("auteur") != "Unknown")
        )
        self.auteur_order = tobar.select(pl.col("auteur")).to_series().to_list()
        fig = px.bar(
            x=tobar.select("auteur").to_series(),
            y=tobar.select("index_list").to_series(),
            labels={"x": "Auteur", "y": "Nombre d'articles"},
            title="Nombre d'articles par auteur",
            range_color="blues"
        )
        zip_file.writestr("auteur.html", fig.to_html())

    def _get_plots_mot_cle(self, zip_file):
        tobar = (
            self.data["mot_cle"]
            .select("mot_cle", pl.col("index_list").map_elements(lambda x: len(x)))
            .filter(pl.col("index_list") > 4)
            .sort("index_list", descending=True)
        )
        self.mot_cle_order = tobar.select(pl.col("mot_cle")).to_series().to_list()
        fig = px.bar(
            x=tobar.select("mot_cle").to_series(),
            y=tobar.select("index_list").to_series(),
            labels={"x": "Mot clé", "y": "Nombre d'articles"},
            title="Nombre d'articles par mot clé",
            range_color="blues"
        )
        zip_file.writestr("mot_cle.html", fig.to_html())

    def _get_plots_mois_journal(self, zip_file):
        pass

    def _get_plots_mois_kw(self, zip_file):
        pass

    def _get_plots_mois_auteur(self, zip_file):
        pass

    def create_index_mois(self):
        self.index_mois = {
            mois: {
            "journal": {journal: 0 for journal in self.journal_order},
            "auteur": {auteur: 0 for auteur in self.auteur_order},
            "mot_cle": {mot_cle: 0 for mot_cle in self.mot_cle_order},
            }
            for mois in self.list_mois
        }

        for row in self.data["mois_journal"].rows():
            self.index_mois[row[1]]["journal"][row[0]] = len(row[2])

        for row in self.data["mois_auteur"].rows():
            self.index_mois[row[1]]["auteur"][row[0]] = len(row[2])

        for row in self.data["mois_kw"].rows():
            if row[1] is None:
                continue

            self.index_mois[row[0]]["mot_cle"][row[1]] = len(row[2])





if __name__ == '__main__':
    import cProfile
    import pstats
    import io

    # mode = "small"

    for mode in ["small", "medium", "large"]:
        with open(f"../../profiler/data/pivots{f'_{mode}' if mode else ''}.json", "r") as f:
            dict_ = json.load(f)
            dict_ = list(dict_.values())
            pivot_list = [Pivot(**d) for d in dict_]

        transformer = StatsTransformer()

        pr = cProfile.Profile()
        pr.enable()

        res = transformer.transform(pivot_list)
        zip_file = transformer.get_plots()

        pr.disable()
        s = io.StringIO()
        sortby = 'cumulative'
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        # ps.print_stats()

        with open(f"../../profiler/results/{mode}/stats.json", "w") as f:
            json.dump(res, f, indent=4)

        with open(f"../../profiler/results/{mode}/profiler.tsv", "w") as f:
            profiler_res = s.getvalue().splitlines()

            # print(f"{mode = }\n\tprofiler => {profiler_res[0].strip()}")

            f.write("\n".join(profiler_res[4:]))

        with open(f"../../profiler/results/{mode}/plots.zip", "wb") as f:
            f.write(zip_file)
