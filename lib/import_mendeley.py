'''Create empty sqlite data file and copy over contents

'''

import sys
import os
import sqlite3
import shutil
import re
import uuid
import logging
import time
if sys.version_info[0]>=3:
    #---------------------Python3---------------------
    from urllib.parse import unquote
    from urllib.parse import urlparse
else:
    #--------------------Python2.7--------------------
    from urllib import unquote
    from urlparse import urlparse

from lib import sqlitedb

FILE_OUT_NAME='~/Documents/MeiTingTrunk/mendeley.sqlite'
FILE_IN_NAME='mendeley.sqlite'
#STORAGE_FOLDER='~/Documents/MTT/'
#LIB_NAME='mendeley'
RENAME_FILE=True

LOGGER=logging.getLogger(__name__)


READ_DOC_ATTRS=[\
'issn', 'issue', 'language', 'read', 'type', 'confirmed',
'deduplicated', 'favourite', 'note',
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

WRITE_DOC_ATTRS=[\
'issn', 'issue', 'language', 'read', 'type', 'confirmed',
'deduplicated', 'favourite', 'note',
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
'institution', 'lastUpdate', 'legalStatus', 'length', 'medium', 'isbn',
'deletionPending']

INT_COLUMNS=['month', 'year', 'day']




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
    #path = unquote(str(urlparse(url).path)).decode("utf8")
    path = unquote(str(urlparse(url).path))
    path=os.path.abspath(path)

    if os.path.exists(path):
        return path
    else:
        #-------------------For windowes-------------------
        if url[5:8]==u'///':
            url=u'file://'+url[8:]
            path=urlparse(url)
            path=os.path.join(path.netloc,path.path)
            #path=unquote(str(path)).decode('utf8')
            path=unquote(str(path))
            path=os.path.abspath(path)
            return path




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



def importMendeleyPreprocess(jobid, file_in_path, file_out_path):

    try:
        #--------------Connect input database--------------
        dbfin=os.path.abspath(file_in_path)

        try:
            dbin = sqlite3.connect(dbfin)
            LOGGER.info('Connected to database %s' %file_in_path)
        except:
            LOGGER.exception('Failed to connect to database %s' %file_in_path)

        cin=dbin.cursor()

        #-----------------Create empty db-----------------
        file_out_path=os.path.expanduser(file_out_path)
        dbout, storage_folder, lib_name=sqlitedb.createNewDatabase(file_out_path)
        cout=dbout.cursor()

        lib_folder=os.path.join(storage_folder,lib_name)
        #file_folder=os.path.join(lib_folder,'_collections')
        rel_lib_folder=os.path.join('', lib_name) # relative to storage folder
        #rel_file_folder=os.path.join('','_collections')

        LOGGER.debug('storage_folder = %s' %storage_folder)
        LOGGER.debug('lib_name = %s' %lib_name)
        LOGGER.debug('lib_folder = %s' %lib_folder)
        LOGGER.debug('rel_lib_folder = %s' %rel_lib_folder)

        #----------------Copy folders table----------------
        query='''SELECT id, name, parentId
        FROM Folders
        '''

        ret=cin.execute(query).fetchall()

        #------------If Default in folder list------------
        folders=[]
        for fid, fname, pid in ret:
            if fname=='Default' and pid==-1:
                fname='Default_Mendeley'
                LOGGER.info('Renaming "Default" folder to "Default_Mendeley')
            # may not happen to you
            if pid==0:
                pid=-1
            folders.append((fid, fname, pid))

        query='''INSERT OR IGNORE INTO Folders (id, name, parentId, path)
        VALUES (?,?,?,?)'''

        for fii in folders:
            cout.execute(query, (fii[0], fii[1], fii[2],
                os.path.join(rel_lib_folder,fii[1])))

        #----------------Loop through docs----------------
        docids=getDocIds(dbin)

        LOGGER.info('NO. of docs in database = %d' %len(docids))

        return 0, jobid, dbin, dbout, docids, lib_folder, lib_name
    except:
        return 1, jobid, None, None, None, None, None



def importMendeleyCopyData(jobid, dbin, dbout, lib_name, lib_folder,
        rename_file, ii, docii):

    if docii is None:
        # this signals db commit
        dbout.commit()
        dbout.close()
        dbin.close()
        return 0, jobid

    cout=dbout.cursor()
    cin=dbin.cursor()

    #lib_folder=os.path.join(storage_folder,lib_name)
    file_folder=os.path.join(lib_folder,'_collections')
    rel_lib_folder=os.path.join('', lib_name) # relative to storage folder
    rel_file_folder=os.path.join('','_collections')

    try:
        ii+=1

        LOGGER.debug('Copying doc id = %s' %docii)

        #---------------Get Documents columns---------------
        meta_query='''SELECT %s from Documents
        WHERE Documents.id = ?''' %', '.join(READ_DOC_ATTRS)

        ret=cin.execute(meta_query, (docii,))
        metaii=list(ret.fetchall()[0])

        # convert int
        for jj in INT_COLUMNS:
            idxjj=READ_DOC_ATTRS.index(jj)
            fjj=metaii[idxjj]
            if fjj is not None:
                fjj=int(fjj)
                metaii[idxjj]=fjj

        # make sure added exists
        idxjj=READ_DOC_ATTRS.index('added')
        fjj=metaii[idxjj]
        if fjj is None:
            fjj=str(int(time.time()))
        metaii[idxjj]=fjj

        meta_dictii=dict(zip(READ_DOC_ATTRS, metaii))
        meta_dictii['deletionPending']='false'
        metaii.append('false')
        metaii=tuple(metaii)

        #-----------------Get DocumentTags-----------------
        tags=selByDocid(cin, 'DocumentTags', 'tag', docii)

        #------------------Get FileNotes------------------
        #notes=selByDocid(cin, 'DocumentNotes', 'text', docii)
        notes=selByDocid(cin, 'FileNotes', ['note', 'modifiedTime', 'createdTime'], docii)

        #---------------Get DocumentKeywords---------------
        keywords=selByDocid(cin, 'DocumentKeywords', 'keyword', docii)

        #-----------------Get DocumentUrls-----------------
        urls=selByDocid(cin, 'DocumentUrls', 'url', docii)
        urls=[str(bjj) for bjj in urls]   # convert blob to str

        #---------------Get DocumentFolders---------------
        query='''SELECT Folders.id, Folders.name, Folders.parentId
        FROM Folders
        LEFT JOIN DocumentFolders ON DocumentFolders.folderId = Folders.id
        WHERE DocumentFolders.documentId = ?'''

        ret=cin.execute(query, (docii,)).fetchall()

        # if name conflict with Default
        folder_info=[]
        for fid, fname, pid in ret:
            if fname=='Default' and pid==-1:
                fname='Default_Mendeley'
            if pid==0:
                pid=-1
            folder_info.append((fid, fname, pid))

        # if not in any folder, put to Default
        if len(folder_info)==0:
            folder_info.append((0, 'Default', -1))

        #-------------Get DocumentContributors-------------
        authors=selByDocid(cin, 'DocumentContributors',
        ['contribution', 'firstNames', 'Lastname'], docii)

        meta_dictii['lastName_l']=[jj[2] for jj in authors]

        #------------Insert to output database------------
        query='''INSERT INTO Documents (
        %s )
        VALUES (%s)''' %(', '.join(WRITE_DOC_ATTRS), ', '.join(['?']*len(WRITE_DOC_ATTRS)))

        metaii=tuple([meta_dictii[jj] for jj in WRITE_DOC_ATTRS])
        cout.execute(query, metaii)

        for tagii in tags:
            query='''INSERT INTO DocumentTags (did, tag)
            VALUES (?, ?)'''
            cout.execute(query, (ii, tagii))

        for keyii in keywords:
            query='''INSERT INTO DocumentKeywords (did, text)
            VALUES (?, ?)'''
            cout.execute(query, (ii, keyii))

        for nii in notes:
            query='''INSERT INTO DocumentNotes (did, note, modifiedTime, createdTime)
            VALUES (?, ?, ?, ?)'''
            cout.execute(query, (ii,)+ nii)

        for fii in folder_info:
            query='''INSERT INTO DocumentFolders (did, folderid)
            VALUES (?, ?)'''
            cout.execute(query, (ii, fii[0]))

            query='''INSERT OR IGNORE INTO Folders (id, name, parentId, path)
            VALUES (?,?,?,?)'''
            cout.execute(query, (fii[0], fii[1], fii[2],
                os.path.join(rel_lib_folder,fii[1])))

        for aii in authors:
            query='''INSERT INTO DocumentContributors (
            did, contribution, firstNames, lastName)
            VALUES (?, ?, ?, ?)'''
            cout.execute(query, (ii,)+aii)

        for urlii in urls:
            query='''INSERT INTO DocumentUrls (did, url)
            VALUES (?, ?)'''
            cout.execute(query, (ii, urlii))

        # get path
        query='''SELECT Files.localUrl
        FROM Files
        LEFT JOIN DocumentFiles ON DocumentFiles.hash = Files.hash
        WHERE DocumentFiles.documentId = ?'''

        ret=cin.execute(query, (docii,))

        fileurl=ret.fetchall()
        meta_dictii['files_l']=[]
        if len(fileurl)>0:

            for fileii in fileurl:
                urlii=fileii[0]
                filepath=converturl2abspath(urlii)
                meta_dictii['files_l'].append(filepath)

            for filepath in meta_dictii['files_l']:

                # rename file
                if rename_file:
                    filename=sqlitedb.renameFile(filepath,meta_dictii)
                else:
                    filename=os.path.split(filepath)[1]

                filename=re.sub(r'[//\ <>:"|?*]','_',filename)
                filename=re.sub(r'al.','al',filename)
                filename=re.sub(r'_-_','_',filename)
                filename=filename.strip()

                relpath=os.path.join(rel_file_folder,filename)

                query='''INSERT INTO DocumentFiles (did, relpath)
                VALUES (?, ?)'''

                cout.execute(query, (ii, relpath))

                abspath=os.path.join(file_folder, filename)

                LOGGER.debug('relpath = %s' %relpath)
                LOGGER.debug('abspath = %s' %abspath)

                try:
                    shutil.copy2(filepath,abspath)
                    LOGGER.debug('Copied %s to %s' %(filepath, abspath))
                except:
                    LOGGER.exception('Failed to copy %s to %s' %(filepath,
                        abspath))

        return 0, jobid
    except:
        return 1, jobid






def importMendeley(file_in_path, file_out_path, rename_file):

    #--------------Connect input database--------------
    dbfin=os.path.abspath(file_in_path)

    try:
        dbin = sqlite3.connect(dbfin)
        print('Connected to database:')
    except:
        print('Failed to connect to database:')

    cin=dbin.cursor()

    #-----------------Create empty db-----------------
    file_out_path=os.path.expanduser(file_out_path)
    dbout, storage_folder, lib_name=sqlitedb.createNewDatabase(file_out_path)
    cout=dbout.cursor()

    lib_folder=os.path.join(storage_folder,lib_name)
    file_folder=os.path.join(lib_folder,'_collections')
    rel_lib_folder=os.path.join('', lib_name) # relative to storage folder
    rel_file_folder=os.path.join('','_collections')

    #----------------Copy folders table----------------
    query='''SELECT id, name, parentId
    FROM Folders
    '''

    ret=cin.execute(query).fetchall()

    #------------If Default in folder list------------
    folders=[]
    for fid, fname, pid in ret:
        if fname=='Default' and pid==-1:
            fname='Default_Mendeley'
        # may not happen to you
        if pid==0:
            pid=-1
        folders.append((fid, fname, pid))

    query='''INSERT OR IGNORE INTO Folders (id, name, parentId, path)
    VALUES (?,?,?,?)'''

    for fii in folders:
        cout.execute(query, (fii[0], fii[1], fii[2],
            os.path.join(rel_lib_folder,fii[1])))

    #----------------Loop through docs----------------
    docids=getDocIds(dbin)

    for ii,docii in enumerate(docids):

        ii+=1
        print('# <imporMendeley>: Copying doc ', ii)

        #---------------Get Documents columns---------------
        meta_query='''SELECT %s from Documents
        WHERE Documents.id = ?''' %', '.join(READ_DOC_ATTRS)

        ret=cin.execute(meta_query, (docii,))
        metaii=list(ret.fetchall()[0])

        # convert int
        for jj in INT_COLUMNS:
            idxjj=READ_DOC_ATTRS.index(jj)
            fjj=metaii[idxjj]
            if fjj is not None:
                fjj=int(fjj)
                metaii[idxjj]=fjj

        # make sure added exists
        idxjj=READ_DOC_ATTRS.index('added')
        fjj=metaii[idxjj]
        if fjj is None:
            fjj=str(int(time.time()))
        metaii[idxjj]=fjj

        meta_dictii=dict(zip(READ_DOC_ATTRS, metaii))
        meta_dictii['deletionPending']='false'
        metaii.append('false')
        metaii=tuple(metaii)

        #-----------------Get DocumentTags-----------------
        tags=selByDocid(cin, 'DocumentTags', 'tag', docii)

        #------------------Get FileNotes------------------
        #notes=selByDocid(cin, 'DocumentNotes', 'text', docii)
        notes=selByDocid(cin, 'FileNotes', ['note', 'modifiedTime', 'createdTime'], docii)

        #---------------Get DocumentKeywords---------------
        keywords=selByDocid(cin, 'DocumentKeywords', 'keyword', docii)

        #-----------------Get DocumentUrls-----------------
        urls=selByDocid(cin, 'DocumentUrls', 'url', docii)
        urls=[str(bjj) for bjj in urls]   # convert blob to str

        #---------------Get DocumentFolders---------------
        query='''SELECT Folders.id, Folders.name, Folders.parentId
        FROM Folders
        LEFT JOIN DocumentFolders ON DocumentFolders.folderId = Folders.id
        WHERE DocumentFolders.documentId = ?'''

        ret=cin.execute(query, (docii,)).fetchall()

        # if name conflict with Default
        folder_info=[]
        for fid, fname, pid in ret:
            if fname=='Default' and pid==-1:
                fname='Default_Mendeley'
            if pid==0:
                pid=-1
            folder_info.append((fid, fname, pid))

        # if not in any folder, put to Default
        if len(folder_info)==0:
            folder_info.append((0, 'Default', -1))

        #-------------Get DocumentContributors-------------
        authors=selByDocid(cin, 'DocumentContributors',
        ['contribution', 'firstNames', 'Lastname'], docii)

        meta_dictii['lastName_l']=[jj[2] for jj in authors]

        #------------Insert to output database------------
        query='''INSERT INTO Documents (
        %s )
        VALUES (%s)''' %(', '.join(WRITE_DOC_ATTRS), ', '.join(['?']*len(WRITE_DOC_ATTRS)))

        metaii=tuple([meta_dictii[jj] for jj in WRITE_DOC_ATTRS])
        cout.execute(query, metaii)

        for tagii in tags:
            query='''INSERT INTO DocumentTags (did, tag)
            VALUES (?, ?)'''
            cout.execute(query, (ii, tagii))

        for keyii in keywords:
            query='''INSERT INTO DocumentKeywords (did, text)
            VALUES (?, ?)'''
            cout.execute(query, (ii, keyii))

        for nii in notes:
            query='''INSERT INTO DocumentNotes (did, note, modifiedTime, createdTime)
            VALUES (?, ?, ?, ?)'''
            cout.execute(query, (ii,)+ nii)

        for fii in folder_info:
            query='''INSERT INTO DocumentFolders (did, folderid)
            VALUES (?, ?)'''
            cout.execute(query, (ii, fii[0]))

            query='''INSERT OR IGNORE INTO Folders (id, name, parentId, path)
            VALUES (?,?,?,?)'''
            cout.execute(query, (fii[0], fii[1], fii[2],
                os.path.join(rel_lib_folder,fii[1])))

        for aii in authors:
            query='''INSERT INTO DocumentContributors (
            did, contribution, firstNames, lastName)
            VALUES (?, ?, ?, ?)'''
            cout.execute(query, (ii,)+aii)

        for urlii in urls:
            query='''INSERT INTO DocumentUrls (did, url)
            VALUES (?, ?)'''
            cout.execute(query, (ii, urlii))

        # get path
        query='''SELECT Files.localUrl
        FROM Files
        LEFT JOIN DocumentFiles ON DocumentFiles.hash = Files.hash
        WHERE DocumentFiles.documentId = ?'''

        ret=cin.execute(query, (docii,))

        fileurl=ret.fetchall()
        meta_dictii['files_l']=[]
        if len(fileurl)>0:

            for fileii in fileurl:
                urlii=fileii[0]
                filepath=converturl2abspath(urlii)
                meta_dictii['files_l'].append(filepath)

            for filepath in meta_dictii['files_l']:

                # rename file
                if rename_file:
                    filename=sqlitedb.renameFile(filepath,meta_dictii)
                else:
                    filename=os.path.split(filepath)[1]

                filename=re.sub(r'[//\ <>:"|?*]','_',filename)
                filename=re.sub(r'al.','al',filename)
                filename=re.sub(r'_-_','_',filename)
                filename=filename.strip()

                relpath=os.path.join(rel_file_folder,filename)

                query='''INSERT INTO DocumentFiles (did, relpath)
                VALUES (?, ?)'''

                cout.execute(query, (ii, relpath))

                abspath=os.path.join(file_folder, filename)
                shutil.copy2(filepath,abspath)

    dbout.commit()

    return 0


if __name__=='__main__':

    importMendeley(FILE_IN_NAME, FILE_OUT_NAME, True)
