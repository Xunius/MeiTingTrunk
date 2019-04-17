'''
Perform searches in sqlite database.


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

import sqlite3
import logging

LOGGER=logging.getLogger(__name__)



#######################################################################
#                             fts5 search NOT IN USE                  #
#######################################################################


def searchTitle(db, text):

    cin=db.cursor()

    query='''SELECT rowid,
    snippet(Documents, 14, '<b>', '</b>', '<b>...</b>', 5) title
    FROM Documents
    WHERE (Documents.title MATCH ?)
    ORDER BY rank
    '''
    print(query)

    ret=cin.execute(query,('%s*' %text,))
    ret=ret.fetchall()
    for ii in ret:
        print(ii)

    return ret

def searchAuthors(db, text):
    cin=db.cursor()

    query='''SELECT did, ("firstNames" || " " || "lastName") as name
    FROM DocumentContributors
    WHERE (DocumentContributors MATCH ?)
    ORDER By rank
    '''

    print(query)
    ret=cin.execute(query, ('%s*' %text,))
    ret=ret.fetchall()

    for ii in ret:
        print(ii)

    return ret

def searchKeywords(db, text):
    cin=db.cursor()

    query='''SELECT did, text
    FROM DocumentKeywords
    WHERE (DocumentKeywords.text MATCH ?)
    ORDER By rank
    '''

    print(query)
    ret=cin.execute(query, ('%s*' %text,))
    ret=ret.fetchall()

    for ii in ret:
        print(ii)

    return ret

def searchTags(db, text):
    cin=db.cursor()

    query='''SELECT did, tag
    FROM DocumentTags
    WHERE (DocumentTags.tag MATCH ?)
    ORDER By rank
    '''

    print(query)
    ret=cin.execute(query, ('%s*' %text,))
    ret=ret.fetchall()

    for ii in ret:
        print(ii)

    return ret

def searchNotes(db, text):
    cin=db.cursor()

    query='''SELECT did,
    snippet(DocumentNotes, 1, '<b>', '</b>', '<b>...</b>', 6) note
    FROM DocumentNotes
    WHERE (DocumentNotes.note MATCH ?)
    ORDER By rank
    '''

    print(query)
    ret=cin.execute(query, ('%s*' %text,))
    ret=ret.fetchall()

    for ii in ret:
        print(ii)

    return ret

def searchMultiple(db, text, field_list, folderid):

    cin=db.cursor()

    #-------------Append * to search term-------------
    text='%s*' %text

    #----------------Create temp table----------------
    query='''
    DROP TABLE IF EXISTS temp.search_res'''
    cin.execute(query)

    query='''
    CREATE VIRTUAL TABLE temp.search_res USING fts5(
    did, text, _rank)
    '''
    cin.execute(query)

    #---------------Compose search query---------------
    queries=[]
    for kk in field_list:
        if kk=='Authors':
            qkk='''SELECT did, ("firstNames" || " " || "lastName") as name, rank
            FROM DocumentContributors
            WHERE DocumentContributors MATCH ?
            '''
        elif kk=='Title':
            qkk='''SELECT rowid, Documents.title, rank
            FROM Documents
            WHERE Documents.title MATCH ?'''
        elif kk=='Keywords':
            qkk='''SELECT did, text, rank
            FROM DocumentKeywords
            WHERE DocumentKeywords.text MATCH ?'''
        elif kk=='Tags':
            qkk='''SELECT did, tag, rank
            FROM DocumentTags
            WHERE DocumentTags.tag MATCH ?'''
        elif kk=='Notes':
            qkk='''SELECT did,
            snippet(DocumentNotes, 1, '<b>', '</b>', '<b>...</b>', 6) note,
            rank
            FROM DocumentNotes
            WHERE DocumentNotes.note MATCH ?'''

        queries.append(qkk)

    query='''INSERT INTO temp.search_res (did, text, _rank)
    %s
    ORDER BY rank
    ''' %('UNION ALL\n'.join(queries))
    print(query)

    ret=cin.execute(query, (text,)*len(queries))

    #---------Get results and filter by folder---------
    if folderid=='-1':
        query='''SELECT search_res.did, search_res.text, search_res._rank
        FROM search_res'''
        ret=cin.execute(query)

    elif folderid=='-2':
        query='''SELECT search_res.did, search_res.text, search_res._rank
        FROM search_res
        LEFT JOIN Documents ON Documents.rowid=search_res.did
        WHERE Documents.confirmed='false'
        '''
        ret=cin.execute(query)

    elif folderid=='-3':
        query='''SELECT search_res.did, search_res.text, search_res._rank
        FROM search_res
        LEFT JOIN Documents ON Documents.rowid=search_res.did
        WHERE Documents.deletionPending='true'
        '''
        ret=cin.execute(query)

    else:
        query='''SELECT search_res.did, search_res.text, search_res._rank
        FROM search_res
        LEFT JOIN DocumentFolders ON DocumentFolders.did=search_res.did
        WHERE DocumentFolders.folderid=?'''
        ret=cin.execute(query, (folderid,))

    print(query)
    ret=ret.fetchall()
    for ii in ret:
        print(ii)

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


def getSubFolders(folder_dict, folderid):

    results=[kk for kk,vv in folder_dict.items() if vv[1]==folderid]

    subs=[]
    for fii in results:
        subids=getSubFolders(folder_dict,fii)
        subs.extend(subids)

    results.extend(subs)

    return results


#######################################################################
#             LIKE search ONLY searchMultipleLike2 IN USE             #
#######################################################################

def searchTitleLike(db, text, folderid, desend=False):

    cin=db.cursor()

    query='''SELECT Documents.id, Documents.title
    FROM Documents
    LEFT JOIN DocumentFolders
    ON DocumentFolders.did=Documents.id
    WHERE (Documents.title LIKE ?) AND
    %s
    ORDER BY Documents.title
    '''

    if desend:
        folder_dict=getFolders(db)
        subfolderids=getSubFolders(folder_dict, folderid)+[folderid,]
        print('# <searchTitleLike>: subfolderids=',subfolderids)
        folder_str='(DocumentFolders.folderid IN (%s))' %','.join(['?']*len(subfolderids))
        folder_value=tuple(subfolderids)
    else:
        folder_str='(DocumentFolders.folderid = ?)'
        folder_value=(folderid,)

    ret=cin.execute(query %folder_str,('%%%s%%' %text,) + folder_value)
    ret=ret.fetchall()

    return ret

def searchAuthorsLike(db, text):

    cin=db.cursor()
    query='''SELECT did, ("firstNames" || " " || "lastName") as name
    FROM DocumentContributors
    WHERE (name LIKE ?)
    ORDER By name
    '''
    ret=cin.execute(query, ('%%%s%%' %text,))
    ret=ret.fetchall()

    return ret

def searchKeywordsLike(db, text):

    cin=db.cursor()
    query='''SELECT did, text
    FROM DocumentKeywords
    WHERE (DocumentKeywords.text LIKE ?)
    ORDER By text
    '''
    ret=cin.execute(query, ('%%%s%%' %text,))
    ret=ret.fetchall()

    return ret



def searchTagsLike(db, text):

    cin=db.cursor()
    query='''SELECT did, tag
    FROM DocumentTags
    WHERE (DocumentTags.tag LIKE ?)
    ORDER By tag
    '''
    ret=cin.execute(query, ('%%%s%%' %text,))
    ret=ret.fetchall()

    return ret


def searchNotesLike(db, text):

    cin=db.cursor()
    query='''SELECT did, note
    FROM DocumentNotes
    WHERE (DocumentNotes.note LIKE ?)
    ORDER By note
    '''

    ret=cin.execute(query, ('%%%s%%' %text,))
    ret=ret.fetchall()

    return ret


def searchMultipleLike(db, text, field_list, folderid, desend=False):

    cin=db.cursor()

    #-------------Append % to search term-------------
    text='%%%s%%' %text

    #----------------Create temp table----------------
    query='''
    DROP TABLE IF EXISTS temp.search_res'''
    cin.execute(query)

    query='''
    CREATE TABLE temp.search_res (
    did, text, field)
    '''
    cin.execute(query)

    #---------------Compose search query---------------
    queries=[]
    for kk in field_list:
        if kk=='Authors':
            qkk='''SELECT did, ("firstNames" || " " || "lastName") as name, 'authors'
            FROM DocumentContributors
            WHERE name LIKE ?'''
        elif kk=='Title':
            qkk='''SELECT id, Documents.title, 'title'
            FROM Documents
            WHERE Documents.title LIKE ?'''
        elif kk=='Keywords':
            qkk='''SELECT did, text, 'keywords'
            FROM DocumentKeywords
            WHERE DocumentKeywords.text LIKE ?'''
        elif kk=='Tags':
            qkk='''SELECT did, tag, 'tag'
            FROM DocumentTags
            WHERE DocumentTags.tag LIKE ?'''
        elif kk=='Notes':
            qkk='''SELECT did, note, 'note'
            FROM DocumentNotes
            WHERE DocumentNotes.note LIKE ?'''
        elif kk=='Publication':
            qkk='''SELECT id, Documents.publication, 'publication'
            FROM Documents
            WHERE Documents.publication LIKE ?'''
        elif kk=='Abstract':
            qkk='''SELECT id, Documents.abstract, 'abstract'
            FROM Documents
            WHERE Documents.abstract LIKE ?'''
        else:
            continue

        queries.append(qkk)

    query='''INSERT INTO temp.search_res (did, text, field)
    %s
    ''' %('UNION ALL\n'.join(queries))

    ret=cin.execute(query, (text,)*len(queries))

    #---------Get results and filter by folder---------
    query='''SELECT search_res.did,
    group_concat(search_res.field, ',')
    FROM search_res
    %s
    GROUP BY search_res.did
    '''
    #query='''SELECT search_res.did,
    #search_res.text,
    #search_res.field
    #FROM search_res
    #%s
    #ORDER BY search_res.did
    #'''

    if folderid=='-1':
        query=query %''
        ret=cin.execute(query)

    elif folderid=='-2':
        query=query %'''
        LEFT JOIN Documents ON Documents.id=search_res.did
        WHERE Documents.confirmed='false'
        '''
        ret=cin.execute(query)

    elif folderid=='-3':
        query=query %'''
        LEFT JOIN Documents ON Documents.id=search_res.did
        WHERE Documents.deletionPending='true'
        '''
        ret=cin.execute(query)

    else:
        query=query %'''
        LEFT JOIN DocumentFolders ON DocumentFolders.did=search_res.did
        WHERE DocumentFolders.folderid=?
        '''
        ret=cin.execute(query, (folderid,))

    #print(query)
    ret=ret.fetchall()

    #for ii in ret:
        #print(ii)

    return ret

