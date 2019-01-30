
# A faire

## Gestion des données
* Insertions concurrentes, tables temporaires
* Scraping Curia
* Réconcilier scraping Curia / Legifrance
* Parsing Curia : à faire
* Parsing legifrance : récupérer le ext_id, je ne suis pas sûr qu'il soit récupéré tout le temps

## Modèles
* Le script models/juris_fr_gensim.py permet d'apprendre un word2vec ou un doc2vec. Il faudrait le tuner (notamment, la méthode gensim score() renvoie je crois la likelihood moyenne d'une observation selon le modèle, elle peut être utile pour comparer 2 modèles)
* Essayer de faire mieux que gensim (avec tensorflow ou autre)

## Interface
* Faire une page html avec zone de texte, qui appelle le serveur de calcul et affiche les N documents les plus proches du texte.
* Pour pouvoir analyser la pertinence d'un modèle : visualisation 2D où passer la souris sur un point nous affiche les N voisins
* Dans le json à visualiser, renseigner les paramètres du modèle ayant produit le json
