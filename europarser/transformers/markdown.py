import io
import re
import zipfile

from typing import List

import yaml

from europarser.models import Pivot, TransformerOutput
from europarser.transformers.transformer import Transformer


class MarkdownTransformer(Transformer):
    def __init__(self):
        super().__init__()
        self.output_type = "zip"
        self.output = TransformerOutput(data=None, output=self.output_type,
                                        filename=f'{self.name}_output.{self.output_type}')

    def generate_markdown(self, pivot: Pivot):
        # Générer le contenu du fichier markdown
        frontmatter = {
            "journal_clean": clean_string(pivot.journal_clean),
            "auteur": clean_string(pivot.auteur),
            "titre": clean_string(pivot.titre),
            "date": pivot.date,
            "langue": clean_string(pivot.langue),
            "tags": [clean_string(tag) for tag in pivot.keywords.split(",")],
        }

        markdown_content = f"---\n{yaml.dump(frontmatter)}---\n\n{pivot.texte}"

        return clean_string(pivot.titre) + ".md", markdown_content

    def transform(self, pivots: List[Pivot]) -> TransformerOutput:
        in_memory_zip = io.BytesIO()
        with zipfile.ZipFile(in_memory_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
            for pivot in pivots:
                filename, content = self.generate_markdown(pivot)
                zipf.writestr(filename, content)

        in_memory_zip.seek(0)
        self.output.data = in_memory_zip
        return self.output


def clean_string(s):
    # Fonction pour nettoyer les chaînes de caractères
    s = re.sub(r"[^\w\s]", "", s)  # Supprimer les caractères spéciaux
    s = s.lower()  # Mettre en minuscule
    s = s.strip()  # Supprimer les espaces au début et à la fin
    s = re.sub(r'\s+', '_', s)  # Remplacer les espaces par des underscores
    return s