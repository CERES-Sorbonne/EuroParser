import re, json, time, zipfile
from datetime import datetime, date
from typing import List, Tuple, Any

import polars as pl

from europarser.transformers.transformer import Transformer
from europarser.models import Pivot


class StatsTransformer(Transformer):
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

    # @staticmethod
    # def clean_keywords(column: pl.Series) -> pl.Series:
    #     return column.apply(lambda x: x.split(', ').trim().filter(lambda e: e.is_not_empty()))

    def __init__(self):
        super().__init__()
        self.df = None
        self.data = None
        self.res = None
        self.stats_processed = False

    def transform(self, pivot_list: List[Pivot]):
        self._logger.warning("Starting to compute stats")
        t1 = time.time()

        self.df = pl.from_records([p.dict() for p in pivot_list])

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

        # journals = self.df['journal_clean'].unique().to_list()
        # mois = self.df['mois'].unique().to_list()
        # auteurs = self.df['auteur'].unique().to_list()
        # keywords = list(set(k for ks in self.df['keywords'] for k in ks))
        # print(keywords)

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
                .with_columns(
                    pl.col("mois").map_elements(self.for_display)
                )
            ),
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
            "journal_mois": (
                self.df
                .group_by(["journal_clean", "mois"])
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
            )
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
        # print(self.res)

        return self.res


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

        pr.disable()
        s = io.StringIO()
        sortby = 'cumulative'
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()

        with open(f"../../profiler/results/{mode}/stats.json", "w") as f:
            json.dump(res, f, indent=4)

        with open(f"../../profiler/results/{mode}/profiler.tsv", "w") as f:
            profiler_res = s.getvalue().splitlines()

            print(f"{mode = }\n\tprofiler => {profiler_res[0].strip()}")

            f.write("\n".join(profiler_res[4:]))