def searchMultipleLike2(db, text, field_list, folderid, desend=False):
    """Combined sqlite searches in multiple tables

    Args:
        db (sqlite connection): sqlite connection.
        text (str): search text.
        field_list (list): list of fields to search, including 'Authors',
                          'Title', 'Keywords', 'Tags', 'Notes', 'Publication',
                          'Abstract'.
        folderid (str): id of folder, search in done within docs in this folder.

    Kwargs:
        desend (bool): whether to include subfolders (by walking done folder
                       tree) of given folder.

    Returns: rec (list): list of doc ids matching search, together with the
        field names where the match is found. E.g.

        [(1, 'authors,title'),
         (10, 'title,keywords'),
         (214, 'abstract,tag'),
         ...
        ]
    """

    cin=db.cursor()

    #-------------Append % to search term-------------
    text='%%%s%%' %text

    #----------------Create temp table----------------
    query='''
    DROP TABLE IF EXISTS temp.search_res'''
    cin.execute(query)

    query='''
    CREATE TABLE temp.search_res (
    did, text, field)
    '''
    cin.execute(query)

    #---------------Compose search query---------------
    queries=[]
    for kk in field_list:
        if kk=='Authors':
            qkk='''SELECT did, ("firstNames" || " " || "lastName") as name, 'authors'
            FROM DocumentContributors
            WHERE name LIKE ?'''
        elif kk=='Title':
            qkk='''SELECT id, Documents.title, 'title'
            FROM Documents
            WHERE Documents.title LIKE ?'''
        elif kk=='Keywords':
            qkk='''SELECT did, text, 'keywords'
            FROM DocumentKeywords
            WHERE DocumentKeywords.text LIKE ?'''
        elif kk=='Tags':
            qkk='''SELECT did, tag, 'tag'
            FROM DocumentTags
            WHERE DocumentTags.tag LIKE ?'''
        elif kk=='Notes':
            qkk='''SELECT did, note, 'note'
            FROM DocumentNotes
            WHERE DocumentNotes.note LIKE ?'''
        elif kk=='Publication':
            qkk='''SELECT id, Documents.publication, 'publication'
            FROM Documents
            WHERE Documents.publication LIKE ?'''
        elif kk=='Abstract':
            qkk='''SELECT id, Documents.abstract, 'abstract'
            FROM Documents
            WHERE Documents.abstract LIKE ?'''
        else:
            continue

        queries.append(qkk)

    query='''INSERT INTO temp.search_res (did, text, field)
    %s
    ''' %('UNION ALL\n'.join(queries))

    ret=cin.execute(query, (text,)*len(queries))

    #---------Get results and filter by folder---------
    query='''SELECT search_res.did,
    group_concat(search_res.field, ',')
    FROM search_res
    %s
    GROUP BY search_res.did
    '''

    #---------Compose folder filtering string---------
    if folderid=='-1':
        query=query %''
        ret=cin.execute(query)
        subfolderids=None
    elif folderid=='-2':
        query=query %'''
        LEFT JOIN Documents ON Documents.id=search_res.did
        WHERE Documents.confirmed='false'
        '''
        ret=cin.execute(query)
        subfolderids=folderid
    else:
        if desend:
            folder_dict=getFolders(db)
            subfolderids=getSubFolders(folder_dict, folderid)+[folderid,]
        else:
            subfolderids=[folderid,]

        LOGGER.debug('subfolder ids = %s' %subfolderids)

        query=query %'''
        LEFT JOIN DocumentFolders ON DocumentFolders.did=search_res.did
        WHERE (DocumentFolders.folderid IN (%s))
        ''' %','.join(['?']*len(subfolderids))
        ret=cin.execute(query, subfolderids)

    ret=ret.fetchall()

    return ret, subfolderids





if __name__=='__main__':

    dbfile='../nonfts3.sqlite'

    db = sqlite3.connect(dbfile)
    #cin=db.cursor()

    #aa=searchTitle(db, 'effect')
    #aa=searchAuthors(db, 'Che')
    #aa=searchKeywords(db, 'ENSO')
    #aa=searchTags(db, 'ENSO')
    #aa=searchNotes(db, 'the')
    #aa=searchMultiple(db, 'ENSO')

    field_list=['Authors', 'Title', 'Keywords', 'Tag', \
            'Abstract', 'Publication', 'Notes']
    #aa=searchMultipleLike2(db, 'ENSO', field_list, '16')
    aa=searchMultipleLike2(db, 'ENSO', ['Title',' Keywords', 'Abstract'], '16', True)
    bb=searchTitleLike(db, 'ENSO', '16', True)
    for ii in bb:
        print(ii)

    #folder_dict=getFolders(db)
    #ff=getSubFolders(folder_dict,'16')

