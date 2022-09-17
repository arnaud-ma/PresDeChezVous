#Ce script permet de récupérer les valeurs de .Database_connection sous forme de dictionnaire
import os

def AbsolutePath(FileName):
    absolutepath = os.path.abspath(__file__)
    while 'PresDeChezVous' in absolutepath: #Remonte jusqu'au dossier du projet
        absolutepath = os.path.dirname(absolutepath)
    print(absolutepath)
    for root, dirs, files in os.walk(absolutepath): #Tous les fichiers du projet sont parcourues
        for name in files:
            if name == FileName:
                return (os.path.abspath(os.path.join(root, name)))


with open(AbsolutePath('Settings.txt'),encoding='utf8') as fichSett:
    Sett = dict()
    for line in fichSett:
        if ':' in line:
            line = line.replace('\n','').replace(' ','')
            sett = line.split(':')
            Sett[sett[0]] = sett[1]

print(Sett) #Print pour que le php le lise

def ConnectionRootMysql():
    HOST = Sett['HOST']
    PORT = Sett['PORT']
    PASSWORD = Sett['PASSWORD_ROOT']
    USER = Sett['ROOT']
    DATABASE = Sett['DATABASE']

    if PASSWORD != '':
        PASSWORD = ':'+PASSWORD
    if PORT != '':
        PORT = ':'+PORT
    return 'mysql+pymysql://'+USER+PASSWORD+'@'+HOST+PORT + '/'+DATABASE+'?charset=utf8mb4'

def GetDatabase():
    return Sett['DATABASE']