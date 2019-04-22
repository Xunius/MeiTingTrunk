'''
Import data from Mendeley.


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''


import sys
import os
import sqlite3
import shutil
import re
import logging
import time
from datetime import datetime
if sys.version_info[0]>=3:
    #---------------------Python3---------------------
    from urllib.parse import unquote
    from urllib.parse import urlparse
else:
    #--------------------Python2.7--------------------
    from urllib import unquote
    from urlparse import urlparse

from . import sqlitedb
from . import exportpdf
from . import tools
if tools.isXapianReady():
    from . import xapiandb
from bs4 import BeautifulSoup


LOGGER=logging.getLogger(__name__)


# columns to read from Mendeley database
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

# columns to create in output sqlite
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


DOI_PATTERN=re.compile(r'(?:doi:)?\s?(10.[1-9][0-9]{3}/.*$)',
        re.DOTALL|re.UNICODE)

# Sometimes citation imported via a .bib or .ris file may contain
# a note field (`annote = {{some note}} `for .bib, `N1 - some note` for .ris).
# It can be doi strings:
#    * doi: 10.1021/ed020p517.1
#    * 10.1021/ed020p517.1
# It can also be ISBN strings: e.g. ISBN 978.....
# It can also be PMID strings: e.g. PMID: xxxx
# It could be something else, whatever the citation provider decides to put in.
# So to distinguish them from actuall notes made by users, below is a list
# of regex patterns trying to catch some recognizable patterns and exclude
# them from the notes.

NOTE_EXCLUDE_PATTERNS=[
        DOI_PATTERN,
        ]


def getDocIds(db):
    '''Get a list of docids from a folder'''

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
    """Perform SELECT query on given column(s) filtered by docid

    Args:
        cursor (sqlite connection cursor): sqlite connection cursor.
        table (str): table name.
        column (str or list/tuple): column name or names.
        docid (int): doc id.

    Returns: list of column values. If <column> is str, a list with one element.
    """

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


def convert2datetime(s):
    return datetime.strptime(s,'%Y-%m-%dT%H:%M:%SZ')


def getUserName(db):
    '''Query db to get user name'''

    query=\
    '''SELECT Profiles.firstName, Profiles.lastName
    FROM Profiles WHERE Profiles.isSelf="true"
    '''
    query_fallback=\
    '''SELECT Profiles.firstName, Profiles.lastName
    FROM Profiles
    '''
    ret=db.execute(query).fetchall()
    if len(ret)==0:
        ret=db.execute(query_fallback).fetchall()
    return ' '.join(filter(None,ret[0]))


def getFilePath(db, docid):
    """Get file path of PDF(s) using documentId

    Args:
        db (sqlite connection): connection to sqlite database.
        docid (int): doc id

    Returns: pth (list or None): None if no path is found. A list of file paths
             otherwise.
    """

    query=\
    '''SELECT Files.localUrl
       FROM Files
       LEFT JOIN DocumentFiles
           ON DocumentFiles.hash=Files.hash
       LEFT JOIN Documents
           ON Documents.id=DocumentFiles.documentId
       WHERE (Documents.id=%s)
    ''' %docid

    ret=db.execute(query)
    data=ret.fetchall()
    if len(data)==0:
        return None
    else:
        pth=[converturl2abspath(urlii[0]) for urlii in data]
        return pth


def getHighlights(db, filterdocid, results=None):
    '''Extract highlights coordinates and related meta data.

    Args:
        db (sqlite connection): connection to Mendeley sqlite database.
        filterdocid (int): doc id .
    Kwargs:
        results (dict or None): dict to store results. If None, create an
                                empty dict.

    Returns:
        results (dict): dictionary containing the query results, with the
                        following structure:

        results=
            {
            path1:
                {'highlights': {page1: [hl1, hl2,...],
                                page2: [hl1, hl2,...],
                                ...}
                }
                 'notes': {page1: [nt1, nt2,...],
                           page2: [nt1, nt2,...],
                           ...}
            path2:
                ...
            }

            where hl1={'rect': bbox,\
                       'cdate': cdate,\
                       'color': color,
                       'page':pg,
                        'author':'highlight author',\
                       'path':pth
                      }
                  note={'rect': bbox,\
                        'author':'note author',\
                        'content':docnote,\
                        'cdate': datetime.now(),\
                        'page':pg,
                        'path':pth
                        }

    '''

    # For Mendeley versions newer than 1.16.1 (include), with highlight colors
    query_new =\
    '''SELECT Files.localUrl, FileHighlightRects.page,
                    FileHighlightRects.x1, FileHighlightRects.y1,
                    FileHighlightRects.x2, FileHighlightRects.y2,
                    FileHighlights.createdTime,
                    FileHighlights.author,
                    Profiles.firstName,
                    Profiles.lastName,
                    FileHighlights.color
            FROM Files
            LEFT JOIN FileHighlights
                ON FileHighlights.fileHash=Files.hash
            LEFT JOIN FileHighlightRects
                ON FileHighlightRects.highlightId=FileHighlights.id
            LEFT JOIN Profiles
                ON Profiles.uuid=FileHighlights.profileUuid
            WHERE (FileHighlightRects.page IS NOT NULL) AND
            (FileHighlights.documentId=%s)
    ''' %filterdocid

    # For Mendeley versions older than 1.16.1, no highlight colors
    query_old =\
    '''SELECT Files.localUrl, FileHighlightRects.page,
                    FileHighlightRects.x1, FileHighlightRects.y1,
                    FileHighlightRects.x2, FileHighlightRects.y2,
                    FileHighlights.createdTime,
                    FileHighlights.author,
                    Profiles.firstName,
                    Profiles.lastName
            FROM Files
            LEFT JOIN FileHighlights
                ON FileHighlights.fileHash=Files.hash
            LEFT JOIN FileHighlightRects
                ON FileHighlightRects.highlightId=FileHighlights.id
            LEFT JOIN Profiles
                ON Profiles.uuid=FileHighlights.profileUuid
            WHERE (FileHighlightRects.page IS NOT NULL) AND
            (FileHighlights.documentId=%s)
    ''' %filterdocid

    if results is None:
        results={}

    #------------------Get highlights------------------
    try:
        ret = db.execute(query_new)
        hascolor=True
    except:
        ret = db.execute(query_old)
        hascolor=False

    for ii,r in enumerate(ret):
        pth = converturl2abspath(r[0])
        pg = r[1]
        bbox = [r[2], r[3], r[4], r[5]]
        # [x1,y1,x2,y2], (x1,y1) being bottom-left,
        # (x2,y2) being top-right. Origin at bottom-left.
        # Fix incorrect storage ordering in Mendeley:
        if bbox[0] > bbox[2]: bbox[0], bbox[2] = bbox[2], bbox[0]
        if bbox[1] > bbox[3]: bbox[1], bbox[3] = bbox[3], bbox[1]
        cdate = convert2datetime(r[6])

        # Changes suggested by matteosecli: retrieve author of highlight:
        author=r[7]
        if not author.strip():
            author=' '.join(filter(None,r[8:10]))

        color=r[10] if hascolor else None

        hlight = {'rect': bbox,\
                  'cdate': cdate,\
                  'color': color,
                  'page': pg,
                  'author': author,
                  'path': pth   # distinguish between multi-attachments
                  }

        #------------Save to dict------------
        # any better way of doing this sht?
        if pth in results:
            if 'highlights' in results[pth]:
                if pg in results[pth]['highlights']:
                    results[pth]['highlights'][pg].append(hlight)
                else:
                    results[pth]['highlights'][pg]=[hlight,]
            else:
                results[pth]['highlights']={pg:[hlight,]}
        else:
            results[pth]={'highlights': {pg:[hlight,]}}


    return results


#-------------------Get sticky notes-------------------
def getNotes(db, filterdocid, results=None):
    '''Extract notes and related meta data

    Args:
        db (sqlite connection): connection to Mendeley sqlite database.
        filterdocid (int): doc id .
    Kwargs:
        results (dict or None): dict to store results. If None, create an
                                empty dict.

    Returns:
        results (dict): dictionary containing the query results. See
                        getHighlights() for more details.
    '''

    query=\
    '''SELECT Files.localUrl, FileNotes.page,
                    FileNotes.x, FileNotes.y,
                    FileNotes.note,
                    FileNotes.modifiedTime,
                    FileNotes.author,
                    Profiles.firstName,
                    Profiles.lastName
            FROM Files
            LEFT JOIN FileNotes
                ON FileNotes.fileHash=Files.hash
            LEFT JOIN Profiles
                ON Profiles.uuid=FileNotes.profileUuid
            WHERE (FileNotes.page IS NOT NULL) AND
            (FileNotes.documentId=%s)
    ''' %filterdocid

    if results is None:
        results={}

    #------------------Get notes------------------
    ret = db.execute(query)

    for ii,r in enumerate(ret):
        pth = converturl2abspath(r[0])
        pg = r[1]
        bbox = [r[2], r[3], r[2]+30, r[3]+30]
        # needs a rectangle, size does not matter

        txt = r[4]
        cdate = convert2datetime(r[5])

        # Changes suggested by matteosecli: retrieve author of note:
        author=r[6]
        if not author.strip():
            author=' '.join(filter(None,r[7:9]))

        note = {'rect': bbox,\
                'author':author,\
                'content':txt,\
                'cdate': cdate,\
                'page':pg,
                'path':pth,
                'isgeneralnote': False
                  }

        #------------Save to dict------------
        if pth in results:
            if 'notes' in results[pth]:
                if pg in results[pth]['notes']:
                    results[pth]['notes'][pg].append(note)
                else:
                    results[pth]['notes'][pg]=[note,]
            else:
                results[pth]['notes']={pg:[note,]}
        else:
            results[pth]={'notes': {pg:[note,]}}


    return results


#-------------------Get side-bar notes-------------------
def getDocNotes(db, filterdocid, results=None):
    '''Extract side-bar notes and related meta data

    Args:
        db (sqlite connection): connection to Mendeley sqlite database.
        filterdocid (int): doc id .
    Kwargs:
        results (dict or None): dict to store results. If None, create an
                                empty dict.

    Returns:
        results (dict): dictionary containing the query results. See
                        getHighlights() for more details.
    '''

    # Some versions of Mendeley saves notes in DocumentsNotes
    query=\
    '''SELECT DocumentNotes.text,
              DocumentNotes.documentId,
              DocumentNotes.baseNote
            FROM DocumentNotes
            WHERE (DocumentNotes.documentId IS NOT NULL) AND
            (DocumentNotes.documentId=%s)
    ''' %filterdocid

    # Some versions (not sure which exactly) of Mendeley saves
    # notes in Documents.note
    query2=\
    '''SELECT Documents.note
            FROM Documents
            WHERE (Documents.note IS NOT NULL) AND
            (Documents.id=%s)
    ''' %filterdocid

    # regex to transform Mendeley's old note formatting to html
    # e.g. <m:bold>Bold</m:bold>  to <bold>Bold</bold>
    pattern=re.compile(r'<(/?)m:(bold|italic|underline|center|left|right|linebreak)(/?)>',
            re.DOTALL | re.UNICODE)
    subfunc=lambda match: u'<%s%s%s>' %match.groups()

    if results is None:
        results={}

    #------------------Get notes------------------
    ret=[]
    try:
        ret1 = db.execute(query).fetchall()
        ret.extend(ret1)
    except:
        pass
    try:
        ret2 = db.execute(query2).fetchall()
        ret.extend(ret2)
    except:
        pass
    username=getUserName(db)

    for ii,rii in enumerate(ret):
        docnote=rii[0]
        if len(docnote)==0:
            # skip u''
            continue

        # skip things that are not user notes. See def of NOTE_EXCLUDE_PATTERNS
        skip=False
        for patternii in NOTE_EXCLUDE_PATTERNS:
            if patternii.match(docnote) is not None:
                skip=True
                break

        if skip:
            continue

        docid=filterdocid
        try:
            basenote=rii[2]
        except:
            basenote=None
        pg=1

        if docnote is not None and basenote is not None\
                and docnote!=basenote:
            docnote=basenote+'\n\n'+docnote

        #--------Convert old <m:tag> to html <tag>--------
        docnote=re.sub(pattern,subfunc,docnote)

        #--------------------Parse html--------------------
        soup=BeautifulSoup(docnote,'html.parser')
        # replace <br> tags with newline
        for br in soup.find_all('br'):
            br.replace_with('\n')
        docnote=soup.get_text()
        '''
        parser=html2text.HTML2Text()
        parser.ignore_links=True
        docnote=parser.handle(docnote)
        '''

        # Try get file path
        #pth=getFilePath(db,docid) or '/pseudo_path/%s.pdf' %title
        pth=getFilePath(db,docid) # a list, could be more than 1, or None
        # If no attachment, use None as path
        if pth is None:
            # make it compatible with the for loop below
            pth=[None,]

        bbox = [50, 700, 80, 730]
        # needs a rectangle, size does not matter
        note = {'rect': bbox,
                'author': username,
                'content':docnote,
                'cdate': datetime.now(),
                'page':pg,
                'path':pth,
                'isgeneralnote': True
                  }

        #-------------------Save to dict-------------------
        # if multiple attachments, add to each of them
        for pthii in pth:
            if pthii in results:
                if 'notes' in results[pthii]:
                    if pg in results[pthii]['notes']:
                        results[pthii]['notes'][pg].insert(0,note)
                    else:
                        results[pthii]['notes'][pg]=[note,]
                else:
                    results[pthii]['notes']={pg:[note,]}
            else:
                results[pthii]={'notes': {pg:[note,]}}


    return results


def importMendeleyPreprocess(jobid, file_in_path, file_out_path):
    """Prepare for copying Mendeley data

    Args:
        jobid (int): job id.
        file_in_path (str): abspath of Mendeley sqlite database file.
        file_out_path (str): abspath of output sqlite database file.

    Returns:
        rec (int): 0 for success, 1 otherwise.
        jobid (int): the input jobd returned as it is.
        dbin (sqlite connection): connection to sqlite at <file_in_path>.
        dbout (sqlite connection): connection to sqlite at <file_out_path>.
        docids (list): list of int doc ids in Mendeley sqlite.
        lib_folder (str): path to a newly created folder to store PDF files.
        lib_name (str): name of the output library.

    In this function, an empty sqlite database is created, and folder info
    obtained from Mendeley database are copied over. A list of doc ids is
    get from Mendeley, used for data transfer in importMendeleyCopyData().
    """

    try:
        #--------------Connect input database--------------
        dbfin=os.path.abspath(file_in_path)

        try:
            dbin = sqlite3.connect(dbfin)
            LOGGER.info('Connected to database %s' %file_in_path)
        except:
            LOGGER.exception('Failed to connect to database %s' %file_in_path)
            return 1, jobid, None, None, None, None, None

        cin=dbin.cursor()

        #-----------------Create empty db-----------------
        file_out_path=os.path.expanduser(file_out_path)
        dbout, storage_folder, lib_name=sqlitedb.createNewDatabase(file_out_path)
        cout=dbout.cursor()

        lib_folder=os.path.join(storage_folder,lib_name)
        rel_lib_folder=os.path.join('', lib_name) # relative to storage folder

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
        rename_file, ii, docii, do_indexing):
    """Copy document data from Mendeley and commit to output sqlite

    Args:
        jobid (int): job id.
        dbin (sqlite connection): connection to sqlite at <file_in_path>.
        dbout (sqlite connection): connection to sqlite at <file_out_path>.
        lib_folder (str): path to a newly created folder to store PDF files.
        lib_name (str): name of the output library.
        rename_file (bool): whether to rename attachment PDF files when copying.
        ii (int): index of a doc id in the doc id list. This is used as the
                  doc id in the output sqlite.
        docii (int or None): if int, id of the copied doc. If None, call
                             commit() on <dbout> and close() on <dbin>.
        do_indexing (bool): do xapian indexing or not.

    Returns:
        rec (int): 0 if success copy. 1 if failed. 2 if failed to export
                   annotations in the attachment PDF(s).
        jobid (int): input jobid.
        file_fail (str): paths of PDF files that failed to get their
                         annotations exported.
    """

    if docii is None:
        # this signals db commit
        dbout.commit()
        dbout.close()
        dbin.close()
        return 0, jobid, None

    cout=dbout.cursor()
    cin=dbin.cursor()

    file_folder=os.path.join(lib_folder,'_collections')
    rel_lib_folder=os.path.join('', lib_name) # relative to storage folder
    rel_file_folder=os.path.join('','_collections')

    if do_indexing:
        xapian_folder=os.path.join(lib_folder, '_xapian_db')
        xapian_db=xapiandb.createDatabase(xapian_folder)

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
        notes=selByDocid(cin, 'FileNotes', ['note', 'modifiedTime',
            'createdTime'], docii)

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

        #---------------Fetch pdf highlights and notes---------
        annotations={}
        annotations = getHighlights(dbin,docii,annotations)
        annotations = getNotes(dbin,docii,annotations)
        annotations = getDocNotes(dbin,docii,annotations)

        #------------------Get file paths------------------
        query='''SELECT Files.localUrl
        FROM Files
        LEFT JOIN DocumentFiles ON DocumentFiles.hash = Files.hash
        WHERE DocumentFiles.documentId = ?'''

        ret=cin.execute(query, (docii,))

        fileurl=ret.fetchall()
        meta_dictii['files_l']=[]

        file_fail_list=[]
        xapian_fail_list=[]
        if len(fileurl)>0:

            for fileii in fileurl:
                urlii=fileii[0]
                filepath=converturl2abspath(urlii)
                meta_dictii['files_l'].append(filepath)

            for filepath in meta_dictii['files_l']:

                #-------------------Rename file-------------------
                if rename_file:
                    filename=sqlitedb.renameFile(filepath,meta_dictii)
                else:
                    filename=os.path.split(filepath)[1]

                #---------------Remove invalid chars---------------
                filename=re.sub(r'[//\ <>:"|?*]','_',filename)
                filename=re.sub(r'al.','al',filename)
                filename=re.sub(r'_-_','_',filename)
                filename=filename.strip()

                relpath=os.path.join(rel_file_folder,filename)

                query='''INSERT INTO DocumentFiles (did, relpath)
                VALUES (?, ?)'''
                cout.execute(query, (ii, relpath))

                #---------------------Copy file---------------------
                abspath=os.path.join(file_folder, filename)

                #LOGGER.debug('relpath = %s' %relpath)
                LOGGER.debug('abspath = %s' %abspath)
                if len(annotations)>0 and filepath in annotations:
                    anno=annotations[filepath]
                    try:
                        exportpdf.exportPdf(filepath, abspath, anno)
                    except:
                        LOGGER.warning('Failed to export annotated pdf %s'\
                                %filepath)
                        file_fail_list.append(filepath)
                        try:
                            shutil.copy2(filepath,abspath)
                            LOGGER.debug('Copied %s to %s' %(filepath, abspath))
                        except:
                            LOGGER.exception('Failed to copy %s to %s' %(filepath,
                                abspath))
                else:
                    try:
                        shutil.copy2(filepath,abspath)
                        LOGGER.debug('Copied %s to %s' %(filepath, abspath))
                    except:
                        LOGGER.exception('Failed to copy %s to %s' %(filepath,
                            abspath))

                #-----------------Update to xapian-----------------
                if do_indexing:
                    try:
                        rec=xapiandb.indexFile(xapian_folder, filepath, relpath,
                                {'id': ii}, db=xapian_db)
                        if rec==1:
                            xapian_fail_list.append(filepath)
                            LOGGER.error('Failed to index attachment %s' %filepath)
                    except:
                        xapian_fail_list.append(filepath)
                        LOGGER.exception('Failed to index attachment %s' %filepath)

        if len(file_fail_list)>0:
            if len(xapian_fail_list)>0:
                return 4, jobid, '%s\n%s' %('; '.join(file_fail_list),
                        '; '.join(xapian_fail_list))
            else:
                return 2, jobid, '; '.join(file_fail_list)
        elif len(xapian_fail_list)>0:
            return 3, jobid, '; '.join(xapian_fail_list)
        else:
            return 0, jobid, None

    except Exception as e:
        LOGGER.exception('Failed to copy data for doc %s' %docii)
        return 1, jobid, None




def importMendeley(file_in_path, file_out_path, rename_file):
    '''For debug'''

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

    #importMendeley(FILE_IN_NAME, FILE_OUT_NAME, True)
    FILE_OUT_NAME='../New_Folder/men.sqlite'
    FILE_IN_NAME='../mendeley.sqlite'
    rec, jobid, dbin, dbout, docids, lib_folder, lib_name=\
    importMendeleyPreprocess(0, FILE_IN_NAME, FILE_OUT_NAME)

    for ii, docii in enumerate(docids):
        rec2, jobid, fail_list = importMendeleyCopyData(1, dbin, dbout, lib_name, lib_folder,
            True, ii, docii)

        print('rec = ', rec2, 'jobid = ', jobid, 'fail=', fail_list)
