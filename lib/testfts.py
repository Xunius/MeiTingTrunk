import sqlite3




def searchTitle(db, text):

    cin=db.cursor()

    query='''SELECT Documents.rowid,
    snippet(Documents, 14, '<b>', '</b>', '<b>...</b>', 15) title
    FROM Documents
    LEFT JOIN DocumentFolders ON DocumentFolders.did=Documents.rowid
    WHERE (Documents.title MATCH ?) AND (DocumentFolders.folderid=7)
    ORDER BY rank
    '''

    query='''SELECT Documents.rowid,
    snippet(Documents, 14, '<b>', '</b>', '<b>...</b>', 15) title
    FROM Documents
    WHERE (Documents.title MATCH ?) AND (Documents.deletionPending='true')
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


def searchMultiple(db, text):

    cin=db.cursor()

    query='''
    DROP TABLE IF EXISTS temp.search_res'''
    cin.execute(query)
    db.commit()

    query='''
    CREATE VIRTUAL TABLE temp.search_res USING fts5(
    did, text, _rank)
    '''
    cin.execute(query)
    db.commit()

    query='''
    INSERT INTO temp.search_res (did, text, _rank)
        SELECT rowid, Documents.title, rank
        FROM Documents
        WHERE Documents.title MATCH ?
    UNION ALL
        SELECT did, DocumentKeywords.text, rank
        FROM DocumentKeywords
        WHERE DocumentKeywords.text MATCH ?
    ORDER BY rank
    '''

    print(query)
    ret=cin.execute(query, (text, text))

    query='''SELECT * FROM search_res'''
    ret=cin.execute(query)
    ret=ret.fetchall()
    for ii in ret:
        print(ii)

    return ret


def searchTitleLike(db, text):

    cin=db.cursor()

    query='''SELECT Documents.id, Documents.title
    FROM Documents
    WHERE (Documents.title LIKE ?)
    ORDER BY Documents.title
    '''

    print(query)

    ret=cin.execute(query,('%%%s%%' %text,))
    ret=ret.fetchall()
    for ii in ret:
        print(ii)

    return ret


def searchAuthorsLike(db, text):
    cin=db.cursor()

    query='''SELECT did, ("firstNames" || " " || "lastName") as name
    FROM DocumentContributors
    WHERE (name LIKE ?)
    ORDER By name
    '''

    print(query)
    ret=cin.execute(query, ('%%%s%%' %text,))
    ret=ret.fetchall()

    for ii in ret:
        print(ii)

    return ret

def searchKeywordsLike(db, text):
    cin=db.cursor()

    query='''SELECT did, text
    FROM DocumentKeywords
    WHERE (DocumentKeywords.text LIKE ?)
    ORDER By text
    '''

    print(query)
    ret=cin.execute(query, ('%%%s%%' %text,))
    ret=ret.fetchall()

    for ii in ret:
        print(ii)

    return ret



def searchTagsLike(db, text):
    cin=db.cursor()

    query='''SELECT did, tag
    FROM DocumentTags
    WHERE (DocumentTags.tag LIKE ?)
    ORDER By tag
    '''

    print(query)
    ret=cin.execute(query, ('%%%s%%' %text,))
    ret=ret.fetchall()

    for ii in ret:
        print(ii)

    return ret


def searchNotesLike(db, text):
    cin=db.cursor()

    query='''SELECT did, note
    FROM DocumentNotes
    WHERE (DocumentNotes.note LIKE ?)
    ORDER By note
    '''

    print(query)
    ret=cin.execute(query, ('%%%s%%' %text,))
    ret=ret.fetchall()

    for ii in ret:
        print(ii)

    return ret

def searchMultipleLike1(db, text):

    cin=db.cursor()

    query='''
    DROP TABLE IF EXISTS temp.search_res'''
    cin.execute(query)
    db.commit()

    query='''
    CREATE TABLE temp.search_res (
    did, text, field)
    '''
    cin.execute(query)
    db.commit()
    __import__('pdb').set_trace()

    query='''
    INSERT INTO temp.search_res (did, text, field)
        SELECT id, Documents.title, '1'
        FROM Documents
        LEFT JOIN DocumentFolders ON DocumentFolders.did=Documents.id
        WHERE (Documents.title LIKE ?) AND (DocumentFolders.folderid=7)
    UNION ALL
        SELECT DocumentKeywords.did, DocumentKeywords.text, '2'
        FROM DocumentKeywords
        WHERE DocumentKeywords.text LIKE ?
    ORDER BY did
    '''

    print(query)
    ret=cin.execute(query, ('%%%s%%' %text, '%%%s%%' %text))

    query='''SELECT * FROM temp.search_res'''
    ret=cin.execute(query)
    ret=ret.fetchall()
    for ii in ret:
        print(ii)

    return ret

def searchMultipleLike(db, text, field_dict, folderid):

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
    for kk,vv in field_dict.items():
        if not vv:
            continue
        if kk=='Authors':
            qkk='''SELECT did, ("firstNames" || " " || "lastName") as name, 'autors'
            FROM DocumentContributors
            WHERE name LIKE ?
            '''
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

        queries.append(qkk)

    query='''INSERT INTO temp.search_res (did, text, field)
    %s
    ''' %('UNION ALL\n'.join(queries))
    print(query)

    ret=cin.execute(query, (text,)*len(queries))

    #---------Get results and filter by folder---------
    if folderid=='-1':
        query='''SELECT * FROM search_res'''
        ret=cin.execute(query)

    elif folderid=='-2':
        query='''SELECT search_res.did, search_res.text, search_res.field
        FROM search_res
        LEFT JOIN Documents ON Documents.id=search_res.did
        WHERE Documents.confirmed='false'
        '''
        ret=cin.execute(query)

    elif folderid=='-3':
        query='''SELECT search_res.did, search_res.text, search_res.field
        FROM search_res
        LEFT JOIN Documents ON Documents.id=search_res.did
        WHERE Documents.deletionPending='true'
        '''
        ret=cin.execute(query)

    else:
        query='''SELECT search_res.did, search_res.text, search_res.field
        FROM search_res
        LEFT JOIN DocumentFolders ON DocumentFolders.did=search_res.did
        WHERE DocumentFolders.folderid=?'''
        ret=cin.execute(query, (folderid,))

    print(query)
    ret=ret.fetchall()
    for ii in ret:
        print(ii)

    return ret





if __name__=='__main__':

    dbfile='../new7_fts5.sqlite'
    dbfile='../nonfts.sqlite'

    db = sqlite3.connect(dbfile)
    #cin=db.cursor()

    #aa=searchTitle(db, 'sea')
    #aa=searchAuthors(db, 'Che')
    #aa=searchKeywords(db, 'ENSO')
    #aa=searchTags(db, 'ENSO')
    #aa=searchNotes(db, 'the')
    #aa=searchMultiple(db, 'ENSO')

    #aa=searchTitleLike(db, 'ffec')
    #aa=searchAuthorsLike(db, 'chi')
    #aa=searchKeywordsLike(db, 'tmos')
    #aa=searchTagsLike(db, 'tmos')
    #aa=searchNotesLike(db, 'he')
    field_dict={'Authors': True, 'Title': True, 'Keywords': True, 'Tag': True, \
            'Abstract': True}
    aa=searchMultipleLike(db, 'tmos', field_dict, '7')
