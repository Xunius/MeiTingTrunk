import sqlite3

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


def searchMultiple(db, text, field_dict, folderid):

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
    for kk,vv in field_dict.items():
        if not vv:
            continue
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



if __name__=='__main__':

    dbfile='../new7.sqlite'

    db = sqlite3.connect(dbfile)
    #cin=db.cursor()

    #aa=searchTitle(db, 'effect')
    #aa=searchAuthors(db, 'Che')
    #aa=searchKeywords(db, 'ENSO')
    #aa=searchTags(db, 'ENSO')
    #aa=searchNotes(db, 'the')
    aa=searchMultiple(db, 'ENSO')

