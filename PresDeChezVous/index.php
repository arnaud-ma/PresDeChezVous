<?php

use LDAP\Result;

require 'vendor/autoload.php';
error_reporting(E_ALL);
session_start();
// Routing

$page = 'Accueil';
if (isset($_GET['p'])) {
    $page = $_GET['p'];
};


$ErreurBool = false;

$ext = '.html.twig'; #Extension des templates


// Paramètres Twig
$loader = new \Twig\Loader\FilesystemLoader(__DIR__ . '/templates/Pages');
$options = [
    'cache ' => false, //__DIR__ . '/tmp'
];
global $twig;
$twig = new \Twig\Environment($loader, $options);

// Fonction str_contains pas présent dans php 7
function str_contains(string $haystack, string $needle): bool
{
    return '' === $needle || false !== strpos($haystack, $needle);
}

#Fonction renvoie false si n'importe quoi mais pas false
function is_false($valeur){
    if ($valeur === false){
        return true;
    }else{
        return false; 
    }
}
// MYSQL

#Lecture settings.txt connexion à la base. Retourne un tableau avec toutes les valeurs

#Connexions base de donnees / api 
#-------------------------------------------------------------------------------------------------------------------

#Si pas mis Reader et writer
function IdNull($table,$Id){
    if (strlen($table[$Id]==0)){
    $table[$Id] = $table['ROOT'];
    $table['PASSWORD_'.$Id] = $table['PASSWORD_ROOT'];
    }
    return $table;
}

#Recupère les données de settings.txt
function RSettings(){
    $A = Array();
    $settings = (file('..\Settings.txt'));
    foreach($settings as $ligne){
        $ligne = trim(str_replace(' ','',$ligne));
        if (str_contains($ligne,':')){
            $ligne = explode(':',$ligne);
            $A[$ligne[0]] = $ligne[1];
        }
    }
    // Si pas d'utilisateur reader ou writer
    $A = IdNull(IdNull($A,'READER'),'WRITER');
    return $A;
}

#Gestion des erreurs de connexion (hors service, à revoir pour redirection vers page erreur)
function IsConnect($dbConnect){
    if (mysqli_connect_errno()){
        global $page,$msg_erreur,$Erreur;
        $page = 'Erreur';
        $msg_erreur = "Désolé, il semble qu'une erreur est apparue lors de la connexion à la base de donnéees";
        $Erreur = mysqli_connect_error();
            return false;
    } else {
        $Erreur = [
            'message'=> "Tout se passe bien, comment êtes-vous arrivé sur cette page d'erreur ?",
            'detail' => ''];
        return $dbConnect;
    }
}


#Connexion à la base
function dbConnect($user){
    $A = RSettings();
    $dbConnect = mysqli_connect( $A['HOST'] , $A[$user] , $A['PASSWORD_'.$user] , $A['DATABASE'] , intval($A['PORT']));
    $dbConnect = IsConnect($dbConnect);
    return $dbConnect;
}

#Retourne les catégories
function Categories($id,$Lib,$foreign,$table){
    if ($foreign == 'None'){
        $req = "SELECT $id,$Lib FROM `$table`";
    } else{
        $req = "SELECT $id,$Lib,$foreign FROM `$table`";
    }
    $link = dbConnect('READER');
    if ($link){
        $sql = mysqli_query($link,$req);
        $data = [];
        mysqli_close($link);
            while ($ligne = $sql->fetch_assoc()) {
            $data[$ligne[$Lib]] = $ligne;
        }
        return $data;
    }
}

#API Adresse
#-------------------------------------------------------------------------------------------------------------------


#API Adresse 
function ExecAPI($url){
    $curl = curl_init($url);
    $options = [
        CURLOPT_CAINFO => __DIR__ . DIRECTORY_SEPARATOR .'certificatSSL.cer',
        CURLOPT_RETURNTRANSFER => true  ];
        curl_setopt_array($curl,$options);
        $data = curl_exec($curl);
    if($data === false ){
        global $page,$Erreur,$msg_erreur;
        $page = 'Erreur';
        $msg_erreur = "Désolé, il semble qu'une erreur est apparue lors de la récupération des adresses";
        $Erreur = curl_error($curl);
    } else {
        $data = json_decode($data,true);
        return $data;
    }
}

#Recupère le résultat de la recherche
#-------------------------------------------------------------------------------------------------------------------

#Recupère la valeur en post ou en session
function post($valeur){
    if (isset($_POST[$valeur])){
        $_SESSION[$valeur] = $_POST[$valeur];
        return $_POST[$valeur];
    }elseif (isset($_SESSION[$valeur])) {
        return $_SESSION[$valeur];
    }else{
        return false;  
    }
}


