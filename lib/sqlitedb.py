'''Sqlite database read and write functions.

Author: guangzhi XU (xugzhi1987@gmail.com; guangzhi.xu@outlook.com)
Update time: 2018-09-27 19:44:32.
'''

import os
import shutil
import time
import re
from datetime import datetime
import sqlite3
import logging
from collections import MutableMapping
try:
    from . import bibparse
except:
    import bibparse
try:
    from .tools import autoRename
except:
    from tools import autoRename

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

LOGGER=logging.getLogger('default_logger')


class DocMeta(MutableMapping):

    def __init__(self, *args, **kwargs):
        # set defaults
        self.store = {
                'id': None, 'title': None, 'issue': None, 'pages': None,
                'publication': None, 'volume': None, 'year': None,
                'doi': None, 'abstract': None, 'arxivId': None, 'chapter': None,
                'city': None, 'country': None, 'edition': None,
                'institution': None, 'isbn': None, 'issn': None, 'month': None,
                'day': None, 'publisher': None, 'series': None,
                'type': 'article',
                'read': 'false', 'favourite': 'false',
                'pmid': None, 'added': str(int(time.time())),
                'confirmed': 'false',
                'firstNames_l': [],
                'lastName_l': [],
                'keywords_l': [],
                'files_l': [],
                'folders_l': [],
                'tags_l': [],
                'urls_l': [],
                'deletionPending': 'false',
                'notes': None
                }

        self.update(dict(*args, **kwargs))  # use the free update to set keys

    def __getitem__(self, key):
        if key == 'has_file':
            return True if len(self.store['files_l']) > 0 else False
        elif key == 'authors_l':
            return zipAuthors(self.store['firstNames_l'],
                    self.store['lastName_l'])
        elif key == 'citationkey':
            ck = self.store.get('citationkey',None)
            if ck:
                return ck
            else:
                last = self.store.get('lastName_l',[])
                year = self.store.get('year',None)
                if len(last) > 0 and year:
                    ck='%s%s' %(last[0],str(year))
                    return ck
                else:
                    return ''
        else:
            return self.store[key]

    def __setitem__(self, key, value):
        if not isinstance(key,str):
            raise Exception("accept only str type keys. key: %s, value: %s"\
                    %(key, value))
        if key.endswith('_l'):
            if not isinstance(value,(tuple,list)):
                raise Exception("keys end with '_l' accepts only list or tuple. key: %s, value: %s" %(key, value))
        if key not in self.store.keys():
            return

        self.store[key] = value

    def __delitem__(self, key):
        del self.store[key]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __repr__(self):
        return self.store.__repr__()



def readSqlite(dbin):

    #-------------------Get folders-------------------
    folder_dict=getFolders(dbin)

    #-------------------Get metadata-------------------
    cursor=dbin.execute('SELECT * FROM Documents')
    names=list(map(lambda x:x[0], cursor.description))

    meta={}

    query='''SELECT DISTINCT %s
    FROM Documents
    ''' %('id' if 'id' in names else 'rowid')

    docids=dbin.execute(query).fetchall()
    docids=[ii[0] for ii in docids]
    docids.sort()

    folder_data={}
    folder_data['-2']=[] # needs review folder
    folder_data['-3']=[] # trash can

    for idii in docids:
        metaii=getMetaData(dbin,idii)
        meta[idii]=metaii

        folderii=metaii['folders_l']

        if metaii['confirmed'] is None or metaii['confirmed']=='false':
            folder_data['-2'].append(idii)
        if metaii['deletionPending']=='true':
            folder_data['-3'].append(idii)

        # note: convert folder id to str, why?
        # TODO: convert back to int when writing to sqlite
        folderids=[str(ff[0]) for ff in folderii]
        for fii in folderids:
            if fii in folder_data:
                folder_data[fii].append(idii)
            else:
                folder_data[fii]=[idii]

    #----------------Add empty folders----------------
    empty_folderids=list(set(folder_dict.keys()).difference(folder_data.keys()))
    for fii in empty_folderids:
        folder_data[fii]=[]

    return meta, folder_data, folder_dict


def fetchField(db,query,values,ncol=1,ret_type='str'):
    if ret_type not in ['str','list']:
        raise Exception("<ret_type> is one of ['str','list'].")

    aa=db.execute(query,values).fetchall()

    if len(aa)==0:
        if ret_type=='str':
            return None
        else:
            return []

    if ncol==1:
        aa=[ii[0] for ii in aa]
    if ret_type=='str':
        if len(aa)==1:
            return str(aa[0])
        else:
            return '; '.join(aa)
    else:
        return aa


