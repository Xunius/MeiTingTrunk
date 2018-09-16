'''Test manipulating sqlite datafile


'''


import os
import sys
import sqlite3
import re
import bibtexparser


FILE_IN='mendeley.sqlite'
BIB_IN='test.bib'

BEGIN_PATTERN=re.compile(r'^@(.*?){(.*?),', re.DOTALL)
END_PATTERN=re.compile(r'^}\s*$')
AUTHOR_PATTERN=re.compile(r'^\s*author\s*=\s*{?(.*?)}?,', re.MULTILINE | re.DOTALL)
TITLE_PATTERN=re.compile(r'^\s*title\s*=\s*{?(.*?)}?,', re.MULTILINE | re.DOTALL)

ENTRY_PATTERN=re.compile(r'^\s*(.*?)\s*=\s*(?P<quote>{|")(.*?)\s*(?P=quote)',
        re.MULTILINE | re.DOTALL)




def deu(text):
    if isinstance(text,str):
        return text.decode('utf8','replace')
    else:
        return text

def enu(text):
    if isinstance(text,unicode):
        return text.encode('utf8','replace')
    else:
        return text


DOC_ATTRS=[\
'uuid', 'issn', 'issue', 'language', 'read', 'type', 'confirmed',
'deduplicated', 'deletionPending', 'favourite', 'importer', 'note',
'abstract', 'added', 'modified', 'advisor', 'articleColumn',
'applicationNumber', 'arxivId', 'privacy', 'title', 'pmid',
'publication', 'publicLawNumber', 'month', 'originalPublication',
'owner', 'pages', 'sections', 'seriesEditor', 'series', 'seriesNumber',
'publisher', 'reprintEdition', 'reviewedArticle', 'revisionNumber',
'userType', 'volume', 'year', 'session', 'shortTitle', 'sourceType',
'code', 'codeNumber', 'codeSection', 'codeVolume', 'chapter',
'citationKey', 'city', 'day', 'department', 'doi', 'edition',
'committee', 'counsel', 'country', 'dateAccessed',
'internationalAuthor', 'internationalNumber', 'internationalTitle',
'internationalUserType', 'genre', 'hideFromMendeleyWebIndex',
'institution', 'lastUpdate', 'legalStatus', 'length', 'medium', 'isbn']


import uuid

def insertEntry(entry,db):
    columns=DOC_ATTRS
    places=','.join('?'*len(columns))
    values=[]
    for kii in columns:
        if kii=='uuid':
            randid=uuid.uuid4().__str__()
            values.append(randid)
        else:
            values.append(entry.get(kii,None))
    values=tuple(values)

    #values=tuple(entry.get(kii,None) for kii in columns)
    __import__('pdb').set_trace()

    query='''\
INSERT INTO Documents (%s) VALUES (%s)
''' %(','.join(columns), places)
    cur=db.cursor()
    ret=cur.execute(query, values)
    print 'values'
    print values
    db.commit()

    return ret




if __name__=='__main__':

    dbfin=os.path.abspath(FILE_IN)

    try:
        db = sqlite3.connect(dbfin)
        print('Connected to database:')
    except:
        print('Failed to connect to database:')

    # read bib
    with open(BIB_IN,'r') as fin:
        bb=bibtexparser.load(fin)

    entries=bb.entries

    #query='''SELECT * FROM Documents'''
    #cur=db.execute(query)
    #columns=[des[0] for des in cur.description]
    #print columns

    aa=insertEntry(entries[0],db)







