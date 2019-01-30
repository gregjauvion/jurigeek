
# Gestion des données

Pour chaque source de données, on dispose des briques suivantes :

* Table dans la base de données MySQL. Cette table contient a minima les deux colonnes suivantes : PK_ID, TEXT. Les autres colonnes sont spécifiques à chaque source de données.
* Fonction permettant de dumper le contenu de la table dans un fichier (avec possibilité de filtrer). Chaque ligne du fichier contient un json contenant uniquement les 2 clés pk_id et text (pour limiter la taille des dumps)

Les modèles et le serveur utilisé en prod sont appris sur les dumps de l'ensemble des sources de données (la lecture de l'intégralité des tables serait trop longue).
Les dumps de prod sont pour l'instant dans /home/gregoire/data/ (on pourrait les mettre dans un user commun).

## Cas particulier (et temporaire) pour le dump des bases legi

Les identifiants des textes de loi, dans article, sont les colonnes <i>cid</i>. Ils sont préfixés par une chaîne de 8  caractères ( "LEGITEXT" ou "JORFTEXT")
, et suffixés par un entier unique. 

Ainsi, afin d'effectuer un dump des bases legi avec un identifiant unique PK_ID, nous proposons de laisser le suffixe, et de préfixer par 1 si le cid commence par LEGITEXT, 2 sinon.
Une requête SQLITE d'extraction des PK ID serait la suivante : 

~~~~
select CASE WHEN substr(cid, 1, 8) = 'LEGI' THEN 1 ELSE 2 END || substr(cid, 9) pk_id from articles limit 10 ;
~~~~