def getMetaData(db, did):
    '''Get meta-data of a doc by docid.
    '''

    cursor=db.execute('SELECT * FROM Documents')
    names=list(map(lambda x:x[0], cursor.description))

    # fetch column from Document table
    if 'id' in names:
        query_base=\
        '''SELECT Documents.%s
           FROM Documents
           WHERE (Documents.id=?)
        '''
    else:
        query_base=\
        '''SELECT Documents.%s
           FROM Documents
           WHERE (Documents.rowid=?)
        '''

    query_tags=\
    '''
    SELECT DocumentTags.tag
    FROM DocumentTags
    WHERE (DocumentTags.did=?)
    '''

    query_urls=\
    '''
    SELECT DocumentUrls.url
    FROM DocumentUrls
    WHERE (DocumentUrls.did=?)
    '''

    query_firstnames=\
    '''
    SELECT DocumentContributors.firstNames
    FROM DocumentContributors
    WHERE (DocumentContributors.did=?)
    '''

    query_lastnames=\
    '''
    SELECT DocumentContributors.lastName
    FROM DocumentContributors
    WHERE (DocumentContributors.did=?)
    '''

    query_keywords=\
    '''
    SELECT DocumentKeywords.text
    FROM DocumentKeywords
    WHERE (DocumentKeywords.did=?)
    '''

    query_folder=\
    '''
    SELECT Folders.id, Folders.name
    FROM Folders
    LEFT JOIN DocumentFolders ON DocumentFolders.folderid=Folders.id
    WHERE (DocumentFolders.did=?)
    '''

    query_files=\
    '''
    SELECT DocumentFiles.abspath
    FROM DocumentFiles
    WHERE (DocumentFiles.did=?)
    '''

    query_notes=\
    '''
    SELECT DocumentNotes.note
    FROM DocumentNotes
    WHERE (DocumentNotes.did=?)
    '''

    #------------------Get file meta data------------------
    #NOTE: rowid here is required by sqlite fts5 virtual table
    fields=['citationkey','title','issue','pages',\
            'publication','volume','year','doi','abstract',\
            'arxivId','chapter','city','country','edition','institution',\
            'isbn','issn','month','day','publisher','series','type',\
            'read','favourite','pmid','added','confirmed', 'deletionPending']

    #result={}
    result=DocMeta()

    if 'id' in names:
        vii=fetchField(db,query_base %'id', (did,))
        result['id']=vii
    else:
        vii=fetchField(db,query_base %'rowid', (did,))
        result['rowid']=vii

    # query single-worded fields, e.g. year, city
    for kii in fields:
        vii=fetchField(db,query_base %(kii), (did,))
        #if kii=='rowid':
            # fts5 in sqlite no longer has docid alias
            #result['id']=vii
        #else:
        result[kii]=vii

    # query notes
    result['notes']=fetchField(db,query_notes,(did,),1,'str')

    # query list fields, .e.g firstnames, tags
    result['firstNames_l']=fetchField(db,query_firstnames,(did,),1,'list')
    result['lastName_l']=fetchField(db,query_lastnames,(did,),1,'list')
    result['keywords_l']=fetchField(db,query_keywords,(did,),1,'list')
    result['files_l']=fetchField(db,query_files,(did,),1,'list')
    result['folders_l']=fetchField(db,query_folder,(did,),2,'list')
    result['tags_l']=fetchField(db,query_tags,(did,),1,'list')
    result['urls_l']=fetchField(db,query_urls,(did,),1,'list')

    folders=result['folders_l']
    # if no folder name, add to Default
    result['folders_l']=folders or [(0, 'Default')]

    return result


def zipAuthors(firstnames,lastnames):
    if len(firstnames)!=len(lastnames):
        print('zipAuthors')
        print('firstnames',firstnames)
        print('lastnames',lastnames)
        raise Exception("Exception")
    authors=[]
    for ii in range(len(firstnames)):
        fii=firstnames[ii]
        lii=lastnames[ii]
        if fii!='' and lii!='':
            authors.append('%s, %s' %(lii,fii))
        elif fii=='' and lii!='':
            authors.append(lii)
        elif fii!='' and lii=='':
            authors.append(fii)

    return authors



def getTrashedFolders(folder_dict):
    results=[kk for kk,vv in folder_dict.items() if vv[1]=='-3']
    print('# <getTrashedFolders>: results=',results)


    def _getChildFolder(folder_dict,folderid,results=None):
        if results is None:
            results=[]
        for idii in folder_dict:
            fii,pii=folder_dict[idii]
            if pii==folderid:
                results.append(idii)
                results=_getChildFolder(folder_dict,fii,results)
        return results
    for fii in results:
        subids=_getChildFolder(folder_dict,fii)
        results.extend(subids)

    return results


