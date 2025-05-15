import hashlib
import io
import zipfile
from collections import defaultdict

from typing import List

import yaml

from ..models import Pivot, TransformerOutput
from ..transformers.transformer import Transformer
from ..utils import super_writestr


class MarkdownTransformer(Transformer):
    def __init__(self):
        super().__init__()
        self.output_type = "zip"
        self.output = TransformerOutput(
            data=None, output=self.output_type, filename=f'{self.name}_output.{self.output_type}'
        )
        self.seen_names = set()
        self.stats = None
        self.stats_output = ""

    def generate_markdown(self, pivot: Pivot):
        # Générer le contenu du fichier markdown
        frontmatter = {
            "journal": pivot.journal_clean,
            "auteur": pivot.auteur,
            "titre": pivot.titre,
            "date": pivot.date,
            "langue": self.clean_string(pivot.langue),
            "tags": [self.clean_string(tag) for tag in pivot.keywords],
            "journal_charts": "journal_" + self.clean_string(pivot.journal_clean),
            "auteur_charts": "auteur_" + self.clean_string(pivot.journal_clean),
            "url": pivot.url,
        }

        markdown_content = f"---\n{yaml.dump(frontmatter)}---\n\n{pivot.texte}"

        # Nom du fichier markdown
        # Si le titre est trop long, on le tronque à 100 caractères
        # Si le titre est vide (une fois nettoyé), on utilise le hash du texte
        base_nom = self.clean_string(pivot.titre).strip("_")[:100] or hashlib.md5(pivot.texte.encode()).hexdigest()

        nom = f"{frontmatter['journal']}/{base_nom}.md"
        if nom in self.seen_names:
            # Si le nom existe déjà, on ajoute la date à la fin (sans l'heure)
            nom = f"{nom[:-3]}_{self.clean_string(pivot.date).split('t')[0]}.md"
        self.seen_names.add(nom)

        return nom, markdown_content

    def transform(self, pivots: List[Pivot]) -> TransformerOutput:
        try:
            self.compute_stats(pivots)
            in_memory_zip = io.BytesIO()
            with zipfile.ZipFile(in_memory_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
                for pivot in pivots:
                    filename, content = self.generate_markdown(pivot)
                    super_writestr(zipf, filename, content)
                zipf.writestr("Statistiques.md", self.make_waffle())

            in_memory_zip.seek(0)
            self.output.data = in_memory_zip.getvalue()
            return self.output
        except Exception as e:
            print(self.__class__.__name__, e)
            raise

    def compute_stats(self, pivots, key="journal"):
        articles_par_cle = defaultdict(int)

        # Parcourez la liste d'éléments pivots
        for pivot in pivots:
            # Incrémentez le compteur pour le journal actuel
            articles_par_cle[pivot.journal_clean] += 1

        # Convertissez le defaultdict en un dictionnaire Python standard pour la sortie
        self.stats = dict(articles_par_cle)

    def make_waffle(self):
        output = "## Articles par journal \n\n" \
                 "```chartsview\n"
        chart = {
            "type": "Treemap",
            "data": {
                "name": "root",
                "children": [],
            },
            "options": {
                "colorField": "name",
                "enableSearchInteraction": {
                    "field": "journal_chart"
                }
            }
        }
        for journal, value in self.stats.items():
            # do this to avoid searching in the Statistics.md file
            search_value = 'journal_' + self.clean_string(journal) + '" -file:(Statistiques) "'
            chart['data']['children'].append({'name': journal, 'value': value, 'journal_chart': search_value})

        output += yaml.dump(chart)
        output += "```"
        return output