#Recupère le nombre d'éléments par page, 20 par défaut
function getNbResult(){
    if (is_false(post("NbResult"))){
        $NbResult = 20;
    } else{
        $NbResult = post('NbResult');
    }
    return $NbResult;
}

#Recupère le numéro de la page de recherche, 1 par défaut
function getnPage(){
    if (isset($_GET['n'])){
        $n = $_GET['n'];
    }else{
        $n = 1;
    }
    return $n;
}

#Ecrit la requête du INSERT INTO des adresses
function EcritureAdresse($table){
    $req = "INSERT INTO `adresse` (`LibAdresse`, `IdLocalisation`) VALUES ";
    foreach ($table as $adresse) {
        $req.= "('" . $adresse['Adresse'] . "', " . $adresse['IdLocalisation'] . "),";     
    }
    $req = trim($req,',') . ';'; #Remplace la , de la fin par un ;
    return $req;
}



#Recupère les données  de la recherche générale
function ResultSearch(){
    $start = microtime(true);   #Pour renvoyer le temps
    $Values = [];    #Tableau auquel on va rajouter les valeurs post pour les avoir en mémoire (la session le fait quand même mais c'est pour l'affichage)
    #Gestion des erreurs
    if (is_false(post('Recherche'))){
        return "Aucun résultat (peut être que vous n'avez sélectionné aucun type d'équipement ?)";
    } 
    if (is_false(post("Adresse"))){
        return "Erreur recupération de l'adresse";
    }
    if (is_false(post("Categorie")) or is_false(post("SousCategorie")) or is_false(post("Type"))){
        return "Erreur récupération des catégories";
    }

    #Recupère region (si besoin, pas pour le moment), Code et libellé Departement, localisation x et y et adresse complète de l'adresse saisie par l'utilisateur
    $Adresse = post('Adresse');  #string
    $Values['Adresse'] = $Adresse;
    $Adresse = str_replace(' ','+',$Adresse);                       #On recupère le premier résultat
    $url = 'https://api-adresse.data.gouv.fr/search/?q='.$Adresse.'&limit=1'; 
    $data = ExecAPI($url);
    if (count($data['features']) == 0 ){
        return "Désolé, il semble qu'aucun lieu ne corresponde à cette adresse";
    }
    $X = $data['features'][0]['properties']['x'];
    $Y = $data['features'][0]['properties']['y'];
    $context = $data['features'][0]['properties']['context']; #string CodeDepartement, Departement, Region 
    $listcontext = (explode(',',$context)); #Liste du string
    $region =  trim(end($listcontext),' '); #Prend region et enleve premier espace
    $CodeDepartement = $listcontext[0];
    $LibDepartement = trim($listcontext[1],' ');
    $AdresseRecherche = $data['features'][0]['properties']['label'];
    #Recupère les catégories séléctionnées par l'utilisateur
    $IdCategorie       = post('Categorie'); 
    $IdSousCategorie   = post('SousCategorie');
    $IdType            = post('Type') ;
    $Values['Categorie'] = $IdCategorie;
    $Values['SousCategorie'] = $IdSousCategorie;
    $Values['Type'] = $IdType;
    #Mise en forme des requêtes mysql
    $req_Enseignement = '';
    $req_Culture = '';
    if (in_array(12, $IdCategorie)){ #Si catégorie enseignement
        $req_Enseignement = ',Cantine,LyceeCPGE,EducPrio,Internat,RPIC,Secteur';
    }
    if (in_array(15, $IdCategorie)){ #Si catégorie sport culture
        $req_Culture = ',Couvert,Eclaire,NbAireJeu,NbSalles';
    }
    $Distance = "DistanceXY(UTMX, $X ,UTMY, $Y )";
    $req = " FROM equipement";
    $req.= " INNER JOIN commune USING(CodeCommune)";
    $req.= " INNER JOIN departement USING(CodeDepartement)";
    $req.= " INNER JOIN region USING(CodeRegion)";
    $req.= " INNER JOIN coordonnees USING(IdLocalisation)";
    $req.= " INNER JOIN type USING(IdType)";
    $req.= " INNER JOIN souscategorie USING(IdSousCategorie)";
    $req.= " INNER JOIN categorie USING(IdCategorie)";
    $req.= " LEFT OUTER JOIN adresse USING(IdLocalisation)";
    $req.= " WHERE CodeDepartement = '$CodeDepartement' AND (";

    foreach ($IdType as $Type) { #Le code type est de la forme XYAB, X Id Categorie, XY IdSousCategorie, mais passé en base 10
        $Type32 = base_convert($Type,10,32);            #On itère chaque catégorie, souscatégorie puis type,                                                        
        foreach ($IdSousCategorie as $SousCategorie) { # # en ajoutant à la requête seulement si le type, la souscategorie et la catégorie sont séléctionnés
            $SousCategorie32 = base_convert($SousCategorie,10,32);
            if (substr($Type32,0,2) == $SousCategorie32) {
                foreach ($IdCategorie as $Categorie) {
                    $Categorie32 = base_convert($Categorie,10,32);
                    if (substr($Type32,0,1) == $Categorie32){
                        $req.= " OR IdType = $Type";
                    }
                }
            }
        }
    }
    $req.=' )';
    $pos = strpos($req, 'OR');  
    if ($pos !== false) {
    $req = substr_replace($req, '', $pos , strlen('OR')); #Supprime le dernier OR
    }                           
    
    $NbResult = getNbResult();
    $nPage = getnPage();
    $limit = ($nPage-1)*$NbResult;
                            #Concat au cas où Adresse vide et donc unique avec une autre
    $reqSelect = "SELECT Concat_WS('',LibAdresse,'-',IdType) as AdresseType, $Distance as Distance, IdLocalisation,LibCategorie ,LatitudeGPS,LongitudeGPS,QualiteXY,LibAdresse, Couleur, LibType".$req_Enseignement.$req_Culture.$req;
    $reqSelect.= "GROUP BY (AdresseType)"; #Group by pour éviter les doublons possibles, (dans la base de l'INSEE certaines données ont été changées mais l'ancienne n'a pas été supprimée)
    
    $reqCount  = "SELECT Count(*) as count FROM (". $reqSelect .") as T"; #Le nombre de résultats totaux (count(*) en sous requête)
    
    $reqSelect.= " ORDER BY $Distance ASC LIMIT $limit,$NbResult;"; #Group by pour éviter les doublons possibles, (dans la base de l'INSEE certaines données ont été changées mais l'ancienne n'a pas été supprimée)
    $data = [];
    $link = dbConnect('READER');
    if ($link){
        $sql = mysqli_query($link,$reqSelect);
        $sqlCount = mysqli_query($link,$reqCount);
        if (!$sql) {
            return  "Désolé, il semble qu'une erreur est apparue lors de la requête pour afficher les résultats".'<br>'. "Détails : ".mysqli_error($link);
        mysqli_close($link);
        }
    } else{
        return "Désolé, il semble qu'une erreur est apparue lors de la requête pour afficher les résultats <br> Détails : ".mysqli_error($link);
        }
    if($sql->num_rows == 0){    #Si aucun résultat avec limit (surement dernière page)
        return "Aucun resultat pour cette page";
    }
    $data = []; #Données finales
    $ListreqAdresse = []; #Liste des adresses obtenues avec l'api
    $NoAdress = 'Aucune adresse disponible'; #Message si aucune adresse trouvée par l'api / base de donnée / api en panne / mauvaise connexion
    while ($ligne = $sql->fetch_assoc()) {
        if ($ligne['LibAdresse'] === $NoAdress){    # $NoAdress dans la base de donnée => api a déjà rien trouvé, pas d'adresse
            $ligne['LibAdresse'] = $NoAdress;
            echo 0;
        } 
        elseif (is_null($ligne['LibAdresse'])){
            $url = 'https://api-adresse.data.gouv.fr/reverse/?lon='.$ligne['LongitudeGPS'].'&lat='.$ligne['LatitudeGPS'].'&limit=1'; 
            $dataAPI = ExecAPI($url);
            if (!isset ($dataAPI['features'][0]) ) {
                $Adresse = $NoAdress;
                echo 1 ;  
                echo $ligne['LongitudeGPS'].'-'.$ligne['LatitudeGPS'].'\n\n';
            }
            elseif (!isset ($dataAPI['features'][0]['properties'])){
                $Adresse = $NoAdress;
                echo 2;
            }
            elseif  (!isset ($dataAPI['features'][0]['properties']['label'])){
                $Adresse = $NoAdress;
                echo 3;
            }
            else{
                $Adresse = $dataAPI['features'][0]['properties']['label'];
                echo 4;
            }
            $ligne['LibAdresse'] = $Adresse;
            array_push($ListreqAdresse,[    #Ajoute l'adresse dans la liste des adresses
                'Adresse'        => $Adresse,
                'IdLocalisation' => $ligne['IdLocalisation'] ]);
        }
        array_push($data,$ligne);   #Ajoute la ligne dans la liste des données finales
    }
    $data['LibDepartement'] = $LibDepartement;
    $data['AdresseRecherche'] = $AdresseRecherche;
    $count = $sqlCount->fetch_assoc()['count'];
    if (count($ListreqAdresse) != 0){
        $req = EcritureAdresse($ListreqAdresse);    #Insère les adresses dans la base de données
        $link = dbConnect('WRITER');
        if ($link){
            mysqli_query($link,$req);
        }
        mysqli_close($link);  
    }
    $end = microtime(true); 
    return [
        'data'      => $data, #array de requête principale
        'count'     => $count,  #int
        'time'      => $end-$start, #float
        'Values'   => $Values,  #array contient Categorie,SousCategorie,Type (en id) et Adresse (saisie)
    ];
}