def walkFolderTree(folder_dict,folder_data,folderid,docids=None,folderids=None):

    if docids is None:
        docids=[]
    if folderids is None:
        folderids=[]

    docids.extend(folder_data[folderid])
    folderids.append(folderid)

    subfolderids=getChildFolders(folder_dict,folderid)
    print('# <walkFolderTree>: subfolderids',subfolderids)
    for sii in subfolderids:
        folderids,docids=walkFolderTree(folder_dict,folder_data,sii,
                docids,folderids)

    folderids=list(set(folderids))
    docids=list(set(docids))

    return folderids,docids


def findOrphanDocs(folder_data,docids,trashed_folder_ids):
    idsinfolders=[]

    for kk,vv in folder_data.items():
        if kk not in ['-1','-2','-3']+trashed_folder_ids:
            idsinfolders.extend(vv)

    result=[idii for idii in docids if idii not in idsinfolders]

    print('# <findOrphanDocs>: excluded folders= ["-1","-2","-3"]+%s' %trashed_folder_ids)
    LOGGER.info('excluded folders= ["-1","-2","-3"]+%s' %trashed_folder_ids)

    print('# <findOrphanDocs>: Orphan docs=%s' %result)
    LOGGER.info('Orphan docs=%s' %result)

    return result


def findOrphanDocs2(db):

    cin=db.cursor()
    query='''SELECT rowid FROM Documents
    WHERE Documents.deletionPending='true'
    '''

    ret=cin.execute(query)
    ret=[ii[0] for ii in ret]
    print('# <findOrphanDocs2>: orphans=',ret)
    return ret



def getFolders(db):

    #-----------------Get all folders-----------------
    query='''SELECT id, name, parentId
    FROM Folders
    '''
    ret=db.execute(query)
    data=ret.fetchall()

    # dict, key: folderid, value: (folder_name, parent_id)
    # note: convert id to str
    df=dict([(str(ii[0]), (ii[1], str(ii[2]))) for ii in data])

    # add Default
    #df['0']=('Default', '-1')

    return df

def fetchMetaData(meta_dict,key,docids,unique,sort):
    if not isinstance(docids, (tuple,list)):
        docids=[docids,]

    result=[]
    for idii in docids:
        vv=meta_dict[idii].get(key,None)
        # NOTE: don't use if vv:
        # as there are '' entries that will also trigger the if
        if vv is not None:
            if isinstance(vv, (tuple,list)):
                result.extend(vv)
            else:
                result.append(vv)

    if unique:
        result=list(set(result))
    if sort:
        result.sort()

    return result



def filterDocs(meta_dict,folder_data,filter_type,filter_text,current_folder):

    results=[]
    if current_folder=='-1':
        docids=meta_dict.keys()
    else:
        docids=folder_data[current_folder]

    if filter_type=='Filter by authors':
        t_last,t_first=map(str.strip,filter_text.split(','))
        #print('t_last: %s, t_first: %s, text: %s' %(t_last,t_first,filter_text))
        for kk in docids:
            authors=meta_dict[kk]['authors_l']
            if filter_text in authors:
                results.append(kk)

    elif filter_type=='Filter by tags':
        for kk in docids:
            tags=meta_dict[kk]['tags_l'] or []
            if filter_text in tags:
                results.append(kk)

    elif filter_type=='Filter by publications':
        for kk in docids:
            pubs=meta_dict[kk]['publication'] or []
            if filter_text in pubs:
                results.append(kk)

    elif filter_type=='Filter by keywords':
        for kk in docids:
            keywords=meta_dict[kk]['keywords_l'] or []
            if filter_text in keywords:
                results.append(kk)

    #print(results)

    return results





#--------------Get folder id and name list in database----------------
def getFolderList(db,folder,verbose=True):
    '''Get folder id and name list in database

    <folder>: select folder from database.
              If None, select all folders/subfolders.
              If str, select folder <folder>, and all subfolders. If folder
              name conflicts, select the one with higher level.
              If a tuple of (id, folder), select folder with name <folder>
              and folder id <id>, to avoid name conflicts.

    Return: <folders>: list, with elements of (id, folder_tree).
            where <folder_tree> is a str of folder name with tree structure, e.g.
            test/testsub/testsub2.

    Update time: 2016-06-16 19:38:15.
    '''

    # get all folders with id, name, parentid
    query=\
    '''SELECT Folders.id,
              Folders.name,
              Folders.parentID
       FROM Folders
    '''
    # get folder by name
    query1=\
    '''SELECT Folders.id,
              Folders.name,
              Folders.parentID
       FROM Folders
       WHERE (Folders.name="%s")
    '''%folder

    #-----------------Get all folders-----------------
    ret=db.execute(query)
    data=ret.fetchall()

    # dict, key: folderid, value: (folder_name, parent_id)
    df=dict([(ii[0],ii[1:]) for ii in data])

    allfolderids=[ii[0] for ii in data]

    #---------------Select target folder---------------
    if folder is None:
        folderids=allfolderids
    if type(folder) is str:
        folderids=db.execute(query1).fetchall()
        folderids=[ii[0] for ii in folderids]
    elif isinstance(folder, (tuple,list)):
        # get folder from gui
        #seldf=df[(df.folderid==folder[0]) & (df.folder==folder[1])]
        #folderids=fetchField(seldf,'folderid')
        folderids=[folder[0]]

    #----------------Get all subfolders----------------
    if folder is not None:
        folderids2=[]
        for ff in folderids:
            folderids2.append(ff)
            subfs=getSubFolders(df,ff)
            folderids2.extend(subfs)
    else:
        folderids2=folderids

    #---------------Remove empty folders---------------
    folderids2=[ff for ff in folderids2 if not isFolderEmpty(db,ff)]

    #---Get names and tree structure of all non-empty folders---
    folders=[]
    for ff in folderids2:
        folders.append(getFolderTree(df,ff))

    #----------------------Return----------------------
    if folder is None:
        return folders
    else:
        if len(folders)==0:
            print("Given folder name not found in database or folder is empty.")
            return []
        else:
            return folders


