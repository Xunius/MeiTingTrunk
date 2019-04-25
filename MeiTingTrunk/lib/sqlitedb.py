'''
In-memory meta data dict (DocMeta) definition.
Sqlite database read and write functions.


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

import os
import shutil
import time
import re
import multiprocessing
from urllib.parse import quote
from datetime import datetime
import sqlite3
import logging
from send2trash import send2trash
from collections import MutableMapping
from .tools import autoRename, isXapianReady, parseAuthors
if isXapianReady():
    from . import xapiandb

DOC_ATTRS=[\
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

LOGGER=logging.getLogger(__name__)


class DocMeta(MutableMapping):
    '''A custom dict definition storing meta data of a document

    Allow only a given list of keys and restrict keys to str type.
    Give default values to keys.
    Some values are returned in a getter manner.

    keys ending with '_l' suffix denotes a list value, e.g. 'authors_l'.
    '''

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
        if value is None:
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
    """Read sqlite data

    Args:
        dbin (sqlite connection): connection to sqlite.

    Returns:
        meta (dict): meta data of all documents. keys: docid,
            values: DocMeta dict.
        folder_data (dict): documents in each folder. keys: folder id in str,
            values: list of doc ids.
        folder_dict (dict): folder structure info. keys: folder id in str,
            values: (foldername, parentid) tuple.
    """

    #-------------------Get folders-------------------
    folder_dict=getFolders(dbin)
    LOGGER.debug('Got %d folders from database.' %len(folder_dict))

    #-------------------Get metadata-------------------
    meta={}

    # this is when I tried fts5 tables in sqlite where 'rowid' was hardwared
    # by sqlite, and eventually switched back to normal table.
    cursor=dbin.execute('SELECT * FROM Documents')
    names=list(map(lambda x:x[0], cursor.description))
    query='''SELECT DISTINCT %s
    FROM Documents
    ''' %('id' if 'id' in names else 'rowid')

    docids=dbin.execute(query).fetchall()
    docids=[ii[0] for ii in docids]
    docids.sort()

    folder_data={}
    folder_data['-2']=[] # needs review folder
    folder_data['-3']=[] # trash can folder

    for idii in docids:

        metaii=getMetaData(dbin,idii)
        meta[idii]=metaii

        if metaii['confirmed'] is None or metaii['confirmed']=='false':
            folder_data['-2'].append(idii)
        if metaii['deletionPending']=='true' and len(metaii['folders_l'])==0:
            folder_data['-3'].append(idii)

        folderii=metaii['folders_l'] # (folderid, foldername)

        # convert folder id to str, as QListWidgetItem request str. very annoying
        # remember to convert back to int when writing to sqlite
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

    LOGGER.info('Done reading in sqlite database.')
    LOGGER.info('len(meta) = %d. len(folder_dict) = %d'\
            %(len(meta), len(folder_dict)))

    return meta, folder_data, folder_dict


def fetchField(db, query, values, ncol=1, ret_type='str'):
    """Query columns from sqlite and do some formatting

    Args:
        db (sqlite connection): sqlite connection.
        query (str): SELECT statement template.
        values (tuple): value list used in sqlite execute.

    Kwargs:
        ncol (int): number of columns queried in <query>.
        ret_type (str): if 'str' and ncol==1, return a single string.
                        if 'str' and ncol>1, return a list of strings.
                        if 'list', return a list.

    Returns: aa: column values. See ret_type.
    """

    if ret_type not in ['str','list']:
        raise Exception("<ret_type> is one of ['str','list'].")

    aa=db.execute(query,values).fetchall()

    if len(aa)==0:
        # don't think this ever happens. Null is returned as None
        if ret_type=='str':
            return None
        else:
            return []

    if ncol==1:
        aa=[ii[0] for ii in aa]
    if ret_type=='str':
        if len(aa)==1:
            if aa[0] is None:
                return None
            else:
                return str(aa[0])
        else:
            return '; '.join(aa)
    else:
        return aa


def getMetaData(db, did):
    """Get meta data of a given document from sqlite

    Args:
        db (sqlite connection): sqlite connection.
        did (int): id of doc.

    Returns: result (DocMeta): meta data dict.
    """

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
    SELECT DocumentFiles.relpath
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
    fields=['citationkey','title','issue','pages',\
            'publication','volume','year','doi','abstract',\
            'arxivId','chapter','city','country','edition','institution',\
            'isbn','issn','month','day','publisher','series','type',\
            'read','favourite','pmid','added','confirmed', 'deletionPending']

    result=DocMeta()

    if 'id' in names:
        vii=fetchField(db,query_base %'id', (did,))
        result['id']=int(vii)
    else:
        vii=fetchField(db,query_base %'rowid', (did,))
        result['rowid']=vii

    # query single-worded fields, e.g. year, city
    for kii in fields:
        vii=fetchField(db,query_base %(kii), (did,))
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

    #LOGGER.debug('Done fetching meta data for doc %s' %str(did))

    return result


def zipAuthors(firstnames, lastnames):
    """Create author name list from lists of first names and last names.

    Args:
        firstnames (list): list of first names.
        lastnames (list): list of last names.

    Returns: authors (list): author names list.

    """

    if len(firstnames)!=len(lastnames):
        LOGGER.error('Length of firstname and lastname dont match.')
        LOGGER.error('firstnames = %s' %firstnames)
        LOGGER.error('lastnames = %s' %lastnames)
        raise Exception("Length of firstname and lastname dont match.")
    authors=[]
    for ii in range(len(firstnames)):
        fii=firstnames[ii]
        lii=lastnames[ii]
        if fii!='' and lii!='':
            authors.append('%s, %s' %(lii.strip(),fii.strip()))
        elif fii=='' and lii!='':
            authors.append(lii)
        elif fii!='' and lii=='':
            authors.append(fii)

    return authors


def getSubFolders(folder_dict, folderid):
    """Get all subfolders of a give folder

    Args:
        folder_dict (dict): folder structure info. keys: folder id in str,
            values: (foldername, parentid) tuple.
        folderid (str): id of given folder.

    Returns: results (list): list of folder ids. Subfolders walked from given
             folder.
    """

    results=[kk for kk,vv in folder_dict.items() if vv[1]==folderid]

    subs=[]
    for fii in results:
        subids=getSubFolders(folder_dict,fii)
        subs.extend(subids)

    results.extend(subs)

    return results


def getTrashedFolders(folder_dict):
    """Get all folders inside Trash

    Args:
        folder_dict (dict): folder structure info. keys: folder id in str,
            values: (foldername, parentid) tuple.

    Returns: results (list): list of folder ids. Subfolders walked from the
             Trash (id='-3') folder.
    """
    '''
    results=[kk for kk,vv in folder_dict.items() if vv[1]=='-3']


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
    '''
    results = getSubFolders(folder_dict, '-3')
    LOGGER.debug('Ids of trashed folders = %s' %results)
    return results


def walkFolderTree(folder_dict, folder_data, folderid, docids=None,
        folderids=None):
    """Get subfolders walked from a given folder and all docs within

    Args:
        folder_dict (dict): folder structure info. keys: folder id in str,
            values: (foldername, parentid) tuple.
        folder_data (dict): documents in each folder. keys: folder id in str,
            values: list of doc ids.
        folderid (str): id of folder to start the walk.

    Kwargs:
        docids (list): list storing the doc ids in folders visited during the
                       walk. If None, create an empty list.
        folderids (list): list storing the ids of folders visited during the
                       walk. If None, create an empty list.

    Returns:
        docids (list): list storing the doc ids in folders visited during the
                       walk.
        folderids (list): list storing the ids of folders visited during the
                       walk.

    """

    if docids is None:
        docids=[]
    if folderids is None:
        folderids=[]

    docids.extend(folder_data[folderid])
    folderids.append(folderid)

    subfolderids=getChildFolders(folder_dict,folderid)
    for sii in subfolderids:
        folderids,docids=walkFolderTree(folder_dict,folder_data,sii,
                docids,folderids)

    folderids=list(set(folderids))
    docids=list(set(docids))

    return folderids,docids


def findOrphanDocs(folder_data, docids, trashed_folder_ids):
    """Identify orphan docs from a given list of doc ids

    Args:
        folder_data (dict): documents in each folder. keys: folder id in str,
            values: list of doc ids.
        docids (list): list of doc ids, within which orphan docs are searched.
        trashed_folder_ids (list): list of ids of folders inside Trash.

    Returns: result (list): list of orphan doc ids.

    Orphan docs are defined as those that ONLY appear in Trash, or folder(s)
    inside Trash.
    """

    idsinfolders=[]

    for kk,vv in folder_data.items():
        if kk not in ['-1','-2','-3']+trashed_folder_ids:
            idsinfolders.extend(vv)

    result=[idii for idii in docids if idii not in idsinfolders]

    LOGGER.debug('excluded folders = ["-1","-2","-3"]+%s' %trashed_folder_ids)
    LOGGER.debug('Orphan docs = %s' %result)

    return result


def findOrphanDocs2(db):
    '''Find orphan docs from sqlite data

    Not in use.
    '''

    cin=db.cursor()
    query='''SELECT rowid FROM Documents
    WHERE Documents.deletionPending='true'
    '''
    ret=cin.execute(query)
    ret=[ii[0] for ii in ret]

    LOGGER.debug('Orphan docs = %s' %ret)

    return ret


def getFolders(db):
    """Read folder info from sqlite

    Args:
        db (sqlite connection): sqlite connection.

    Returns: df (dict): folder structure info. keys: folder id in str,
            values: (foldername, parentid) tuple.
    """

    #-----------------Get all folders-----------------
    query='''SELECT id, name, parentId
    FROM Folders
    '''
    ret=db.execute(query)
    data=ret.fetchall()

    # dict, key: folderid, value: (folder_name, parent_id)
    # note: convert id to str
    df=dict([(str(ii[0]), (ii[1], str(ii[2]))) for ii in data])

    return df


def fetchMetaData(meta_dict, key, docids, unique, sort):
    """Get the meta data values of a given key within a list of docs

    Args:
        meta_dict (dict): meta data of all documents. keys: docid,
            values: DocMeta dict.
        key (str): key in DocMeta to get value.
        docids (list): list of doc ids within which search is done.
        unique (bool): remove duplicate or not.
        sort (bool): sort result list or not.

    Returns: result (list): list of values.

    """
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


def filterDocs(meta_dict, docids, filter_type, filter_text):
    """Filter docs using a given filter text

    Args:
        meta_dict (dict): meta data of all documents. keys: docid,
            values: DocMeta dict.
        docids (list): list of int doc ids to perform filter.
        filter_type (str): defines the field of the filter_text.
        filter_text (str): filtering text.

    Returns: results (list): ids of docs within folder given by
             <current_folder>, containing the text <filter_text> in the field
             defined by <filter_type>.
    """

    results=[]

    if filter_type=='Filter by authors':
        t_last,t_first=map(str.strip,filter_text.split(','))
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

    return results


def getChildFolders(folder_dict, folderid):
    """Get child folders of a given folder

    Args:
        folder_dict (dict): folder structure info. keys: folder id in str,
            values: (foldername, parentid) tuple.
        folderid (str): id of given folder.

    Returns: results (list): list of ids of child folders.

    NOTE: different from getSubFolders() that this only get direct child
    folders of a given folder, while getSubFolders() walks done the folder
    tree.
    """

    results=[]
    for idii in folder_dict:
        fii,pii=folder_dict[idii]
        if pii==folderid:
            results.append(idii)
    results.sort()
    return results


def getFolderTree(folder_dict, folderid):
    """Get a str representation of a given folder in the folder tree

    Args:
        folder_dict (dict): folder structure info. keys: folder id in str,
            values: (foldername, parentid) tuple.
        folderid (str): id of given folder.

    Returns:
        folderid (str): input folder id.
        folder (str): path of the given folder in the tree.
    """

    getFolderName=lambda folder_dict,id: folder_dict[id][0]
    getParentId=lambda folder_dict,id: folder_dict[id][1]

    folder=getFolderName(folder_dict,folderid)

    #------------Back track tree structure------------
    cid=folderid
    while True:
        pid=str(getParentId(folder_dict,cid))
        if pid=='-1':
            break
        else:
            pfolder=getFolderName(folder_dict,pid)
            folder=os.path.join(pfolder,folder)
        cid=pid

    return folderid,folder


def renameFile(fname, meta_dict, replace_space=False):
    """Rename a attachment file using meta data

    Args:
        fname (str): abspath of a file.
        meta_dict (DocMeta): meta data dict.

    Kwargs:
        replace_space (bool): whether to replace spaces in file name with some
                              symbol.

    Returns: fname2 (str): renamed file name. NOTE this doesn't include folder
                           path, ONLY file name.

    The file name is constrcuted from meta data in the format:

        Author_year_title.ext

    If the renamed abspath is too long (>255-6), the title field is cropped.
    If a doc contains more than 1 attachment files, an int index is appended
    before extension to distinguish them.
    Chars that are invalid in Linux, Mac or Win are removed, such as ':', '?'.
    """

    dirjj,filenamejj=os.path.split(fname)
    basename,ext=os.path.splitext(filenamejj)

    # get first author
    author=meta_dict['lastName_l']
    if len(author)>0:
        author=author[0]
        if author is None or author=='':
            author='Unknown'
        else:
            author=author.strip()
    else:
        author='Unknown'

    # get year
    year=meta_dict['year']
    if year is None:
        year='unknown'
    else:
        year=str(year).strip()

    # get title
    title=meta_dict['title'] or basename
    title=title.strip()

    LOGGER.debug('author = %s, year = %s, title = %s' %(author,year,title))

    # crop length
    fname2='%s_%s_%s%s' %(author,year,title,ext)
    len1=len(dirjj)+1+len(fname2)
    if len1>255-6:
        title=title[:255-6-len1]

        LOGGER.debug('Cropped title = %s' %title)

    #---------Handle multiple files for a doc---------
    if len(meta_dict['files_l'])==1:
        fname2='%s_%s_%s%s' %(author,year,title,ext)
    else:
        fname2='%s_%s_%s_%d%s' %(author,year,title,\
                meta_dict['files_l'].index(fname), ext)

        LOGGER.debug('Appending idx to a mutli-file doc.')

    if replace_space:
        fname2=fname2.replace(' ','-')

    fname2=re.sub(r'[<>:"|/\?*]','_',fname2)

    LOGGER.info('Old filename = %s. New filename = %s' %(fname,fname2))

    return fname2


def saveFoldersToDatabase(db, folder_ids, folder_dict, lib_folder):
    """Save folder changes to sqlite

    Args:
        db (sqlite connection): connection to sqlite.
        folder_ids (list): list of ids (in str) of folders to save.
        folder_dict (dict): folder structure info. keys: folder id in str,
            values: (foldername, parentid) tuple.
        lib_folder (str): abspath to the folder of the library. By design
                          this should point to the folder CONTAINING the
                          sqlite database file.

    Returns: 0
    """

    cout=db.cursor()
    folder_ids=list(set(folder_ids))
    LOGGER.info('Saving folders with ids = %s' %folder_ids)

    for idii in folder_ids:

        folder=folder_dict.get(idii)
        if folder is None:
            # deleting folder
            LOGGER.info('Deleting folder with id = %s' %idii)
            query='''
            DELETE FROM Folders WHERE Folders.id=?
            '''
            cout.execute(query, (int(idii),))
        else:
            nameii,pidii=folder_dict[idii]
            idii=int(idii)
            pathii=os.path.join(lib_folder,nameii)
            pathii=os.path.abspath(pathii)

            LOGGER.info('Updating folder, id = %s, name = %s, pid = %s, path = %s'\
                    %(idii, nameii, pidii, pathii))

            query='''INSERT OR REPLACE INTO Folders (id, name, parentId, path) \
                     VALUES (?,?,?,?)'''
            cout.execute(query, (idii, nameii, pidii, pathii))

    db.commit()
    LOGGER.info('Done saving folders')

    return 0


def createNewDatabase(file_path):
    """Create a new sqlite database for a new library

    Args:
        file_path (str): abspath of the sqlite database file.

    Returns:
        dbout (sqlite connection): connection to the new sqlite database.
        dirname (str): abspath to the folder containing the sqlite database,
                       ie dir part of <file_path>.
        lib_name (str): library name, taken as the file name of <file_path>
                        without extension.
    """

    # make sure has .sqlite ext
    dirname,filename=os.path.split(file_path)
    lib_name,ext=os.path.splitext(filename)
    if ext=='':
        filename='%s.sqlite' %lib_name
        file_path=os.path.join(dirname,filename)

    dbfout=os.path.abspath(file_path)

    try:
        dbout = sqlite3.connect(dbfout)
        LOGGER.info('Connected to databaase %s' %file_path)
    except Exception:
        LOGGER.exception('Failed to connect to database %s' %file_path)

    cout=dbout.cursor()

    #dirname,filename=os.path.split(file_path)
    #lib_name,ext=os.path.splitext(filename)
    lib_folder=os.path.join(dirname,lib_name)

    if not os.path.exists(lib_folder):
        os.makedirs(lib_folder)
        LOGGER.info('Create lib folder %s' %lib_folder)

    file_folder=os.path.join(lib_folder,'_collections')
    if not os.path.exists(file_folder):
        os.makedirs(file_folder)
        LOGGER.info('Create lib collections folder %s' %file_folder)

    #--------------Create documents table--------------
    query='''CREATE TABLE IF NOT EXISTS Documents (
    id INTEGER PRIMARY KEY,
    %s)'''
    columns=[]
    for kii in DOC_ATTRS:
        if kii in INT_COLUMNS:
            columns.append('%s INT' %kii)
        else:
            columns.append('%s TEXT' %kii)

    columns=', '.join(columns)
    query=query %columns

    LOGGER.info('Creating empty table ...')
    cout.execute(query)
    #dbout.commit()

    #------------Create DocumentTags table------------
    query='''CREATE TABLE IF NOT EXISTS DocumentTags (
    did INT,
    tag TEXT)'''

    cout.execute(query)
    #dbout.commit()

    #------------Create DocumentNotes table------------
    query='''CREATE TABLE IF NOT EXISTS DocumentNotes (
    did INT,
    note TEXT,
    modifiedTime TEXT,
    createdTime TEXT
    )'''

    cout.execute(query)
    #dbout.commit()

    #----------Create DocumentKeywords table----------
    query='''CREATE TABLE IF NOT EXISTS DocumentKeywords (
    did INT,
    text TEXT)'''

    cout.execute(query)
    #dbout.commit()

    #-----------Create DocumentFolders table-----------
    query='''CREATE TABLE IF NOT EXISTS DocumentFolders (
    did INT,
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
    query='''CREATE TABLE IF NOT EXISTS DocumentContributors (
    did INT,
    contribution TEXT,
    firstNames TEXT,
    lastName TEXT
    )'''

    cout.execute(query)
    #dbout.commit()

    #------------Create DocumentFiles table------------
    query='''CREATE TABLE IF NOT EXISTS DocumentFiles (
    did INT,
    relpath TEXT
    )'''

    cout.execute(query)
    #dbout.commit()

    #------------Create DocumentUrls table------------
    query='''CREATE TABLE IF NOT EXISTS DocumentUrls (
    did INT,
    url TEXT
    )'''

    cout.execute(query)
    #dbout.commit()

    #--------------create Default folder--------------
    query='''INSERT OR IGNORE INTO Folders (id, name, parentId, path)
    VALUES (?,?,?,?)'''

    #cout.execute(query, (0, 'Default', -1, os.path.join(lib_folder,'Default')))
    cout.execute(query, (0, 'Default', -1, os.path.join(lib_name,'Default')))
    dbout.commit()

    LOGGER.info('Created empty table.')

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

    return dbout, dirname, lib_name


def metaDictToDatabase(db, docid, meta_dict_all, meta_dict, lib_folder,
        rename_files, add_manner):
    """Save document changes to sqlite

    Args:
        db (sqlite connection): sqlite connection.
        docid (int): id of doc to save changes.
        meta_dict_all (dict): meta data of all documents. keys: docid,
            values: DocMeta dict.
        meta_dict (DocMeta): meta data dict.
        lib_folder (str): abspath to the folder of the library. By design
                          this should point to the folder CONTAINING the
                          sqlite database file.
        rename_files (int): 1 for renaming attachment files when saving, 0
                            for using original file name.
        add_manner (int): file adding manner. If 'copy', copy added attachment
                          into lib_folder/_collections/. If 'link', create
                          symbolic link.

    Returns: rec (int): 0 if success, None otherwise.
             reload_doc (bool): if True, call loadDocTable() to refresh changes
                                in the 'files_l' field later.

    3 types of changes are handled in this function:
        * insertion: <docid> is not found in sqlite, addToDatabase() is called.
        * deletion: <docid> in in sqlite, and <meta_dict> is None,
                    delDocFromDatabase() is called.
        * update: <docid> is in sqlite, and <meta_dict> is not None,
                  updateToDatabase() is called.
    """

    query='''SELECT DISTINCT rowid
    FROM Documents
    '''
    docids=db.execute(query).fetchall()
    docids=[ii[0] for ii in docids]

    LOGGER.debug('rename_files = %s' %rename_files)

    if docid in docids:

        if meta_dict is None:
            LOGGER.info('docid %s in database. New meta=None. Deleting...' %docid)
            rec=delDocFromDatabase(db,docid,lib_folder)
            reload_doc=False
        else:
            LOGGER.info('docid %s in database. Updating...' %docid)
            rec,reload_doc=updateToDatabase(db, docid, meta_dict, lib_folder,
                    rename_files, add_manner)
    else:
        if meta_dict is None:
            LOGGER.info('docid %s not in database. New meta=None. Ignore.' %docid)
            rec=0
        else:
            LOGGER.info('docid %s not in database. Inserting...' %docid)
            rec,reload_doc=addToDatabase(db, docid, meta_dict, lib_folder,
                    rename_files, add_manner)

    if reload_doc:
        meta_dict_all[docid]=getMetaData(db,docid)

    #----------------Call xapian index----------------
    xapian_folder=os.path.join(lib_folder,'_xapian_db')
    if isXapianReady() and os.path.exists(xapian_folder):
        proc=multiprocessing.Process(target=xapiandb.indexFolder, args=(
            xapian_folder, lib_folder), daemon=False)
        LOGGER.debug('Start indexing process')
        proc.start()

    LOGGER.info('Done updating doc to database. Need to reload_doc = %s' %reload_doc)

    return rec, reload_doc


def insertToDocuments(db, docid, meta_dict, action):
    """Insert or update columns in the Documents table

    Args:
        db (sqlite connection): sqlite connection.
        docid (int): id of doc to save changes.
        meta_dict (DocMeta): meta data dict.
        action (str): if 'insert', use 'INSERT OR IGNORE' sqlite statement.
                      if 'replace', use 'REPLACE INTO' sqlite statement.

    Returns: 0
    """

    cout=db.cursor()
    #--------------Update Documents table--------------
    key_list=[]
    value_list=[]

    for kk,vv in meta_dict.items():

        if kk in DOC_ATTRS:
            LOGGER.debug('key = %s, value = %s' %(str(kk), str(vv)))
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

    LOGGER.info('Done inserting doc %s to Documents table.' %docid)

    return 0


def insertToTable(db, table, columns, values):
    """Insert columns in a given table

    Args:
        db (sqlite connection): sqlite connection.
        table (str): table name.
        columns (list): column names.
        values (list or tuple): new values to save to columns.

    Returns: 0
    """

    if len(values)>0:
        cout=db.cursor()
        query='INSERT OR IGNORE INTO %s (%s) VALUES (%s)' %\
                (table, ','.join(columns), ','.join(['?',]*len(columns)))
        for vii in values:
            cout.execute(query, vii)
        db.commit()

    LOGGER.info('Done inserting to %s table.' %table)

    return 0


def delFromTable(db, table, docid):
    """Delete table rows matching given doc id

    Args:
        db (sqlite connection): sqlite connection.
        table (str): table name.
        docid (int): doc id.

    Returns: 0
    """

    cout=db.cursor()
    query='DELETE FROM %s WHERE (%s.did=?)' %(table,table)
    cout.execute(query, (docid,))
    db.commit()
    LOGGER.debug('Deleted old rows in table %s with docid = %s' %(table,docid))

    return 0


def insertToDocumentFiles(db, docid, meta_dict, lib_folder, rename_files,
        add_manner):
    """Insert or update columns in the DocumentsFiles table

    Args:
        db (sqlite connection): sqlite connection.
        docid (int): id of doc to save changes.
        meta_dict (DocMeta): meta data dict.
        lib_folder (str): abspath to the folder of the library. By design
                          this should point to the folder CONTAINING the
                          sqlite database file.
        rename_files (int): 1 for renaming attachment files when saving, 0
                            for using original file name.
        add_manner (int): file adding manner. If 'copy', copy added attachment
                          into lib_folder/_collections/. If 'link', create
                          symbolic link.

    Returns: 0

    The path of each attachment file of the give doc is renamed if required,
    and copied to a specified folder corresponding to the library.
    A relative file path, relative to <lib_folder>, is obtained, and saved
    to sqlite.
    """

    cout=db.cursor()
    _,lib_name=os.path.split(lib_folder)
    if lib_name=='':
        lib_name=os.path.split(_)[1]

    abs_file_folder=os.path.join(lib_folder,'_collections')
    rel_file_folder=os.path.join('','_collections')
    rename_files=int(rename_files) # make sure this int, not str
    LOGGER.debug('lib_name = %s' %lib_name)
    LOGGER.debug('abs_file_folder = %s' %abs_file_folder)
    LOGGER.debug('rel_file_folder = %s' %rel_file_folder)
    LOGGER.debug('rename_files = %s' %rename_files)

    if not os.path.exists(abs_file_folder):
        os.makedirs(abs_file_folder)

    files=meta_dict['files_l']
    files_updated=[]
    if len(files)>0:
        query='''INSERT OR IGNORE INTO DocumentFiles (did, relpath)
        VALUES (?,?)'''

        LOGGER.debug('files_l=%s' %files)
        for fii in files:
            LOGGER.debug('fii=%s' %fii)

            # this is a newly added file, therefore it's abs
            if os.path.isabs(fii):
                new_file=True
                # check new file is in the same lib
                #common=os.path.commonprefix([abs_file_folder,fii])
                dirname=os.path.dirname(fii)
                if dirname==abs_file_folder:
                    LOGGER.warning('Adding a file from within lib: %s'\
                            %fii)

            # this file is already added to lib, therefore it's rel
            else:
                new_file=False

            #--------------Compose new file name--------------
            if rename_files:
                newfilename=renameFile(fii,meta_dict)
            else:
                newfilename=os.path.split(fii)[1]
                newfilename=re.sub(r'[<>:"|/\?*]','_',newfilename)

            newabsii=os.path.join(abs_file_folder,newfilename)

            if new_file:
                # deal with name conflicts
                newabsii=autoRename(newabsii)
                newfilename=os.path.split(newabsii)[1]
                oldabsii=fii
            else:
                # deal with name conflicts?
                newabsii=autoRename(newabsii)
                newfilename=os.path.split(newabsii)[1]
                oldfilename=os.path.split(fii)[1]
                oldabsii=os.path.join(abs_file_folder,oldfilename)

            rel_fii=os.path.join(rel_file_folder,newfilename)
            cout.execute(query,(docid,rel_fii))

            files_updated.append(rel_fii)

            LOGGER.debug('new abspath = %s' %newabsii)
            LOGGER.debug('new relpath = %s' %rel_fii)

            #------------Copy or link or move file------------
            if new_file:
                try:
                    if add_manner=='copy':
                        shutil.copy(oldabsii,newabsii)
                    elif add_manner=='link':
                        os.symlink(oldabsii,newabsii)
                    LOGGER.info('%s file %s -> %s' %(add_manner,oldabsii,newabsii))
                except:
                    LOGGER.exception('Failed to %s file %s to %s'\
                            %(add_manner,oldabsii,newabsii))
            else:
                try:
                    shutil.move(oldabsii,newabsii)
                    LOGGER.info('move file %s -> %s' %(oldabsii,newabsii))
                except:
                    LOGGER.exception('Failed to move file %s to %s'\
                            %(oldabsii,newabsii))

            '''
            #-----------------Update to xapian-----------------
            if isXapianReady():
                try:
                    rec=xapiandb.indexFile(abs_xapian_folder, newabsii, rel_fii,
                            meta_dict)
                    if rec==1:
                        LOGGER.error('Failed to index attachment %s' %fii)
                except:
                    LOGGER.exception('Failed to index attachment %s' %fii)
            '''

        db.commit()

    # update meta_dict
    meta_dict['files_l']=files_updated
    LOGGER.info('Done inserting doc %s to DocumentFiles' %docid)

    return 0


def addToDatabase(db, docid, meta_dict, lib_folder, rename_files, add_manner):
    """Add new document to sqlite

    Args:
        db (sqlite connection): sqlite connection.
        docid (int): id of doc to save changes.
        meta_dict (DocMeta): meta data dict.
        lib_folder (str): abspath to the folder of the library. By design
                          this should point to the folder CONTAINING the
                          sqlite database file.
        rename_files (int): 1 for renaming attachment files when saving, 0
                            for using original file name.
        add_manner (int): file adding manner. If 'copy', copy added attachment
                          into lib_folder/_collections/. If 'link', create
                          symbolic link.

    Returns: rec (int): 0 if success, None otherwise.
             reload_doc (bool): if True, call loadDocTable() to refresh changes
                                in the 'files_l' field later.
    """

    LOGGER.info('Adding doc to database. docid = %s' %docid)

    #--------------Update Documents table--------------
    rec=insertToDocuments(db, docid, meta_dict, 'insert')
    LOGGER.debug('rec of insertToDocuments = %s' %rec)

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
        LOGGER.debug('rec of insertToDocumentAuthors = %s' %rec)

    #-------------------Update files-------------------
    if len(meta_dict['files_l'])>0:
        rec=insertToDocumentFiles(db, docid, meta_dict, lib_folder,
                rename_files, add_manner)
        LOGGER.debug('rec of insertToDocumentFiles = %s' %rec)
        reload_doc=True
    else:
        reload_doc=False

    #------------------Update folder------------------
    rec=insertToTable(db, 'DocumentFolders',
            ('did', 'folderid'),
            [(docid,fii[0]) for fii in meta_dict['folders_l']])
    LOGGER.debug('rec of insertDocumentFolders = %s' %rec)

    #-----------------Update keywords-----------------
    rec=insertToTable(db, 'DocumentKeywords',
            ('did', 'text'),
            [(docid, kii) for kii in meta_dict['keywords_l']])
    LOGGER.debug('rec of insertDocumentKeywords = %s' %rec)

    #-------------------Update notes-------------------
    notes=meta_dict['notes']
    if notes:
        ctime=datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        rec=insertToTable(db, 'DocumentNotes',
                ('did', 'note', 'modifiedTime', 'createdTime'),
                [(docid, notes, ctime, ctime)]
                )
    LOGGER.debug('rec of insertDocumentNotes = %s' %rec)

    #-----------------Update tags-----------------
    rec=insertToTable(db, 'DocumentTags',
            ('did', 'tag'),
            [(docid, kii) for kii in meta_dict['tags_l']])
    LOGGER.debug('rec of insertDocumentTags = %s' %rec)

    #-------------------Update urls-------------------
    rec=insertToTable(db, 'DocumentUrls',
            ('did', 'url'),
            [(docid, kii) for kii in meta_dict['urls_l']])
    LOGGER.debug('rec of insertDocumentUrls = %s' %rec)

    LOGGER.info('Done adding doc to database.')

    return 0, reload_doc


def updateToDatabase(db, docid, meta_dict, lib_folder, rename_files,
        add_manner):
    """Save changes of existing document to sqlite

    Args:
        db (sqlite connection): sqlite connection.
        docid (int): id of doc to save changes.
        meta_dict (DocMeta): meta data dict.
        lib_folder (str): abspath to the folder of the library. By design
                          this should point to the folder CONTAINING the
                          sqlite database file.
        rename_files (int): 1 for renaming attachment files when saving, 0
                            for using original file name.
        add_manner (int): file adding manner. If 'copy', copy added attachment
                          into lib_folder/_collections/. If 'link', create
                          symbolic link.

    Returns: rec (int): 0 if success, None otherwise.
             reload_doc (bool): if True, call loadDocTable() to refresh changes
                                in the 'files_l' field later.
    """

    cout=db.cursor()
    LOGGER.info('Updating doc to database. docid = %s' %docid)

    #----------Get a meta_dict from database----------
    old_meta=getMetaData(db, docid)

    #------------------Update folders------------------
    folders=meta_dict['folders_l']
    old_folders=old_meta['folders_l']
    LOGGER.debug('previous folders = %s. current folders = %s'\
            %(old_folders, folders))

    if set(old_folders) != set(folders):

        del_folders=list(set(old_folders).difference(folders))
        new_folders=list(set(folders).difference(old_folders))
        LOGGER.debug('Need to update folders.')
        LOGGER.debug('del folders = %s. new folders = %s'\
                %(del_folders, new_folders))

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
    LOGGER.debug('rec of insertToDocuments = %s' %rec)

    #------------------Update authors------------------
    if old_meta['authors_l']!=meta_dict['authors_l']:
        # order change is also a change
        LOGGER.debug('Need to update authors.')

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
            LOGGER.debug('rec of insertToDocumentAuthors = %s' %rec)

    #-------------------Update files-------------------
    if set(old_meta['files_l']) != set(meta_dict['files_l']):

        LOGGER.debug('Need to update files.')
        delFromTable(db, 'DocumentFiles', docid)
        rec=insertToDocumentFiles(db, docid, meta_dict, lib_folder,
                rename_files, add_manner)
        LOGGER.debug('rec of insertToDocumentFiles=%s' %rec)

        # any old file to del?
        del_files=list(set(old_meta['files_l']).difference(set(meta_dict['files_l'])))
        if len(del_files)>0:
            xapian_folder=os.path.join(lib_folder,'_xapian_db')
            LOGGER.info('Deleting old files: %s' %del_files)
            for fii in del_files:
                # del from xapian
                if isXapianReady() and os.path.exists(xapian_folder):
                    try:
                        urlii='U/%s' %quote(fii)
                        print('# <updateToDatabase>: urlii=',urlii)
                        rec=xapiandb.delXapianDoc(xapian_folder, urlii)
                        if rec==1:
                            LOGGER.error('Failed to delete from xapian.')
                    except:
                        LOGGER.exception('Failed to delete from xapian.')

                absii=os.path.join(lib_folder,fii)
                if os.path.exists(absii):
                    LOGGER.info('Deleting file from disk %s' %absii)
                    #os.remove(absii)
                    send2trash(absii)
                    #NOTE that files deleted by send2trash seems to be
                    # unable to restore, at least in linux

        reload_doc=True
    else:
        reload_doc=False

    #-----------------Update keywords-----------------
    if set(old_meta['keywords_l']) != set(meta_dict['keywords_l']):

        LOGGER.debug('Need to update keywords.')
        delFromTable(db, 'DocumentKeywords', docid)
        rec=insertToTable(db, 'DocumentKeywords',
                ('did', 'text'),
                [(docid, kii) for kii in meta_dict['keywords_l']])
        LOGGER.debug('rec of insertDocumentKeywords = %s' %rec)

    #-------------------Update notes-------------------
    notes=meta_dict['notes']
    if old_meta['notes'] != notes:

        LOGGER.debug('Need to update notes.')

        if notes:
            mtime=datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
            # Get createdTime if old note exists
            query='''
            SELECT (DocumentNotes.createdTime) FROM DocumentNotes
            WHERE (DocumentNotes.did=?)
            '''
            ctime=fetchField(db,query,(docid,),1,'str')

            if ctime is None:
                LOGGER.debug('Old creation time not exists. Use current time.')
                ctime=mtime

            delFromTable(db, 'DocumentNotes', docid)

            rec=insertToTable(db, 'DocumentNotes',
                    ('did', 'note', 'modifiedTime', 'createdTime'),
                    [(docid, notes, mtime, ctime)]
                    )
            LOGGER.debug('rec of insertDocumentNotes = %s' %rec)
        else:
            delFromTable(db, 'DocumentNotes', docid)

    #-------------------Update tags-------------------
    if set(old_meta['tags_l']) != set(meta_dict['tags_l']):

        LOGGER.debug('Need to update tags.')

        delFromTable(db, 'DocumentTags', docid)
        rec=insertToTable(db, 'DocumentTags',
                ('did', 'tag'),
                [(docid, kii) for kii in meta_dict['tags_l']])
        LOGGER.debug('rec of insertDocumentTags = %s' %rec)

    #-------------------Update urls-------------------
    if set(old_meta['urls_l']) != set(meta_dict['urls_l']):

        LOGGER.debug('Need to update urls.')

        delFromTable(db, 'DocumentUrls', docid)
        rec=insertToTable(db, 'DocumentUrls',
                ('did', 'url'),
                [(docid, kii) for kii in meta_dict['urls_l']])
        LOGGER.debug('rec of insertDocumentUrls = %s' %rec)

    LOGGER.info('Done updating doc to database.')

    return 0, reload_doc


def delDocFromDatabase(db, docid, lib_folder):
    """Delete existing document from sqlite

    Args:
        db (sqlite connection): sqlite connection.
        docid (int): id of doc to delete.
        lib_folder (str): abspath to the folder of the library. By design
                          this should point to the folder CONTAINING the
                          sqlite database file.

    Returns: rec (int): 0 if success, None otherwise.
    """

    cout=db.cursor()
    LOGGER.info('Deleting doc %s from database' %docid)

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
    SELECT DocumentFiles.relpath
    FROM DocumentFiles
    WHERE (DocumentFiles.did=?)
    '''
    old_files=fetchField(db, query_files, (docid,), 1, 'list')
    delFromTable(db, 'DocumentFiles', docid)

    #-----------------Del from xapian-----------------
    xapian_folder=os.path.join(lib_folder,'_xapian_db')
    sqlitepath=db.execute('PRAgMA database_list').fetchall()[0][2]
    if isXapianReady() and os.path.exists(xapian_folder):
        try:
            xapiandb.delByDocid2(xapian_folder, sqlitepath, docid)
        except:
            LOGGER.exception('Failed to delete from xapian.')

    for ii, fii in enumerate(old_files):
        # prepend folder path
        absii=os.path.join(lib_folder,fii)
        if os.path.exists(absii):
            LOGGER.info('Deleting file from disk %s' %absii)
            #os.remove(absii)
            send2trash(absii)

    #-----------------del keywords-----------------
    delFromTable(db, 'DocumentKeywords', docid)

    #-------------------del notes-------------------
    delFromTable(db, 'DocumentNotes', docid)

    #-------------------del tags-------------------
    delFromTable(db, 'DocumentTags', docid)

    #-------------------del urls-------------------
    delFromTable(db, 'DocumentUrls', docid)

    LOGGER.info('Done deleting doc from database.')

    return 0


def replaceTerm(db, field, old_terms, new_term):
    '''Replace terms

    Args:
        db (sqlite connection): sqlite connection.
        field (str): field of replacement, one of 'Authors', 'Journals',
                     'Keywords', 'Tags'.
        old_terms (list): list of terms to replace.
        new_term (str): new term to use.
    '''

    LOGGER.debug('new_term = %s' %new_term)
    LOGGER.debug('old_terms = %s' %old_terms)

    if field=='Authors':
        firstnames, lastnames, authors=parseAuthors(old_terms)
        newf, newlast, newauthor=parseAuthors([new_term,])
        newf=newf[0]
        newlast=newlast[0]

        LOGGER.debug('firstnames = %s' %firstnames)
        LOGGER.debug('lastnames = %s' %lastnames)
        LOGGER.debug('new firstname = %s' %newf)
        LOGGER.debug('new lastnames = %s' %newlast)

        query='''UPDATE DocumentContributors SET
        firstNames = ?,
        lastName = ?
        WHERE (firstNames = ? AND lastName = ?)
        '''

        for fii, lii in zip(firstnames, lastnames):
            if fii==newf and lii==newlast:
                continue
            LOGGER.debug('Updating %s %s' %(fii, lii))
            db.execute(query, (newf, newlast, fii, lii))
    else:
        if field=='Journals':
            table_name='Documents'
            column_name='publication'
        elif field=='Keywords':
            table_name='DocumentKeywords'
            column_name='text'
        elif field=='Tags':
            table_name='DocumentTags'
            column_name='tag'

        query='''UPDATE %s SET
        %s = ?
        WHERE %s = ?
        ''' %(table_name, column_name, column_name)

        for ii in old_terms:
            if ii==new_term:
                continue
            db.execute(query, (new_term, ii))

    db.commit()

    return


