import json
import re
import time
import zipfile
from datetime import datetime, date
from typing import List, Optional, Any
from io import StringIO, BytesIO

import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import polars as pl

from ..models import Pivot, TransformerOutput, Params
from ..transformers.transformer import Transformer

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

    @staticmethod
    def int_to_monthyear(i: int) -> str:
        # return self.to_monthyear(self.int_to_datetime(i))
        dt = datetime.fromtimestamp(i)
        return f"{dt.year}-{dt.month:02}"

    @staticmethod
    def int_to_monthyear_intversion( i: int) -> int:
        dt = datetime.fromtimestamp(i)
        return dt.year * 100 + dt.month  # --> int(f"{dt.year}{dt.month:02}") equivalent

    @staticmethod
    def for_display(mois_int: int) -> str:
        return f"{mois_int // 100}-{mois_int % 100:02}"
        # ## TODO : compare performance with this
        # mois_str = str(mois_int)
        # return f"{mois_str[:-2]}-{mois_str[-2:]}"

    def __init__(self, params: Optional[Params] = None, **kwargs: Optional[Any]):
        super().__init__(params, **kwargs)
        self.df = None
        self.data = None
        self.res = None

        self.stats_done = False
        self.processed_stats_done = False
        self.plots_done = False

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

    def transform(self, pivot_list: List[Pivot]) -> TransformerOutput:
        self._logger.debug("Starting to compute stats")
        t1 = time.time()

        self.pivot_list = pivot_list
        self.df = pl.from_records([p.model_dump() for p in self.pivot_list])

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
        self.stats_done = True

        self._transform_processed()

        self.output["stats"].data = json.dumps(self.res)
        return self.output["stats"]

    def _transform_processed(self, *args, **kwargs):
        if not self.stats_done:
            raise ValueError("You must compute the stats before generating the processed ones")

        self.processed_stats = {
            "journal":
                (
                    self.data["journal"]
                    .select("journal", pl.col("index_list").map_elements(lambda x: len(x)).alias("count"))
                    .filter(pl.col("count") >= self.params.minimal_support_journals)
                    .sort("count", descending=True)
                ),
            "mois":
                (
                    self.data["mois"]
                    .select("mois", pl.col("index_list").map_elements(lambda x: len(x)).alias("count"))
                    .filter(pl.col("count") >= self.params.minimal_support_dates)
                    .sort("mois")
                ),
            "auteur":
                (
                    self.data["auteur"]
                    .select(pl.col("auteur").cast(pl.Utf8), pl.col("index_list").map_elements(lambda x: len(x)).alias("count"))
                    .sort("count", descending=True)
                    .filter(pl.col("count") >= self.params.minimal_support_authors)
                    .filter(pl.col("auteur") != "Unknown")
                ),
            "mot_cle":
                (
                    self.data["mot_cle"]
                    .select("mot_cle", pl.col("index_list").map_elements(lambda x: len(x)).alias("count"))
                    .filter(pl.col("count") >= self.params.minimal_support_kw)
                    .sort("count", descending=True)
                ),
        }

        self.journal_order = self.processed_stats["journal"].select(pl.col("journal")).to_series().to_list()
        self.auteur_order = self.processed_stats["auteur"].select(pl.col("auteur")).to_series().to_list()
        self.mot_cle_order = self.processed_stats["mot_cle"].select(pl.col("mot_cle")).to_series().to_list()

        self.processed_stats.update({
            "mois_journal": {
                journal: (
                    self.data["mois_journal"]
                    .filter(pl.col("journal") == journal)
                    .select("mois", pl.col("index_list").map_elements(lambda x: len(x)).alias("count"))
                    .sort("mois")
                ) for journal in self.journal_order
            },
            "mois_kw": {
                kw: (
                    self.data["mois_kw"]
                    .filter(pl.col("mot_cle") == kw)
                    .select("mois", pl.col("index_list").map_elements(lambda x: len(x)).alias("count"))
                    .sort("mois")
                ) for kw in self.mot_cle_order
            },
            "mois_auteur": {
                auteur: (
                    self.data["mois_auteur"]
                    .filter(pl.col("auteur") == auteur)
                    .select("mois", pl.col("index_list").map_elements(lambda x: len(x)).alias("count"))
                    .sort("mois")
                ) for auteur in self.auteur_order
            },
        })

        self.processed_stats_done = True

    def get_stats(self, *args, **kwargs):
        if not self.stats_done:
            raise ValueError("You must compute the stats before getting them")
        return self.output["stats"]

    def get_processed_stats(self, *args, **kwargs):
        if not self.stats_done or not self.processed_stats_done:
            raise ValueError("You must compute the stats before getting the processed ones")

        self.output["processed_stats"].data = json.dumps({
            "journal": {k: v for k, v in zip(*self.processed_stats["journal"].to_dict(as_series=False).values())},
            "mois": {k: v for k, v in zip(*self.processed_stats["mois"].to_dict(as_series=False).values())},
            "auteur": {k: v for k, v in zip(*self.processed_stats["auteur"].to_dict(as_series=False).values())},
            "mois_journal": {
                journal: {k: v for k, v in zip(*df.to_dict(as_series=False).values())} for journal, df in self.processed_stats["mois_journal"].items()
            },
            "mois_kw": {
                kw: {k: v for k, v in zip(*df.to_dict(as_series=False).values())} for kw, df in self.processed_stats["mois_kw"].items()
            },
            "mois_auteur": {
                auteur: {k: v for k, v in zip(*df.to_dict(as_series=False).values())} for auteur, df in self.processed_stats["mois_auteur"].items()
            },
        })

        return self.output["processed_stats"]

    def get_plots(self, *args, **kwargs):
        if not self.stats_done or not self.processed_stats_done:
            raise ValueError("You must compute the stats before generating the plots")

        if self.plots_done:
            return self.output["plots"]

        self._logger.debug("Starting to compute plots")
        t1 = time.time()

        with BytesIO() as zip_io:
            with zipfile.ZipFile(zip_io, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
                self._get_plots(zip_file)

            self._logger.debug(f"Time to compute plots: {time.time() - t1:.2f}s")
            self.output["plots"].data = zip_io.getvalue()

            self.plots_done = True
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
        fig = px.bar(
            self.processed_stats["journal"],
            x="journal",
            y="count",
            color="count",
            labels={"x": "Journal", "y": "Nombre d'articles", "count": "Nombre d'articles"},
            title="Nombre d'articles par journal",
            color_continuous_scale=self.MAIN_COLOR,
        )

        fig.update_layout(
            xaxis_tickformat="%B %Y",
        )

        self.zip_file.writestr("journal.html", fig.to_html())

    def _get_plots_mois(self):
        fig = px.bar(
            self.processed_stats["mois"],
            x="mois",
            y="count",
            color="count",
            labels={"x": "Mois", "y": "Nombre d'articles", "count": "Nombre d'articles"},
            title="Nombre d'articles par mois",
            color_continuous_scale=self.MAIN_COLOR,
        )
        fig.update_layout(
            xaxis_tickformat="%B %Y",
        )
        self.zip_file.writestr("mois.html", fig.to_html())

    def _get_plots_auteur(self):
        fig = px.bar(
            self.processed_stats["auteur"],
            x="auteur",
            y="count",
            color="count",
            labels={"x": "Auteur", "y": "Nombre d'articles", "count": "Nombre d'articles"},
            title="Nombre d'articles par auteur",
            color_continuous_scale=self.MAIN_COLOR,
        )
        self.zip_file.writestr("auteur.html", fig.to_html())

    def _get_plots_mot_cle(self):
        fig = px.bar(
            self.processed_stats["mot_cle"],
            x="mot_cle",
            y="count",
            color="count",
            labels={"x": "Mot clé", "y": "Nombre d'articles", "count": "Nombre d'articles"},
            title="Nombre d'articles par mot clé",
            color_continuous_scale=self.MAIN_COLOR,
        )
        self.zip_file.writestr("mot_cle.html", fig.to_html())

    def _get_plots_mois_journal(self):
        fig = px.line()

        for journal in self.journal_order:
            df = self.processed_stats["mois_journal"][journal]

            if len(df) < self.params.minimal_support:
                continue

            fig.add_trace(
                go.Scatter(
                    x=df.select("mois").to_series(),
                    y=df.select("count").to_series(),
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
            df = self.processed_stats["mois_kw"][kw]

            if len(df) < self.params.minimal_support:
                continue

            fig.add_trace(
                go.Scatter(
                    x=df.select("mois").to_series(),
                    y=df.select("count").to_series(),
                    name=kw,
                    connectgaps=True,
                )
            )

        fig.update_layout(
            xaxis_tickformat="%B %Y",
            title="Nombre d'articles par mois et par mot clé",
            xaxis_title="Mois",
            yaxis_title="Nombre d'articles",
            margin=dict(l=20),
        )

        self.zip_file.writestr("mois_kw.html", fig.to_html())

    def _get_plots_mois_auteur(self):
        fig = px.line()

        for auteur in self.auteur_order:
            df = self.processed_stats["mois_auteur"][auteur]

            if len(df) < self.params.minimal_support:
                continue

            fig.add_trace(
                go.Scatter(
                    x=df.select("mois").to_series(),
                    y=df.select("count").to_series(),
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


if __name__ == '__main__':
    import cProfile
    import pstats

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
        s = StringIO()
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