#--------------------Check a folder is empty or not--------------------
def isFolderEmpty(db,folderid,verbose=True):
    '''Check a folder is empty or not
    '''

    query=\
    '''SELECT Documents.title,
              DocumentFolders.folderid,
              Folders.name
       FROM Documents
       LEFT JOIN DocumentFolders
           ON Documents.id=DocumentFolders.documentId
       LEFT JOIN Folders
           ON Folders.id=DocumentFolders.folderid
    '''

    fstr='(Folders.id="%s")' %folderid
    fstr='WHERE '+fstr
    query=query+' '+fstr

    ret=db.execute(query)
    data=ret.fetchall()
    if len(data)==0:
        return True
    else:
        return False

#-------------------Get subfolders of a given folder-------------------
def getChildFolders(df,folderid,verbose=True):
    '''Get subfolders of a given folder

    <df>: dict, key: folderid, value: (folder_name, parent_id).
    <folderid>: int, folder id
    '''
    results=[]
    for idii in df:
        fii,pii=df[idii]
        if pii==folderid:
            results.append(idii)
    results.sort()
    return results

#-------------------Get subfolders of a given folder-------------------
def getSubFolders(df,folderid,verbose=True):
    '''Get subfolders of a given folder

    <df>: dict, key: folderid, value: (folder_name, parent_id).
    <folderid>: int, folder id
    '''

    getParentId=lambda df,id: df[id][1]
    results=[]

    for idii in df:
        fii,pii=df[idii]
        cid=idii
        while True:
            pid=getParentId(df,cid)
            if pid==-1 or pid==0:
                break
            if pid==folderid:
                results.append(idii)
                break
            else:
                cid=pid

    results.sort()
    return results

#-------------Get folder tree structure of a given folder-------------
def getFolderTree(df,folderid,verbose=True):
    '''Get folder tree structure of a given folder

    <df>: dict, key: folderid, value: (folder_name, parent_id).
    <folderid>: int, folder id
    '''

    getFolderName=lambda df,id: df[id][0]
    getParentId=lambda df,id: df[id][1]

    folder=getFolderName(df,folderid)

    #------------Back track tree structure------------
    cid=folderid
    while True:
        pid=str(getParentId(df,cid))
        if pid=='-1':
            break
        else:
            pfolder=getFolderName(df,pid)
            #folder=u'%s/%s' %(pfolder,folder)
            folder=os.path.join(pfolder,folder)
        cid=pid

    return folderid,folder


#----------Get a list of docids from a folder--------------
def getFolderDocList(db,folderid,verbose=True):
    '''Get a list of docids from a folder

    Update time: 2018-07-28 20:11:09.
    '''

    query=\
    '''SELECT Documents.id
       FROM Documents
       LEFT JOIN DocumentFolders
           ON Documents.id=DocumentFolders.documentId
       WHERE (DocumentFolders.folderid=%s)
    ''' %folderid

    ret=db.execute(query)
    data=ret.fetchall()
    docids=[ii[0] for ii in data]
    docids.sort()
    return docids


def renameFile(fname,meta_dict,replace_space=False):
    '''Rename file on export.

    Temp func, need to enable formatting later
    '''
    dirjj,filenamejj=os.path.split(fname)
    basename,ext=os.path.splitext(filenamejj)

    author=meta_dict['lastName_l']
    if len(author)>0:
        author=author[0]
        if author is None or author=='':
            author='Unknown'
    else:
        author='Unknown'

    year=meta_dict['year']
    print('year=',year)
    if year is None:
        year='unknown'
    title=meta_dict.get('title',basename)

    #---------Handle multiple files for a doc---------
    if len(meta_dict['files_l'])==1:
        fname2='%s_%s_%s%s' %(author,year,title,ext)
    else:
        fname2='%s_%s_%s_%d%s' %(author,year,title,\
                meta_dict['files_l'].index(fname), ext)

    if replace_space:
        fname2=fname2.replace(' ','-')

    fname2=re.sub(r'[<>:"|?*]','_',fname2)
    print('# <renameFile>: Old file name=',fname,'New file name=',fname2)

    return fname2


