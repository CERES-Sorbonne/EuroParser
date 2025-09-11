from typing import List

from europarser.models import Pivot, TransformerOutput, OutputFormat
from europarser.transformers.transformer import Transformer


class BibtexTransformer(Transformer):
    def __init__(self):
        super(BibtexTransformer, self).__init__()
        self.output_type = "bib"
        self.output = TransformerOutput(data=None, output=self.output_type,
                                        filename=f'{self.name}_output.{self.output_type}')

    def transform(self, pivot_list: List[Pivot]) -> TransformerOutput:
        try:
            bibtex_entries = []

            for i, pivot in enumerate(pivot_list):
                # Génération d'une clé unique pour chaque entrée
                key = self._generate_key(pivot, i)

                # Construction de l'entrée BibTeX
                entry = self._create_bibtex_entry(pivot, key)
                bibtex_entries.append(entry)

            # Assemblage du fichier BibTeX complet
            bibtex_content = "\n\n".join(bibtex_entries)
            self.output.data = bibtex_content
            return self.output

        except Exception as e:
            print(self.__class__.__name__, e)
            raise

    def _generate_key(self, pivot: Pivot, index: int) -> str:
        """Génère une clé unique pour l'entrée BibTeX"""
        # Nettoie l'auteur pour la clé
        author_clean = self._clean_for_key(pivot.auteur) if pivot.auteur else "unknown"

        # Utilise les premiers mots du titre si disponible
        title_words = pivot.titre.split()[:2] if pivot.titre else ["article"]
        title_clean = "".join(self._clean_for_key(word) for word in title_words)

        return f"{author_clean}{pivot.annee}{title_clean}_{index}"

    def _clean_for_key(self, text: str) -> str:
        """Nettoie le texte pour l'utiliser dans une clé BibTeX"""
        if not text:
            return ""

        # Supprime les accents et caractères spéciaux
        import unicodedata
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')

        # Garde seulement les lettres et chiffres
        return ''.join(c for c in text if c.isalnum())

    def _escape_bibtex(self, text: str) -> str:
        """Échappe les caractères spéciaux pour BibTeX"""
        if not text:
            return ""

        # Remplace les caractères spéciaux BibTeX
        replacements = {
            '{': '\\{',
            '}': '\\}',
            '$': '\\$',
            '&': '\\&',
            '%': '\\%',
            '#': '\\#',
            '_': '\\_',
            '^': '\\^{}',
            '~': '\\~{}',
            '\\': '\\textbackslash{}'
        }

        for char, replacement in replacements.items():
            text = text.replace(char, replacement)

        return text

    def _create_bibtex_entry(self, pivot: Pivot, key: str) -> str:
        """Crée une entrée BibTeX complète"""

        # Détermine le type d'entrée (article par défaut)
        entry_type = "article"

        # Prépare les champs
        fields = []

        if pivot.auteur:
            fields.append(f'  author = {{{self._escape_bibtex(pivot.auteur)}}}')

        if pivot.titre:
            fields.append(f'  title = {{{self._escape_bibtex(pivot.titre)}}}')

        if pivot.journal_clean:
            fields.append(f'  journal = {{{self._escape_bibtex(pivot.journal_clean)}}}')
        elif pivot.journal:
            fields.append(f'  journal = {{{self._escape_bibtex(pivot.journal)}}}')

        if pivot.annee:
            fields.append(f'  year = {{{pivot.annee}}}')

        if pivot.mois:
            month_names = {
                1: "jan", 2: "feb", 3: "mar", 4: "apr",
                5: "may", 6: "jun", 7: "jul", 8: "aug",
                9: "sep", 10: "oct", 11: "nov", 12: "dec"
            }
            if pivot.mois in month_names:
                fields.append(f'  month = {{{month_names[pivot.mois]}}}')

        if pivot.url:
            fields.append(f'  url = {{{pivot.url}}}')

        if pivot.langue:
            fields.append(f'  language = {{{pivot.langue}}}')


        # Ajoute un abstract basé sur les premières lignes du texte
        if pivot.texte:
            # Prend les 200 premiers caractères comme résumé
            abstract = pivot.texte[:200] + "..." if len(pivot.texte) > 200 else pivot.texte
            fields.append(f'  abstract = {{{self._escape_bibtex(abstract)}}}')

        # Assemble l'entrée
        fields_str = ",\n".join(fields)
        return f"@{entry_type}{{{key},\n{fields_str}\n}}"