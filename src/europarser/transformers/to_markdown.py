import hashlib
import io
import re
import zipfile
from collections import defaultdict

from typing import List

import yaml

from ..models import Pivot, TransformerOutput
from ..transformers.transformer import Transformer


class MarkdownTransformer(Transformer):
    def __init__(self):
        super().__init__()
        self.output_type = "zip"
        self.output = TransformerOutput(data=None, output=self.output_type,
                                        filename=f'{self.name}_output.{self.output_type}')
        self.seen_names = set()
        self.stats = None
        self.stats_output = ""

    def generate_markdown(self, pivot: Pivot):
        # Générer le contenu du fichier markdown
        frontmatter = {
            "journal": clean_string(pivot.journal_clean),
            "auteur": clean_string(pivot.auteur),
            "titre": clean_string(pivot.titre),
            "date": pivot.date,
            "langue": clean_string(pivot.langue),
            "tags": [clean_string(tag) for tag in pivot.keywords],
            "journal_charts": "journal_" + clean_string(pivot.journal_clean),
            "auteur_charts": "auteur_" + clean_string(pivot.journal_clean),
            "url": pivot.url,
        }

        markdown_content = f"---\n{yaml.dump(frontmatter)}---\n\n{pivot.texte}"

        # Nom du fichier markdown
        # Si le titre est trop long, on le tronque à 100 caractères
        # Si le titre est vide (une fois nettoyé), on utilise le hash du texte
        base_nom = frontmatter["titre"][:100].strip("_") or hashlib.md5(pivot.texte.encode()).hexdigest()

        nom = f"{frontmatter['journal']}/{base_nom}.md"
        if nom in self.seen_names:
            # Si le nom existe déjà, on ajoute la date à la fin (sans l'heure)
            nom = f"{nom[:-3]}_{clean_string(pivot.date).split('t')[0]}.md"
        self.seen_names.add(nom)

        return nom, markdown_content

    def transform(self, pivots: List[Pivot]) -> TransformerOutput:
        self.compute_stats(pivots)
        in_memory_zip = io.BytesIO()
        with zipfile.ZipFile(in_memory_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
            for pivot in pivots:
                filename, content = self.generate_markdown(pivot)
                zipf.writestr(filename, content)
            zipf.writestr("Statistiques.md", self.make_waffle())

        in_memory_zip.seek(0)
        self.output.data = in_memory_zip.getvalue()
        return self.output

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
            search_value = 'journal_' + clean_string(journal) + '" -file:(Statistiques) "'
            chart['data']['children'].append({'name': journal, 'value': value, 'journal_chart': search_value})

        output += yaml.dump(chart)
        output += "```"
        return output

def clean_string(s):
    # Fonction pour nettoyer les chaînes de caractères
    s = re.sub(r"[^\w\s]", "", s)  # Supprimer les caractères spéciaux
    s = s.lower()  # Mettre en minuscule
    s = s.strip()  # Supprimer les espaces au début et à la fin
    s = re.sub(r'\s+', '_', s)  # Remplacer les espaces par des underscores
    return s