def saveFoldersToDatabase(db,folder_ids,folder_dict,lib_folder):

    cout=db.cursor()

    #for idii,vv in folder_dict.items():
    folder_ids=list(set(folder_ids))
    for idii in folder_ids:
        nameii,pidii=folder_dict[idii]
        idii=int(idii)
        pathii=os.path.join(lib_folder,nameii)
        pathii=os.path.abspath(pathii)

        print('# <saveFoldersToDatabase>: update folder id', idii,
                'name',nameii, 'parentid', pidii, 'path',pathii)

        query='''INSERT OR REPLACE INTO Folders (id, name, parentId, path) \
                 VALUES (?,?,?,?)'''

        cout.execute(query, (idii, nameii, pidii, pathii))

    db.commit()

    return 0


def createNewDatabase(file_path,lib_folder,rename_files):

    dbfout=os.path.abspath(file_path)

    try:
        dbout = sqlite3.connect(dbfout)
        print('Connected to database:')
    except:
        print('Failed to connect to database:')

    cout=dbout.cursor()

    #--------------Create documents table--------------
    query='''CREATE VIRTUAL TABLE IF NOT EXISTS Documents USING fts5(
    %s)'''
    columns=[]
    for kii in DOC_ATTRS:
        if kii in INT_COLUMNS:
            columns.append('%s' %kii)
        else:
            columns.append('%s' %kii)

    columns=', '.join(columns)
    query=query %columns

    print('Creating empty table...')
    cout.execute(query)
    #dbout.commit()

    #------------Create DocumentTags table------------
    query='''CREATE VIRTUAL TABLE IF NOT EXISTS DocumentTags USING fts5(
    docid, tag)'''

    cout.execute(query)
    #dbout.commit()

    #------------Create DocumentNotes table------------
    query='''CREATE VIRTUAL TABLE IF NOT EXISTS DocumentNotes USING fts5(
    docid,
    note,
    modifiedTime,
    createdTime
    )'''

    cout.execute(query)
    #dbout.commit()

    #----------Create DocumentKeywords table----------
    query='''CREATE VIRTUAL TABLE IF NOT EXISTS DocumentKeywords USING fts5(
    docid,
    text)'''

    cout.execute(query)
    #dbout.commit()

    #-----------Create DocumentFolders table-----------
    query='''CREATE TABLE IF NOT EXISTS DocumentFolders (
    docid INT,
    folderid INT
    )'''

    cout.execute(query)
    #dbout.commit()

    #---------------Create Folders table---------------
    query='''CREATE TABLE IF NOT EXISTS Folders (
    id INTEGER PRIMARY KEY,
    name TEXT,
    parentId INT,
    path TEXT,
    UNIQUE (name, parentId)
    )'''

    cout.execute(query)
    #dbout.commit()

    #--------Create DocumentContributors table--------
    query='''CREATE VIRTUAL TABLE IF NOT EXISTS DocumentContributors USING fts5(
    docid,
    contribution,
    firstNames,
    lastName
    )'''

    cout.execute(query)
    #dbout.commit()

    #------------Create DocumentFiles table------------
    query='''CREATE TABLE IF NOT EXISTS DocumentFiles (
    docid INT,
    abspath TEXT
    )'''

    cout.execute(query)
    #dbout.commit()

    #------------Create DocumentUrls table------------
    query='''CREATE TABLE IF NOT EXISTS DocumentUrls (
    docid INT,
    url TEXT
    )'''

    cout.execute(query)
    #dbout.commit()

    #--------------create Default folder--------------
    query='''INSERT OR IGNORE INTO Folders (id, name, parentId, path)
    VALUES (?,?,?,?)'''

    cout.execute(query, (0, 'Default', -1, os.path.join(lib_folder,'Default')))
    dbout.commit()

    #-----------------Add sample file-----------------
    #fname='./sample_bib.bib'
    #bib_entries=bibparse.readBibFile(fname)

    #print('# <createNewDatabase>: sample bib file.')
    #print(bib_entries)
    #print(type(bib_entries[0]))

    #doc=bib_entries[0]
    #doc['folders_l']=[(0,'Default')]
    #doc['files_l']=['./sample_pdf.pdf',]


    #metaDictToDatabase(dbout,1,bib_entries[0],lib_folder,rename_files)

    return dbout


