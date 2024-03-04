# Près de chez vous - Projet de L1

*Près de chez vous* est un site web qui permet de connaître tous les équipements (commerce, services, santé...) ou seulement certains (maternelle,salon de coiffure...) qui se trouvent autour d'un endroit donné en France.

Les paramètres de connexion au sgbd (mysql) se font via le fichier "*Settings.txt*".

Version de php : 7.4.26     |      Version de mysql : 8.0.27     |     Version de python : 3.8.4 (les dépendances pour chaque fichier sont précisées dans `Dependances.txt`)

Ce site utilise le moteur de template Twig. Par conséquent tous les fichiers du site sont contenus dans le dossier `templates`. Le seul fichier php qui n'a pas été créé avec l'implantation de Twig est `index.php`.

Les dossiers `sql` et `csv` ont été compressés pour des raisons de stockage, ils sont à décompresser après le téléchargement.

Tous les fichiers .sql sont contenus dans `Base de donnees/sql`. `CreationTables` contient seulement les tables. `DATABASE_PresDeChezVous.sql` contient toute la base de données (y compris les tables), `DATABASE_PresDeChezVous.zip` en est sa version compressée.

Le fichier `ScriptSQLToBDD.py` importe `DATABASE_PresDeChezVous.sql` dans la base mysql lorsqu'il est executé. Il a l'avantage d'afficher l'avancement au fur et à mesure de l'importation et de s'affranchir de tout ce qui est problèmes de réglages d'importation, par exemple des limite de tailles de fichier ou des limites de temps d'importation.

Le contenu du dossier `csv` et le fichier `ScriptToSQL` sont inutiles. Ils ont seulement servi à la première création de la base de données.

<https://github.com/Anomaaaa/PresDeChezVous>
