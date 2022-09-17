#Ce script sert à récupérer les données csv pour les mettre dans le sgbd sql. On n'en aura plus besoin une fois tout transformé
import pandas as pd
import numpy as np
from sqlalchemy import create_engine,text,Table,MetaData,Column,Integer
import pyproj
import time
import requests as rq
from index import AbsolutePath,ConnectionRootMysql
from tqdm import tqdm
#pip install pymysql en +


#Importation des paramètres de connexion du sgbd (forcément mysql ici, sinon changer ligne 30 'mysql' par le sgbd approprié)
engine = ConnectionRootMysql()
sqlEngine = create_engine(engine,pool_recycle=3600)

#Plus le chiffre est grand plus l'execution est rapide mais + de risque de surcharge de mémoire
tailleTable = 3000 #!Pas prévu pour en dessous de 1000

#------------------------------------------------------------------------------------------------------

#Reinitialiser toutes les tables
def Reinit(fichiersql):
    fichiersql = AbsolutePath(fichiersql)
    dbConection = sqlEngine.connect()           #Connexion sgbd
    fichiersql = open(fichiersql,'r')           #Ouverture fichier sql
    requete = ''                                #Initialisation requête
    for line in fichiersql:                     #Iteration de chaque ligne du fichier sql
        line = line.replace('\n','')            #Supprime les sauts de ligne
        if not line.startswith('#'):            #Supprime les commentaires
            requete += line                     #Ajoute la ligne à la requête
        if requete.endswith(';'):               #Si ; execute la requete
            dbConection.execute(text(requete))
            requete = ''                        #Remet à 0 la requete
    fichiersql.close()                          #Deconnexion sgbd
    dbConection.close()                         #Fermeture fichier

#------------------------------------------------------------------------------------------------------

def Categorie(fichier):
    fichier = AbsolutePath(fichier)
    table = pd.read_csv(fichier,sep=';',encoding = 'utf8')
    table = table.rename(columns = {'TYPEQU':'CodeType','LIB_EQUIP':'LibType','SDOM':'IdSousCategorie','LIB_SDOM':'LibSousCategorie','DOM':'IdCategorie','LIB_DOM':'LibCategorie'})
                        #On garde CodeType et IdType (str et int)
    table['IdType'] = table['CodeType'].apply(lambda x: int(x,32))                    #Transforme l'Id str en int (base 32 à 10)
    table['IdSousCategorie'] = table['IdSousCategorie'].apply(lambda x: int(x,32))
    table['IdCategorie'] = table['IdCategorie'].apply(lambda x: int(x,32))

    tableCat = table.reindex(columns=['IdCategorie','LibCategorie']) #Bonne colonnes
    tableCat = tableCat.drop_duplicates(subset=['IdCategorie'])     #Supprime lignes identiques
    tableSousCat = table.reindex(columns=['IdSousCategorie','LibSousCategorie','IdCategorie'])
    tableSousCat = tableSousCat.drop_duplicates(subset=['IdSousCategorie'])
    tableType = table.reindex(columns=['IdType','LibType','IdSousCategorie','CodeType'])

    dbConnection  = sqlEngine.connect() #Ouvre la connexion au sgbd
    tableCat.to_sql('categorie', dbConnection, if_exists='append',index=False)
    tableSousCat.to_sql('souscategorie', dbConnection, if_exists='append',index=False)
    tableType.to_sql('type', dbConnection, if_exists='append',index=False)
    dbConnection.close() #Ferme la connexion au sgbd

#------------------------------------------------------------------------------------------------------