#Recupère le nombre d'équipement total
#-------------------------------------------------------------------------------------------------------------------

function nbEquipements(){
    $req = "SELECT COUNT(*) FROM equipement";
    $link = dbConnect('READER');
    if ($link){
        $sql = mysqli_query($link,$req);
        mysqli_close($link);
        return $sql->fetch_assoc()['COUNT(*)'];
    } else{
        return '? (Erreur)';}
}

function ValueCategories($Categories,$type){
    $data = [];
    foreach ($Categories as $Categorie) {
        array_push($data,$Categorie['Id'.$type]);
    }
    return $data;
}
#-------------------------------------------------------------------------------------------------------------------
#Envoi des mails 

function EnvoiMail(){
    $nom = post('nom');
    $mail = post('mail');
    $sujet = post('sujet');
    $message = post('message');
    $envoi = post('envoi');
    if (!is_false($envoi)){
        $to = 'arnaud.mabit@etu.univ-tours.fr, malo.lequintrec@etu.univ-tours , clement.pouilleau@etu.univ-tours.fr,baptsite.pichon@etu.univ-tours.fr';
        $subject = "PresDeChezVous Contactez-nous $sujet ";
        $headers = "From : $nom \r\n mail : $mail"."\r\n"."Sujet : $sujet";
        if (!@mail($to,$subject,$message,$headers)){
            return "Erreur lors de l'envoi (peut être serveur SMTP non configuré)";
        }
        else{
            echo mail($to,$subject,$message,$headers);
            return 'message bien envoyé !';
        }
    }
}


