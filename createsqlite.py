'''Create empty sqlite data file and copy over contents

'''


import sys
import os
import sqlite3
import shutil
import re
import uuid
if sys.version_info[0]>=3:
    #---------------------Python3---------------------
    from urllib.parse import unquote
    from urllib.parse import urlparse
else:
    #--------------------Python2.7--------------------
    from urllib import unquote
    from urlparse import urlparse

FILE_OUT_NAME='new3.sqlite'
FILE_IN_NAME='mendeley.sqlite'
LIB_FOLDER='~/Papers2'
FILE_FOLDER=os.path.join(LIB_FOLDER,'collections')


DOC_ATTRS=[\
'issn', 'issue', 'language', 'read', 'type', 'confirmed',
'deduplicated', 'deletionPending', 'favourite', 'note',
'abstract', 'advisor', 'added',
'arxivId', 'title', 'pmid',
'publication', 'publicLawNumber', 'month',
'pages', 'sections', 'seriesEditor', 'series', 'seriesNumber',
'publisher', 'reprintEdition', 'reviewedArticle', 'revisionNumber',
'userType', 'volume', 'year', 'session', 'shortTitle', 'sourceType',
'code', 'codeNumber', 'codeSection', 'codeVolume', 'chapter',
'citationKey', 'city', 'day', 'department', 'doi', 'edition',
'committee', 'counsel', 'country', 'dateAccessed',
'internationalAuthor', 'internationalNumber', 'internationalTitle',
'internationalUserType', 'genre',
'institution', 'lastUpdate', 'legalStatus', 'length', 'medium', 'isbn']

INT_COLUMNS=['read', 'confirmed', 'deduplicated', 'deletionPending',
        'favourite', 'month', 'year', 'day']




#----------Get a list of docids from a folder--------------
def getDocIds(db,verbose=True):
    '''Get a list of docids from a folder

    Update time: 2018-07-28 20:11:09.
    '''

    query=\
    '''SELECT Documents.id
       FROM Documents
    '''

    ret=db.execute(query)
    data=ret.fetchall()
    docids=[ii[0] for ii in data]
    docids.sort()
    return docids

def converturl2abspath(url):
    '''Convert a url string to an absolute path
    This is necessary for filenames with unicode strings.
    '''

    #--------------------For linux--------------------
    path = unquote(str(urlparse(url).path)).decode("utf8") 
    path=os.path.abspath(path)

    if os.path.exists(path):
        return path
    else:
        #-------------------For windowes-------------------
        if url[5:8]==u'///':   
            url=u'file://'+url[8:]
            path=urlparse(url)
            path=os.path.join(path.netloc,path.path)
            path=unquote(str(path)).decode('utf8')
            path=os.path.abspath(path)
            return path


