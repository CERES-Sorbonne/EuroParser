from random import sample
from itertools import chain


from colour import Color
import numpy as np
from tqdm.auto import tqdm
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_distances as pairwise_cos_dist

from europarser.models import Pivot



def doublon_avance(pivots: List[Pivot], taillegroupe : int, NB_PIVOTS : int = 50) -> List[Pivot]:
    tqdm.write("\nDédoublonage avancé")
    with tqdm(total=2, desc = "Calcul des vecteurs BoW") as pbar:
        avg = np.mean([len(e["texte"]) for e in pivots])
        docspivots = sample(pivots, NB_PIVOTS)

        #On crée les vecteurs pour les textes (coordonnée n = occurences du mot de position n dans la liste de vocabulaire)
        vocab = set(' '.join([e["texte"] for e in docspivots]).lower().split())
        vectorizer = TfidfVectorizer(stop_words = ("english"), vocabulary = vocab)
        pbar.update()
        tf = vectorizer.fit_transform([e["texte"] for e in pivots])
        pbar.update()
        arrtf = tf.toarray()

        #On sépare les textes en groupes de même taille, en fonction de leur longueur
        pivots = sorted(pivots, key=lambda pivot: len(pivots["texte"]))
        nbgroupes = 1 + (len(pivots) // taillegroupe)
        groupes = [pivots[i*taillegroupe:(i+1)*taillegroupe] for i in range(nbgroupes)]

    colors = [Color("blue")] + list(Color("blue").range_to(Color("green"),nbgroupes))
    manualpbar = tqdm(groupes, desc="Calcul des vecteurs seconds / supression")
    for i, groupe in enumerate(manualpbar, 1):
        manualpbar.colour = colors[i].hex_l
        #Array de tous les vecteurs 2, un texte par ligne comparé a chaque pivot par colonne
        vect1_pivot = np.array([arrtf[i] * (avg / len(e["texte"])) for i, e in enumerate(docspivots)], dtype = np.half)
        vect1_non_pivot = np.array([arrtf[i] * (avg / len(e["texte"])) for i, e in enumerate(groupe)], dtype = np.half)
        array_vecteurs = pairwise_cos_dist(vect1_non_pivot, vect1_pivot)
        del vect1_non_pivot, vect1_pivot

        #Matrice de la distance cosinus entre chaque texte du corpus, chaque intersection [x,y] donnant
        #la distance entre les textes de rang x et y
        matrice_cosine = pairwise_cos_dist(array_vecteurs)
        del array_vecteurs

        #Permet de faire abstraction de la distance nulle du texte n avec lui-même et ne pas le remonter comme doublon
        for i in range(np.shape(matrice_cosine)[0]): 
            matrice_cosine[i,i] = 1
        #Liste de toutes les distances faibles --> Doublons
        lst_doublons = np.transpose(np.nonzero(matrice_cosine < 0.00001)).tolist()

        del matrice_cosine

        for e in lst_doublons:
            lst_doublons.remove([e[1], e[0]])

        #Nous permet de supprimer directement les doublons par l'index vu que l'élement reste a sa place (seuls ceux qui suivent ont étés supprimés)
        doublons = sorted([e[1] for e in lst_doublons], reverse = True) 
        del lst_doublons

        for db in doublons:
            del groupe[db]

        del doublons
    
    pivots = list(chain.from_iterable(groupes))
    tqdm.write(f"Dédoublonage avancé : Il reste désormais {len(pivot)} articles.")
    return pivots