#-------------------------------------------------------------------------------------------------------------------

#Variables utiles pour l'affichage

$Categories =  [
    'Categorie'     => Categories('IdCategorie','LibCategorie','None','Categorie'),
    'SousCategorie' => Categories('IdSousCategorie','LibSousCategorie','IdCategorie','SousCategorie'),
    'Type'          => Categories('IdType','LibType','IdSousCategorie','Type')
];

// echo var_dump($Categories);

#Pour avoir la table comme si on avait tout sélectionné sur la page accueil
function Values($Categories){
    $Values = [];
    foreach ($Categories as $Categorie => $table) {
        $Values[$Categorie] = ValueCategories($table,$Categorie);
    }
    return $Values;
}

// echo var_dump(Values($Categories));

$Precision = [
    'Bonne' => '< 100m',
    'Acceptable' => '100m - 500m',
    'Mauvaise' => '> 500m (mauvaise)'
];
#-------------------------------------------------------------------------------------------------------------------
// Affichage des pages

switch ($page){
    case 'Accueil':
        echo $twig->render('Accueil'.$ext , [
                                            'Categories'    => $Categories,
                                            'Result'        => Array('Values'=>Values($Categories)),
                                            'NbEquipements' => nbEquipements(),
                                            'NbResult'      => getNbResult()
                                        ]);
        break;
    case 'Connexion':
        echo $twig->render('Connexion'.$ext);
        break;
    case 'Contactez-nous':
        echo $twig->render('Contactez-nous'.$ext , [
                                                'Envoi' => EnvoiMail(),
                                            ]);
        break;
    case 'Mentions_legales':
        echo $twig->render('Mentions_legales'.$ext);
        break;
    case 'Mon_Compte':
        echo $twig->render('Mon_Compte'.$ext);
        break;
    case 'Recherche':
        echo $twig->render('Recherche'.$ext,[
                                            'Categories'=> $Categories,
                                            'Result'    =>ResultSearch(),
                                            'Precision' => $Precision,
                                            'NbResult'  => getNbResult(),
                                            'n'         => getnPage()
                                            ] ); 
        break;
    case 'Favoris':
        echo $twig->render('Favoris'.$ext);
        break;
    case 'Erreur':
        echo $twig->render('Erreur'.$ext , ['Erreur' => $Erreur,
                                            'msg_erreur' => $msg_erreur 
                                        ]);

    }

?>