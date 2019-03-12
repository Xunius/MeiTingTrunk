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
    __import__('pdb').set_trace()

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



if __name__=='__main__':

    dbfile='../new7_fts5.sqlite'

    db = sqlite3.connect(dbfile)
    #cin=db.cursor()

    aa=searchTitle(db, 'sea')
    #aa=searchAuthors(db, 'Che')
    #aa=searchKeywords(db, 'ENSO')
    #aa=searchTags(db, 'ENSO')
    #aa=searchNotes(db, 'the')
    #aa=searchMultiple(db, 'ENSO')