def CommuneDepRegion(fichierRegion,fichierDep,fichierCommune):
    fichierRegion = AbsolutePath(fichierRegion)
    fichierDep = AbsolutePath(fichierDep)
    fichierCommune = AbsolutePath(fichierCommune)
    print(fichierCommune + '\n \n Chargement... \n')

    tableRegion = pd.read_csv(fichierRegion,sep=',',encoding = 'utf8')
    tableRegion = tableRegion.rename(columns={'REG':'CodeRegion','LIBELLE':'LibRegion'})
    tableRegion = tableRegion.reindex(columns=['CodeRegion','LibRegion']) #On a les colonnes : CodeRegion ; LibRegion

    tableDep = pd.read_csv(fichierDep,sep=',',encoding = 'utf8')
    tableDep = tableDep.rename(columns={'REG':'CodeRegion','LIBELLE':'LibDepartement','DEP':'CodeDepartement'})
    tableDep = tableDep.reindex(columns=['CodeDepartement','LibDepartement','CodeRegion']) #On a les colonnes : CodeRegion ; LibRegion
    tableDep['CodeDepartement'] = tableDep['CodeDepartement'].replace('2A','210').replace('2B','211') #Corse dep en int

    dbConnection  = sqlEngine.connect() #Ouvre la connexion au sgbd

    #Exporte les 2 tables dans le sgbd
    tableRegion.to_sql('region', dbConnection, if_exists='append',index=False)
    tableDep.to_sql('departement', dbConnection, if_exists='append',index=False)

    table = pd.read_csv(fichierCommune,sep=',',encoding = 'utf8' , dtype={'COMPARENT':'str'} )
    table = table.query("COM != COMPARENT")
    table = table.replace('2A','210',regex=True).replace('2B','211',regex=True) #Corse dep en int


    table['DEP'] = np.where(table['DEP'].isnull(), #Si departement pas noté
                    np.where( 96000 < table['COM'].astype('int32').any() < 98000 , table['COM'].astype(str).str[:3], #Outre Mer
                            table['COM'].astype(str).str[:2] ) #France métropolitaine
                    , table['DEP'] )    #Si departement noté
    table = table.astype({'DEP':'int16'})
    table = table.astype({'COM':'int32'}) #CodeCommune en int
    table = table.rename(columns={'COM':'CodeCommune','DEP':'CodeDepartement','LIBELLE':'LibCommune'})
    table = table.reindex(columns=['CodeCommune','LibCommune','CodeDepartement']) #Supprime colonnes inutiles

    table.to_sql('commune', dbConnection, if_exists='append',index=False) #Exporte dans le sgbd

    dbConnection.close() #Ferme la connexion au sgbd

#------------------------------------------------------------------------------------------------------


def Type(fichier): #Mettre les types de chaque colonne csv en string (il faut forcément le spécifier en lecture pandas)
    with open(fichier) as f:
        Colonnes = next(f).strip('\n').split(';')
    return {colonne:'string' for colonne in Colonnes}

def LectureCSV(fichier):
    return pd.read_csv(fichier,sep=';', chunksize=tailleTable, encoding='utf8',dtype=Type(fichier))

def NbTables(fichier):   #Compte le nombre de lignes dans le csv (-1 pour titre des colonnes),  divise par le nombre de lignes par table et prend la partie entière supérieure
    return np.ceil((sum(1 for row in open(fichier,'r'))-1) / tailleTable)

def Avancement(x,nb): 
    return str(round((x)/nb*100,1))+' %'

def Converter(coIn,coOut,x,y):
    transformer = pyproj.Transformer.from_crs(coIn, coOut)
    return transformer.transform(x,y)

def ConverterLonLat(epsg,x,y):
    return Converter('epsg:'+str(epsg),"+proj=lonlat",x,y)  #Renvoie le tuple (longitude,latitude)


