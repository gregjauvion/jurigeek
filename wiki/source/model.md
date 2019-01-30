
# Modèles utilisés

## Serveur de similarité

Le serveur est construit avec un modèle sérialisé (pour l'instant un modèle Doc2Vec gensim). A la construction, il ne contient aucun corpus.

L'ajout d'un corpus de documents se fait par la requête POST load/ accompagnée du json {'key': {KEY}, 'path': {PATH}}. {KEY} identifie le type de corpus (ex. 'jurisprudence_fr', 'law', ...), et {PATH} donne le chemin vers un dump de documents (i.e. chaque ligne du fichier doit être un json avec les clés pk_id et text). Le serveur stocke pour chaque document un embedding construit à l'aide du modèle ainsi que le pk_id du document.

L'appel de la requête load/ avec une {KEY} connue par le serveur écrase le corpus avec les documents contenus dans {PATH}.

La requête POST similar/ accompagnée d'un document renverra les N documents les plus proches pour chaque corpus connu par le serveur (ainsi que le score de similarité). La réponse est du type {KEY_1: {[{'document': PK_ID, 'similarity': SIMILARITY}, ...]}, KEY_2: ...}.

## Serveur de mots-clés

Le serveur de mots clés est construit avec un modèle TF-IDF sérialisé (pour l'instant l'apprentissage du modèle est fait dans le code du serveur, TODO). Le modèle TF-IDF est appris idéalement sur l'ensemble des dumps.

La requête POST keywords/ accompagnée d'un document renvoie les mots clés du document.