if __name__=='__main__':

    dbfin=os.path.abspath(FILE_IN_NAME)

    try:
        dbin = sqlite3.connect(dbfin)
        print('Connected to database:')
    except:
        print('Failed to connect to database:')

    dbfout=os.path.abspath(FILE_OUT_NAME)

    try:
        dbout = sqlite3.connect(dbfout)
        print('Connected to database:')
    except:
        print('Failed to connect to database:')

    cin=dbin.cursor()
    cout=dbout.cursor()

    #--------------Create documents table--------------
    query='''CREATE TABLE IF NOT EXISTS Documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL UNIQUE,
    %s)'''
    columns=[]
    for kii in DOC_ATTRS:
        if kii in INT_COLUMNS:
            columns.append('%s INT' %kii)
        else:
            columns.append('%s TEXT' %kii)

    columns=', '.join(columns)
    query=query %columns

    print 'Creating empty table...'
    cout.execute(query)
    dbout.commit()

    #------------Create DocumentTags table------------
    query='''CREATE TABLE IF NOT EXISTS DocumentTags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    docid INT,
    tag TEXT)'''

    cout.execute(query)
    dbout.commit()

    #------------Create DocumentNotes table------------
    query='''CREATE TABLE IF NOT EXISTS DocumentNotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    docid INT,
    note TEXT,
    modifiedTime TEXT,
    createdTime TEXT
    )'''

    cout.execute(query)
    dbout.commit()
    
    #----------Create DocumentKeywords table----------
    query='''CREATE TABLE IF NOT EXISTS DocumentKeywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    docid INT,
    text TEXT)'''

    cout.execute(query)
    dbout.commit()

    #-----------Create DocumentFolders table-----------
    query='''CREATE TABLE IF NOT EXISTS DocumentFolders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    docid INT,
    folderid INT
    )'''

    cout.execute(query)
    dbout.commit()

    #---------------Create Folders table---------------
    query='''CREATE TABLE IF NOT EXISTS Folders (
    id INTEGER,
    name TEXT,
    parentId INT,
    path TEXT,
    UNIQUE (name, parentId)
    )'''

    cout.execute(query)
    dbout.commit()
    

    #--------Create DocumentContributors table--------
    query='''CREATE TABLE IF NOT EXISTS DocumentContributors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    docid INT,
    contribution TEXT,
    firstNames TEXT,
    lastName TEXT
    )'''

    cout.execute(query)
    dbout.commit()

    #------------Create DocumentFiles table------------
    query='''CREATE TABLE IF NOT EXISTS DocumentFiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    docid INT,
    abspath TEXT
    )'''

    cout.execute(query)
    dbout.commit()

    #------------Create DocumentUrls table------------
    query='''CREATE TABLE IF NOT EXISTS DocumentUrls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    docid INT,
    url TEXT
    )'''

    cout.execute(query)
    dbout.commit()

    #----------------Copy over content----------------
    docids=getDocIds(dbin)

    #---------------Create output folder---------------
    FILE_FOLDER=os.path.expanduser(FILE_FOLDER)
    if not os.path.exists(FILE_FOLDER):
        os.makedirs(FILE_FOLDER)
        print("Create folder %s" %FILE_FOLDER)

    #----------------Copy folders table----------------
    query='''SELECT id, name, parentId
    FROM Folders
    '''

    ret=cin.execute(query).fetchall()

    query='''INSERT OR IGNORE INTO Folders (id, name, parentId, path)
    VALUES (?,?,?,?)'''

    for fii in ret:
        cout.execute(query, (fii[0], fii[1], fii[2], os.path.join(LIB_FOLDER,fii[1])))

    #----------------Loop through docs----------------
    def selByDocid(cursor, table, column, docid):
        if isinstance(column, str):
            cols=column
            single=True
        elif isinstance(column, (tuple, list)):
            cols=', '.join(column)
            single=False

        query='''SELECT %s from %s
        WHERE %s.documentId = ?''' %(cols, table, table)
        ret=cursor.execute(query, (docid,)).fetchall()

        if single:
            return [ii[0] for ii in ret]
        else:
            return [ii for ii in ret]


    for ii,docii in enumerate(docids):

        ii+=1
        print '\n# <createsqlite>: Copying doc ', ii
        
        meta_query='''SELECT %s from Documents
        WHERE Documents.id = ?''' %', '.join(DOC_ATTRS)

        ret=cin.execute(meta_query, (docii,))
        metaii=ret.fetchall()[0]

        tags=selByDocid(cin, 'DocumentTags', 'tag', docii)
        #notes=selByDocid(cin, 'DocumentNotes', 'text', docii)
        notes=selByDocid(cin, 'FileNotes', ['note', 'modifiedTime', 'createdTime'], docii)
        keywords=selByDocid(cin, 'DocumentKeywords', 'keyword', docii)
        folderid=selByDocid(cin, 'DocumentFolders', 'folderId', docii)
        urls=selByDocid(cin, 'DocumentUrls', 'url', docii)
        urls=[str(bjj) for bjj in urls]   # convert blob to str

        # get folder
        query='''SELECT Folders.id, Folders.name, Folders.parentId
        FROM Folders
        LEFT JOIN DocumentFolders ON DocumentFolders.folderId = Folders.id
        WHERE DocumentFolders.documentId = ?'''

        ret=cin.execute(query, (docii,))
        folder_info=ret.fetchall()

        # get authors
        authors=selByDocid(cin, 'DocumentContributors',
        ['contribution', 'firstNames', 'Lastname'], docii)

        # insert to table
        uuidstr=str(uuid.uuid4())
        query='''INSERT INTO Documents (
        uuid, %s )
        VALUES (%s)''' %(', '.join(DOC_ATTRS), ', '.join(['?']*(len(DOC_ATTRS)+1)))

        cout.execute(query, (uuidstr,)+metaii)

        for tagii in tags:
            query='''INSERT INTO DocumentTags (docid, tag)
            VALUES (?, ?)'''
            cout.execute(query, (ii, tagii))

        for keyii in keywords:
            query='''INSERT INTO DocumentKeywords (docid, text)
            VALUES (?, ?)'''
            cout.execute(query, (ii, keyii))

        for nii in notes:
            query='''INSERT INTO DocumentNotes (docid, note, modifiedTime, createdTime)
            VALUES (?, ?, ?, ?)'''
            cout.execute(query, (ii,)+ nii)

        for fii in folder_info:
            query='''INSERT INTO DocumentFolders (docid, folderid)
            VALUES (?, ?)'''
            cout.execute(query, (ii, fii[0]))
            #cout.execute(query, (ii, fii[1], fii[2],
                #os.path.join(LIB_FOLDER,fii[1])))

            query='''INSERT OR IGNORE INTO Folders (id, name, parentId, path)
            VALUES (?,?,?,?)'''
            cout.execute(query, (fii[0], fii[1], fii[2], os.path.join(LIB_FOLDER,fii[1])))

        for aii in authors:
            query='''INSERT INTO DocumentContributors (
            docid, contribution, firstNames, lastName)
            VALUES (?, ?, ?, ?)'''
            cout.execute(query, (ii,)+aii)

        for urlii in urls:
            query='''INSERT INTO DocumentUrls (docid, url)
            VALUES (?, ?)'''
            cout.execute(query, (ii, urlii))

        # get path
        query='''SELECT Files.localUrl
        FROM Files
        LEFT JOIN DocumentFiles ON DocumentFiles.hash = Files.hash
        WHERE DocumentFiles.documentId = ?'''

        ret=cin.execute(query, (docii,))

        fileurl=ret.fetchall()
        if len(fileurl)>0:

            for fileii in fileurl:
                urlii=fileii[0]

                filepath=converturl2abspath(urlii)

                # copy to collection
                filename=os.path.split(filepath)[1]
                newpath=os.path.join(FILE_FOLDER,filename)
                newpath=re.sub(r'[\ <>:"|?*]','_',newpath)
                newpath=re.sub(r'al.','al',newpath)
                newpath=re.sub(r'_-_','_',newpath)
                newpath=newpath.strip()

                shutil.copy2(filepath,newpath)

                query='''INSERT INTO DocumentFiles (docid, abspath)
                VALUES (?, ?)'''

                cout.execute(query, (ii, newpath))


        dbout.commit()








        