def Equipement(fichierEns,fichierEnsgt,fichierSL):
    fichierEns = AbsolutePath(fichierEns)
    fichierEnsgt = AbsolutePath(fichierEnsgt)
    fichierSL = AbsolutePath(fichierSL)
    print(fichierEns+ '\n'  + fichierEnsgt +'\n' + fichierSL + ' \n \n Chargement... \n')
    tables = {'Ens':LectureCSV(fichierEns) , 'Ensgt':LectureCSV(fichierEnsgt) , 'SL':LectureCSV(fichierSL)}
    nbTables = {'Ens':NbTables(fichierEns) , 'Ensgt':NbTables(fichierEnsgt) , 'SL':NbTables(fichierSL)}
    TotNbTables = sum(nbTables.values())
    AttEnsgt = ['Cantine','MaternellePrimaire','LyceeCPGE','EducPrio','Internat','RPIC','Secteur'] #Colonnes propres à table Enseignement
    AttSL =    ['Couvert' , 'Eclaire' , 'NbAireJeu' , 'NbSalles']                                  #                         Sport-Loisir
    Att = AttEnsgt + AttSL
    listTables = []
    for table in tqdm(tables['Ens'],desc="Lecture Ensemble",total=nbTables['Ens']): #Tables ensemble
        table = table[~table["TYPEQU"].str.contains('C')] #Suppr enseignement
        table = table[~table["TYPEQU"].str.contains('F')] #Suppr sport-loisir

        for att in Att:   #Valeur nulle pour les attributs de ensgt et SL
            table[att] = np.nan #Preferable NaN à None pour les nombres
        listTables.append(table)

    for table in tqdm(tables['Ensgt'],desc="Lecture Enseignement",total=nbTables['Ensgt']): #Tables enseignements
        table = table.replace('X',np.nan) #Remplace le symbole "sans objet" par valeur nulle
        table = table.rename(columns={'CANTINE':'Cantine' , 'CL_PELEM':'MaternellePrimaire' ,'CL_PGE':'LyceeCPGE' ,
                                      'EP':'EducPrio' , 'INTERNAT':'Internat' , 'SECT':'Secteur'})
        for attSL in AttSL:
            table[attSL] = np.nan
        listTables.append(table)

    for table in tqdm(tables['SL'],desc="Lecture Sport-Loisir-Culture",total=nbTables['SL']): #Tables sport-loisir
        table = table.replace('X',np.nan)
        table = table.rename(columns={'COUVERT':'Couvert' , 'ECLAIRE':'Eclaire' ,
                                      'NB_AIRE_JEU':'NbAireJeu' , 'NBSALLES':'NbSalles'})
        for attEnsgt in AttEnsgt:
            table[attEnsgt] = np.nan
        listTables.append(table)
    #On a maintenant toutes les tables de chaque catégorie qui ont les mêmes colonnes
    DicTables = {'coordonnees':[],'equipement':[]} #Dictionnaire des tables initialisé
    
    for i,table in enumerate(tqdm(listTables,desc="Conversion coordonnees",total=TotNbTables)):
        table = table.rename(columns={'TYPEQU':'IdType' , 'DEPCOM':'CodeCommune' ,
                                      'LAMBERT_X':'utmx' , 'LAMBERT_Y':'utmy' , 'QUALITE_XY':'QualiteXY'})
        table = table.reindex(columns=Att + ['IdType','CodeCommune','utmx','utmy','QualiteXY'])  #Ordre colonnes
        table['IdType'] = table['IdType'].apply(lambda x: int(x,32))  #Transforme l'Id str en int (base 32 à 10)
        table['CodeCommune'] = table['CodeCommune'].replace('2A','210',regex=True).replace('2B','211',regex=True) #Corse
        table = table.dropna(subset=['utmx','utmy'])  #Supprime les equipements non géolocalisés <=>  valeur nulle dans X ou Y
        table = table.astype({'IdType':'Int64','CodeCommune':'Int32','utmx':'float','utmy':'float'}) #Type des colonnes qui sont des chiffres
        #Creation nouvelles colonnes longitude et latitude
        #On utilise pas geopandas car exceptions avec Outre mer. Plus simple de faire pour chaque ligne avec pyproj
        table['longitudegps'] = np.where(table['CodeCommune'].astype(str).str[:3] == '971', ConverterLonLat(5490,table.utmx,table.utmy)[0],  #Guadeloupe
                                np.where(table['CodeCommune'].astype(str).str[:3] == '972', ConverterLonLat(5490,table.utmx,table.utmy)[0],  #Martinique
                                np.where(table['CodeCommune'].astype(str).str[:3] == '973', ConverterLonLat(2972,table.utmx,table.utmy)[0],  #Guyane
                                np.where(table['CodeCommune'].astype(str).str[:3] == '974', ConverterLonLat(2975,table.utmx,table.utmy)[0],  #La Réunion
                                np.where(table['CodeCommune'].astype(str).str[:3] == '976', ConverterLonLat(5879,table.utmx,table.utmy)[0],  #Mayotte
                                                ConverterLonLat(2154,table.utmx,table.utmy)[0]))))) #France métropolitaine

        table['latitudegps'] = np.where(table['CodeCommune'].astype(str).str[:3] == '971', ConverterLonLat(5490,table.utmx,table.utmy)[1],  #Guadeloupe
                                np.where(table['CodeCommune'].astype(str).str[:3] == '972', ConverterLonLat(5490,table.utmx,table.utmy)[1],  #Martinique
                                np.where(table['CodeCommune'].astype(str).str[:3] == '973', ConverterLonLat(2972,table.utmx,table.utmy)[1],  #Guyane
                                np.where(table['CodeCommune'].astype(str).str[:3] == '974', ConverterLonLat(2975,table.utmx,table.utmy)[1],  #La Réunion
                                np.where(table['CodeCommune'].astype(str).str[:3] == '976', ConverterLonLat(5879,table.utmx,table.utmy)[1],  #Mayotte
                                                ConverterLonLat(2154,table.utmx,table.utmy)[1]))))) #France métropolitaine

        #Avoir une colonne IdLocalisation avec même id si même coordonnees
        table['xy'] = tuple(zip(table.utmx,table.utmy))     #Créer tuple (utmx,utmy) temporaire
        values = table['xy'].unique()                       #Supprime tous les tuples identiques et garder que le premier
        values = pd.Series(np.arange(len(values)), values)  #Créer un id pour chaque tuple unique
        table['IdLocalisation'] = (table['xy'].apply(values.get)+1)+i*tailleTable #Ajoute l'id à la df et l'adapte pour toutes les tables
        table = table.drop(columns='xy') #Supprime la colonne tuple temporaire

        tableCoo = table.reindex(columns=['IdLocalisation','latitudegps','longitudegps','utmx','utmy','QualiteXY'])
        tableCoo = tableCoo.drop_duplicates(subset=['utmx','utmy']) #Supprime lignes coordonnees identiques

        tableEquipement = table.reindex(columns=Att+['IdType','CodeCommune','IdLocalisation'])

        DicTables['equipement'].append(tableEquipement)
        DicTables['coordonnees'].append(tableCoo)
        #DicTables possède coordonnees : listTablesCoordonnee   et equipement : listTablesEquipement

    dbConnection  = sqlEngine.connect() #Ouvre la connexion au sgbd
    for listTables in tqdm(DicTables,desc="Importation"):
        table.to_sql(listTables,dbConnection,if_exists='append',index=False)
    dbConnection.close()

