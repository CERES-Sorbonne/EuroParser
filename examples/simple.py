import os.path

from europarser import process
import json

if __name__ == "__main__":
    from europarser import FileToTransform, pipeline
    import os

    path = r'C:\Users\Utilisateur\Downloads\corpus html clara\corpus html clara'

    files = [os.path.join(path, x) for x in os.listdir(path)]
    files_to_transform = []

    for f in files:
        with open(f, 'r', encoding='utf-8') as text:
            files_to_transform.append(FileToTransform(file=text.read(), name='osef.txt'))

    pivots, _ = pipeline(files_to_transform, output="pivot")
    with open(os.path.join(r'D:\Alie\Documents\Projets\Dedoublonnage', 'corpus2.json'), 'w', encoding='utf-8') as f:
        pivots = json.loads(pivots)
        json.dump(pivots, f, indent=4, ensure_ascii=False)