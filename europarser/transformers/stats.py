import json
import re
import time
import zipfile
import io
from datetime import datetime, date
from typing import List

import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import polars as pl

from europarser.models import Pivot, TransformerOutput
from europarser.transformers.transformer import Transformer

# locale.setlocale(locale.LC_ALL, "fr_FR.UTF-8")
pio.templates.default = "none"


class StatsTransformer(Transformer):
    mois = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre",
            "décembre")
    COOL_COLORS = {"bluered", "plasma", "plotly3", "rainbow", "portland", "spectral", "inferno", "sunsetdark", "matter",
                   "turbo", "rdbu"}
    COOL_COLORS |= {e + "_r" for e in COOL_COLORS}
    MAIN_COLOR = "bluered_r"

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
        return f"{mois_int // 100}-{mois_int % 100:02}"
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

        self.output_type = {
            "stats": "json",
            "processed_stats": "json",
            "plots": "zip",
        }

        self.output = {
            k: TransformerOutput(
                data=None,
                output=self.output_type[k],
                filename=f'{k}_output.{self.output_type[k]}'
            )
            for k in self.output_type
        }

    def transform(self, pivot_list: List[Pivot]) -> dict[str, dict[str, list[int]]]:
        self._logger.debug("Starting to compute stats")
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

        self._logger.debug(f"Time to compute stats: {time.time() - t1:.2f}s")
        self.stats_processed = True

        self.output["stats"].data = json.dumps(self.res)
        return self.output["stats"]

    def get_stats(self, *args, **kwargs):
        if not self.stats_processed:
            raise ValueError("You must compute the stats before getting them")
        return self.output["stats"]

    def get_plots(self, *args, **kwargs):
        if not self.stats_processed:
            raise ValueError("You must provide a pivot_list to get_plots if you haven't already computed the stats")

        self._logger.debug("Starting to compute plots")
        t1 = time.time()

        with io.BytesIO() as zip_io:
            with zipfile.ZipFile(zip_io, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
                self._get_plots(zip_file)

            self._logger.debug(f"Time to compute plots: {time.time() - t1:.2f}s")
            self.output["plots"].data = zip_io.getvalue()
            return self.output["plots"]

    def _get_plots(self, zip_file):
        self.zip_file = zip_file

        self._get_plots_journal()
        self._get_plots_mois()
        self._get_plots_auteur()
        self._get_plots_mot_cle()

        self._get_plots_mois_journal()
        self._get_plots_mois_kw()
        self._get_plots_mois_auteur()

    def _get_plots_journal(self):
        tobar = (
            self.data["journal"]
            .select("journal", pl.col("index_list").map_elements(lambda x: len(x)))
            .sort("index_list", descending=True)
        )
        self.journal_order = tobar.select(pl.col("journal")).to_series().to_list()
        fig = px.bar(
            tobar,
            x="journal",
            y="index_list",
            color="index_list",
            labels={"x": "Journal", "y": "Nombre d'articles", "index_list": "Nombre d'articles"},
            title="Nombre d'articles par journal",
            color_continuous_scale=self.MAIN_COLOR,
        )
        self.zip_file.writestr("journal.html", fig.to_html())

    def _get_plots_mois(self):
        tobar = (
            self.data["mois"]
            .select("mois", pl.col("index_list").map_elements(lambda x: len(x)))
            .sort("mois")
        )
        fig = px.bar(
            tobar,
            x="mois",
            y="index_list",
            color="index_list",
            labels={"x": "Mois", "y": "Nombre d'articles", "index_list": "Nombre d'articles"},
            title="Nombre d'articles par mois",
            color_continuous_scale=self.MAIN_COLOR,
        )
        fig.update_layout(
            xaxis_tickformat="%B %Y",
        )
        self.zip_file.writestr("mois.html", fig.to_html())

    def _get_plots_auteur(self):
        tobar = (
            self.data["auteur"]
            .select(pl.col("auteur").cast(pl.Utf8), pl.col("index_list").map_elements(lambda x: len(x)))
            .sort("index_list", descending=True)
            .filter(pl.col("index_list") > 1)
            .filter(pl.col("auteur") != "Unknown")
        )
        self.auteur_order = tobar.select(pl.col("auteur")).to_series().to_list()
        fig = px.bar(
            tobar,
            x="auteur",
            y="index_list",
            color="index_list",
            labels={"x": "Auteur", "y": "Nombre d'articles", "index_list": "Nombre d'articles"},
            title="Nombre d'articles par auteur",
            color_continuous_scale=self.MAIN_COLOR,
        )
        self.zip_file.writestr("auteur.html", fig.to_html())

    def _get_plots_mot_cle(self):
        tobar = (
            self.data["mot_cle"]
            .select("mot_cle", pl.col("index_list").map_elements(lambda x: len(x)))
            .filter(pl.col("index_list") > 4)
            .sort("index_list", descending=True)
        )
        self.mot_cle_order = tobar.select(pl.col("mot_cle")).to_series().to_list()
        fig = px.bar(
            tobar,
            x="mot_cle",
            y="index_list",
            color="index_list",
            labels={"x": "Mot clé", "y": "Nombre d'articles", "index_list": "Nombre d'articles"},
            title="Nombre d'articles par mot clé",
            color_continuous_scale=self.MAIN_COLOR,
        )
        self.zip_file.writestr("mot_cle.html", fig.to_html())

    def _get_plots_mois_journal(self):
        fig = px.line()

        for journal in self.journal_order:
            df = (
                self.data["mois_journal"]
                .filter(pl.col("journal") == journal)
                .select("mois", pl.col("index_list").map_elements(lambda x: len(x)))
                .sort("mois")
            )

            if len(df) < 2:
                continue

            fig.add_trace(
                go.Scatter(
                    x=df.select("mois").to_series(),
                    y=df.select("index_list").to_series(),
                    name=journal,
                    connectgaps=True,
                )
            )

        fig.update_layout(
            xaxis_tickformat="%B %Y",
            title="Nombre d'articles par mois et par journal",
            xaxis_title="Mois",
            yaxis_title="Nombre d'articles",

        )

        self.zip_file.writestr("mois_journal.html", fig.to_html())

    def _get_plots_mois_kw(self):
        fig = px.line()

        for kw in self.mot_cle_order:
            df = (
                self.data["mois_kw"]
                .filter(pl.col("mot_cle") == kw)
                .select("mois", pl.col("index_list").map_elements(lambda x: len(x)))
                .sort("mois")
            )

            if len(df) < 2:
                continue

            fig.add_trace(
                go.Scatter(
                    x=df.select("mois").to_series(),
                    y=df.select("index_list").to_series(),
                    name=kw,
                    connectgaps=True,

                )
            )

        fig.update_layout(
            xaxis_tickformat="%B %Y",
            title="Nombre d'articles par mois et par mot clé",
            xaxis_title="Mois",
            yaxis_title="Nombre d'articles",

        )

        self.zip_file.writestr("mois_kw.html", fig.to_html())

    def _get_plots_mois_auteur(self):
        fig = px.line()

        for auteur in self.auteur_order:
            df = (
                self.data["mois_auteur"]
                .filter(pl.col("auteur") == auteur)
                .select("mois", pl.col("index_list").map_elements(lambda x: len(x)))
                .sort("mois")
            )

            if len(df) < 2:
                continue

            fig.add_trace(
                go.Scatter(
                    x=df.select("mois").to_series(),
                    y=df.select("index_list").to_series(),
                    name=auteur,
                    connectgaps=True,

                )
            )

        fig.update_layout(
            xaxis_tickformat="%B %Y",
            title="Nombre d'articles par mois et par auteur",
            xaxis_title="Mois",
            yaxis_title="Nombre d'articles",

        )

        self.zip_file.writestr("mois_auteur.html", fig.to_html())

    def get_processed_stats(self, *args, **kwargs):
        # TODO: add processed_stats
        if not self.stats_processed:
            raise ValueError("You must compute the stats before getting them")

        raise NotImplementedError

    def _test_COOLORS(self):
        tobar = (
            self.data["journal"]
            .select("journal", pl.col("index_list").map_elements(lambda x: len(x)))
            .sort("index_list", descending=True)
        )
        self.journal_order = tobar.select(pl.col("journal")).to_series().to_list()

        for color in self.COOL_COLORS:
            fig = px.bar(
                tobar,
                x="journal",
                y="index_list",
                labels={"x": "Journal", "y": "Nombre d'articles", "index_list": "Nombre d'articles"},
                title="Nombre d'articles par journal",
                color_continuous_scale=color,
                color="index_list",
            )
            fig.update_layout(

            )
            self.zip_file.writestr(f"!_journal_{color}.html", fig.to_html())


if __name__ == '__main__':
    import cProfile
    import pstats
    import io

    # mode = "small"

    for mode in ["small", "medium", "large"]:
        with open(f"../../profiler/data/pivots{f'_{mode}' if mode else ''}.json", "r", encoding="utf-8") as f:
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