def metaDictToDatabase(db,docid,meta_dict,lib_folder,rename_files):

    query='''SELECT DISTINCT rowid
    FROM Documents
    '''
    docids=db.execute(query).fetchall()
    docids=[ii[0] for ii in docids]

    if docid in docids:

        if meta_dict=={}:
            print('# <metaDictToDatabase>: docid %s in database. New meta={}. Deleting...' %docid)
            LOGGER.info('docid %s in database. New meta={}. Deleting...' %docid)

            rec=delDocFromDatabase(db,docid,lib_folder)

        else:
            print('# <metaDictToDatabase>: docid %s in database. Updating...' %docid)
            LOGGER.info('docid %s in database. Updating...' %docid)

            rec=updateToDatabase(db,docid,meta_dict,lib_folder,rename_files)
    else:
        if meta_dict=={}:
            print('# <metaDictToDatabase>: docid %s not in database. New meta={}. Ignored.' %docid)
            LOGGER.info('docid %s not in database. New meta={}. Ignored.' %docid)
            rec=0

        else:
            print('# <metaDictToDatabase>: docid %s not in database. Inserting...' %docid)
            LOGGER.info('docid %s not in database. Inserting...' %docid)

            rec=addToDatabase(db,docid,meta_dict,lib_folder,rename_files)

    print('# <metaDictToDatabase>: rec=%s' %rec)

    return rec



def insertToDocuments(db,docid,meta_dict,action):

    cout=db.cursor()
    #--------------Update Documents table--------------
    key_list=[]
    value_list=[]

    for kk,vv in meta_dict.items():

        if kk in DOC_ATTRS:
            print('# <insertToDocuments>: kk=',kk,'vv=',vv)
            key_list.append(kk)
            value_list.append(vv)

    if action=='insert':
        query='''INSERT OR IGNORE INTO Documents (rowid, %s) VALUES (%s)''' \
                %(', '.join(key_list), ','.join(['?',]*(1+len(key_list))))
    elif action=='replace':
        query='''REPLACE INTO Documents (rowid, %s) VALUES (%s)''' \
                %(', '.join(key_list), ','.join(['?',]*(1+len(key_list))))
    else:
        raise Exception("action not defined.")

    cout.execute(query,[docid,]+value_list)
    db.commit()

    return 0



def insertToTable(db, table, columns, values):

    if len(values)>0:
        cout=db.cursor()

        query='INSERT OR IGNORE INTO %s (%s) VALUES (%s)' %\
                (table, ','.join(columns), ','.join(['?',]*len(columns)))

        print('# <insertToTable>: query:',query)

        for vii in values:
            cout.execute(query, vii)
        db.commit()

    return 0


def delFromTable(db, table, docid):

    cout=db.cursor()
    query='DELETE FROM %s WHERE (%s.did=?)' %(table,table)

    print('# <delFromTable>: Delete old table rows. query=%s' %query)
    LOGGER.info('Delete old table rows. query=%s' %query)

    cout.execute(query, (docid,))
    db.commit()

    return 0


def insertToDocumentFiles(db, docid, meta_dict, lib_folder, rename_files):

    cout=db.cursor()
    files=meta_dict['files_l']
    if len(files)>0:
        query='''INSERT OR IGNORE INTO DocumentFiles (did, abspath)
        VALUES (?,?)'''

        for fii in files:
            absii=os.path.expanduser(fii)
            #absii=tools.removeInvalidPathChar(absii)
            folder,filename=os.path.split(absii)
            # can't do filename change here, will cause missing file.
            #filename=re.sub(r'[<>:"|?*]','_',filename)
            if rename_files:
                filename=renameFile(fii,meta_dict)
            newabsii=os.path.join(lib_folder,'_collections')
            newabsii=os.path.join(newabsii,filename)

            # deal with name conflicts
            newabsii=autoRename(newabsii)

            cout.execute(query,(docid,newabsii))

            #--------------------Copy file--------------------
            print('# <insertToDocumentFiles>: Copy',absii,'to',newabsii)
            try:
                shutil.copy(absii, newabsii)
            except:
                print('# <insertToDocumentFiles>: Failed to copy file %s' %absii)
                LOGGER.info('Failed to copy file %s' %absii)

            print('# <insertToDocumentFiles>: Add file: %s.' %newabsii)
            LOGGER.info('Add file: %s.' %newabsii)

            print('# <insertToDocumentFiles>: Copy file %s to %s' %(absii,newabsii))
            LOGGER.info('Copy file %s to %s' %(absii,newabsii))

        db.commit()

    return 0