#------------------------------------------------------------------------------------------------------
tailleTableAdresse = 10 #! conseillé de mettre <1000

def roundw0(x,nbdigits): #Arrondir en gardant le 0 de la fin par exemple 2.30 au lieu de 2.3
    f = '{:.'+str(nbdigits)+'f}'
    return f.format(round(x, nbdigits))

def AvancementTime(temps,xtable,nbLignes): #Afficher le temps restant, temps moyen par iteration et temps total écoulé
    #Se base sur le temps moyen total pour faire le temps restant
    nbTables= np.ceil(nbLignes/tailleTableAdresse) 
    moy = temps/(xtable*tailleTableAdresse)
    restant = (nbTables-xtable)*tailleTableAdresse
    Avancement = str(roundw0((xtable)/nbTables*100,3))+' %'
    TR = time.strftime('%H:%M:%S', time.gmtime(moy*restant))
    print(Avancement,'  |    Temps restant :',TR,'  |    Temps moyen :',roundw0(moy,4),'s','  |    Temps écoulé :',time.strftime('%H:%M:%S', time.gmtime(temps)))

#Si erreur de connexion à l'api, retry 20 fois la même connexion
sess = rq.Session()
adapter = rq.adapters.HTTPAdapter(max_retries = 20)
sess.mount('http://', adapter)

def reverse_geocodeur(lon,lat):
    reponse =  sess.get('https://api-adresse.data.gouv.fr/reverse/?lon='+str(lon)+'&lat='+str(lat)) #API du gouvernement (fiable) pour reverse geocoding
    try: 
        reponse = reponse.json() #Transforme la sortie json en dictionnaire
        if 'features' in reponse and len(reponse['features']) != 0 and 'properties' in reponse['features'][0] and 'label' in  reponse['features'][0]['properties']: #Si adresse trouvée
            return reponse['features'][0]['properties']['label'] #Emplacement de l'adresse
        else:
            print(reponse)
            return np.nan  #Retourn nan si pas d'adresse trouvée
    except Exception as err:    #Si erreur affiche ce que renvoie l'api et l'erreur
        print('ERREUR sur :',reponse,'\n'+err)

def Adresse():
    print('Creation adresses')
    print('\n Chargement... \n')
    
    requete = """SELECT IdLocalisation,Longitudegps,Latitudegps FROM coordonnees #Requete pour limiter le nombre d'équipements sinon ça prend des jours
                    INNER JOIN equipement USING(IdLocalisation)
                    INNER JOIN commune USING(CodeCommune)
                    INNER JOIN departement USING(CodeDepartement)
                    WHERE CodeDepartement = 37"""
    requeteNb = requete.replace('IdLocalisation,Longitudegps,Latitudegps','COUNT(*)') #Requete qui renvoie le nombre total de lignes

    dbConnection = sqlEngine.connect() #Connexion sgbd
    dbConnection.execute('DELETE FROM adresse') #Initialise table adresse
    tables = pd.read_sql(requete,dbConnection,chunksize=tailleTableAdresse) #DataFrame de la requete
    NbLignes = pd.read_sql(requeteNb,dbConnection).values[0][0] #Avoir le nombre de lignes

    for table in tqdm(enumerate(tables),desc="Adresses",total=NbLignes):
        table['LibAdresse'] = table.apply(lambda row: reverse_geocodeur(row.Longitudegps , row.Latitudegps),axis=1) #Ajoute les adresses
        table = table.reindex(columns=['LibAdresse','IdLocalisation'])
        table.to_sql('adresse',dbConnection,if_exists='append',index=False) #Ajoute au sgbd
        
    dbConnection.close() #Ferme la connexion au sgbd

#------------------------------------------------------------------------------------------------------

Reinit('CreationTables.sql')
Categorie('BPE20_table_passage.csv')

CommuneDepRegion('region_2022.csv',
                 'departement_2022.csv',
                 'communes-01012019.csv')

Equipement('bpe20_ensemble_xy.csv',
           'bpe20_enseignement_xy.csv',
           'bpe20_sport_loisir_xy.csv')
Adresse()