def addToDatabase(db,docid,meta_dict,lib_folder,rename_files):

    print('# <addToDatabase>: Add doc to database. docid=%s' %docid)
    LOGGER.info('Add doc to database. docid=%s' %docid)

    #--------------Update Documents table--------------
    rec=insertToDocuments(db, docid, meta_dict, 'insert')
    print('# <addToDatabase>: rec of insertToDocuments=%s' %rec)
    LOGGER.info('rec of insertToDocuments=%s' %rec)

    #------------------Update authors------------------
    firsts=meta_dict['firstNames_l']

    if len(firsts)>0:

        lasts=meta_dict['lastName_l']
        rec=insertToTable(db, 'DocumentContributors',
                ('did', 'contribution', 'firstNames', 'lastName'),
                list(zip((docid,)*len(firsts),
                    ('DocumentAuthor',)*len(firsts),
                    firsts, lasts))
                )

        print('# <addToDatabase>: rec of insertToDocumentAuthors=%s' %rec)
        LOGGER.info('rec of insertToDocumentAuthors=%s' %rec)

    #-------------------Update files-------------------
    rec=insertToDocumentFiles(db, docid, meta_dict, lib_folder, rename_files)

    print('# <addToDatabase>: rec of insertToDocumentFiles=%s' %rec)
    LOGGER.info('rec of insertToDocumentFiles=%s' %rec)

    #------------------Update folder------------------
    rec=insertToTable(db, 'DocumentFolders',
            ('did', 'folderid'),
            [(docid,fii[0]) for fii in meta_dict['folders_l']])

    print('# <addToDatabase>: rec of insertDocumentFolders=%s' %rec)
    LOGGER.info('rec of insertDocumentFolders=%s' %rec)

    #-----------------Update keywords-----------------
    rec=insertToTable(db, 'DocumentKeywords',
            ('did', 'text'),
            [(docid, kii) for kii in meta_dict['keywords_l']])

    print('# <addToDatabase>: rec of insertDocumentKeywords=%s' %rec)
    LOGGER.info('rec of insertDocumentKeywords=%s' %rec)

    #-------------------Update notes-------------------
    notes=meta_dict['notes']
    if notes:
        ctime=datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        rec=insertToTable(db, 'DocumentNotes',
                ('did', 'note', 'modifiedTime', 'createdTime'),
                [(docid, notes, ctime, ctime)]
                )

    print('# <addToDatabase>: rec of insertDocumentNotes=%s' %rec)
    LOGGER.info('rec of insertDocumentNotes=%s' %rec)

    #-----------------Update tags-----------------
    rec=insertToTable(db, 'DocumentTags',
            ('did', 'tag'),
            [(docid, kii) for kii in meta_dict['tags_l']])

    print('# <addToDatabase>: rec of insertDocumentTags=%s' %rec)
    LOGGER.info('rec of insertDocumentTags=%s' %rec)

    #-------------------Update urls-------------------
    rec=insertToTable(db, 'DocumentUrls',
            ('did', 'url'),
            [(docid, kii) for kii in meta_dict['urls_l']])

    print('# <addToDatabase>: rec of insertDocumentUrls=%s' %rec)
    LOGGER.info('rec of insertDocumentUrls=%s' %rec)

    print('# <addToDatabase>: Finished adding doc to database.')
    LOGGER.info('Finished adding doc to database.')

    return 0



def updateToDatabase(db,docid,meta_dict,lib_folder,rename_files):

    cout=db.cursor()

    #----------Get a meta_dict from database----------
    old_meta=getMetaData(db, docid)

    #------------------Update folders------------------
    folders=meta_dict['folders_l']
    print('# <updateToDatabase>: Current folders:', folders)

    old_folders=old_meta['folders_l']
    if set(old_folders) != set(folders):

        del_folders=list(set(old_folders).difference(folders))
        new_folders=list(set(folders).difference(old_folders))

        print('# <updateToDatabase>: old_folders:',old_folders,
                'del_folders',del_folders,
                'new_folders',new_folders)

        for fii in del_folders:

            query='''DELETE FROM DocumentFolders
            WHERE (DocumentFolders.did=? AND DocumentFolders.folderid=?)
            '''
            cout.execute(query, (docid, int(fii[0])))

        for fii in new_folders:

            query='''INSERT OR IGNORE INTO DocumentFolders (did, folderid)
            VALUES (?,?)'''

            cout.execute(query, (docid, int(fii[0])))

    #--------------Update Documents table--------------
    rec=insertToDocuments(db, docid, meta_dict, 'replace')
    print('# <updateToDatabase>: rec of insertToDocuments=%s' %rec)
    LOGGER.info('rec of insertToDocuments=%s' %rec)

    #------------------Update authors------------------
    if old_meta['authors_l']!=meta_dict['authors_l']:
        # so order change is also a change
        print('# <updateToDatabase>: need to update authors')

        #----------------Remove old authors----------------
        delFromTable(db, 'DocumentContributors', docid)

        #------------------Update authors------------------
        firsts=meta_dict['firstNames_l']

        if len(firsts)>0:

            lasts=meta_dict['lastName_l']
            rec=insertToTable(db, 'DocumentContributors',
                    ('did', 'contribution', 'firstNames', 'lastName'),
                    list(zip((docid,)*len(firsts),
                        ('DocumentAuthor',)*len(firsts),
                        firsts, lasts))
                    )

            print('# <updateToDatabase>: rec of insertToDocumentAuthors=%s' %rec)
            LOGGER.info('rec of insertToDocumentAuthors=%s' %rec)

    #-------------------Update files-------------------
    if set(old_meta['files_l']) != set(meta_dict['files_l']):

        delFromTable(db, 'DocumentFiles', docid)

        rec=insertToDocumentFiles(db, docid, meta_dict, lib_folder, rename_files)

        print('# <updateToDatabase>: rec of insertToDocumentFiles=%s' %rec)
        LOGGER.info('rec of insertToDocumentFiles=%s' %rec)

    #-----------------Update keywords-----------------
    if set(old_meta['keywords_l']) != set(meta_dict['keywords_l']):

        delFromTable(db, 'DocumentKeywords', docid)

        rec=insertToTable(db, 'DocumentKeywords',
                ('did', 'text'),
                [(docid, kii) for kii in meta_dict['keywords_l']])

        print('# <updateToDatabase>: rec of insertDocumentKeywords=%s' %rec)
        LOGGER.info('rec of insertDocumentKeywords=%s' %rec)

    #-------------------Update notes-------------------
    notes=meta_dict['notes']
    if old_meta['notes'] != notes:

        if notes:
            mtime=datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
            # Get createdTime if old note exists
            query='''
            SELECT (DocumentNotes.createdTime) FROM DocumentNotes
            WHERE (DocumentNotes.did=?)
            '''
            ctime=fetchField(db,query,(docid,),1,'str')

            if ctime is None:
                ctime=mtime

            delFromTable(db, 'DocumentNotes', docid)

            rec=insertToTable(db, 'DocumentNotes',
                    ('did', 'note', 'modifiedTime', 'createdTime'),
                    [(docid, notes, mtime, ctime)]
                    )
            print('# <updateToDatabase>: rec of insertDocumentNotes=%s' %rec)
            LOGGER.info('rec of insertDocumentNotes=%s' %rec)
        else:
            delFromTable(db, 'DocumentNotes', docid)


    #-------------------Update tags-------------------
    if set(old_meta['tags_l']) != set(meta_dict['tags_l']):

        delFromTable(db, 'DocumentTags', docid)

        rec=insertToTable(db, 'DocumentTags',
                ('did', 'tag'),
                [(docid, kii) for kii in meta_dict['tags_l']])

        print('# <updateToDatabase>: rec of insertDocumentTags=%s' %rec)
        LOGGER.info('rec of insertDocumentTags=%s' %rec)


    #-------------------Update urls-------------------
    if set(old_meta['urls_l']) != set(meta_dict['urls_l']):

        delFromTable(db, 'DocumentUrls', docid)

        rec=insertToTable(db, 'DocumentUrls',
                ('did', 'url'),
                [(docid, kii) for kii in meta_dict['urls_l']])

        print('# <updateToDatabase>: rec of insertDocumentUrls=%s' %rec)
        LOGGER.info('rec of insertDocumentUrls=%s' %rec)

    print('# <updateToDatabase>: Finished updating doc to database.')
    LOGGER.info('Finished updating doc to database.')

    return 0

def delDocFromDatabase(db,docid,lib_folder):

    cout=db.cursor()

    #--------------del Documents table--------------
    query='DELETE FROM Documents WHERE (Documents.id=?)'
    cout.execute(query, (docid,))
    #db.commit()

    #------------------del folders------------------
    delFromTable(db, 'DocumentFolders', docid)

    #------------------del authors------------------
    delFromTable(db, 'DocumentContributors', docid)

    #-------------------del files-------------------
    query_files='''
    SELECT DocumentFiles.abspath
    FROM DocumentFiles
    WHERE (DocumentFiles.did=?)
    '''

    old_files=fetchField(db, query_files, (docid,), 1, 'list')
    print('# <delDocFromDatabase>: old_files=', old_files)
    delFromTable(db, 'DocumentFiles', docid)

    for fii in old_files:
        if os.path.exists(fii):
            os.remove(fii)

    #-----------------del keywords-----------------
    delFromTable(db, 'DocumentKeywords', docid)

    #-------------------del notes-------------------
    delFromTable(db, 'DocumentNotes', docid)

    #-------------------del tags-------------------
    delFromTable(db, 'DocumentTags', docid)

    #-------------------del urls-------------------
    delFromTable(db, 'DocumentUrls', docid)

    print('# <delDocFromDatabase>: Finished deleting doc from database.')
    LOGGER.info('Finished deleting doc from database.')

    return 0
