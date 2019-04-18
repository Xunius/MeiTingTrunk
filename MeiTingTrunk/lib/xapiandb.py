'''
PDF full text search using xapian.

MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

import os
from urllib.parse import unquote
from urllib.parse import urlparse
import json
import logging
from pprint import pprint
import subprocess
import xapian
import tempfile
import sqlite3

LOGGER=logging.getLogger(__name__)


# field name to xapian prefix mapping
FIELDS={
        #'authors_l'   : 'A',
        #'abstract'    : 'B',
        #'keywords_l'  : 'K',
        #'tags_l'      : 'XTAG',
        #'notes'        : 'XNOTE',
        #'title'       : 'S',
        #'publication' : 'XPUB',
        #'folders_l'   : 'XFD',
        #'confirmed'   : 'XCF',
        'pdf'         : 'XPDF',
        'id'          : 'XID'
        }


def createDatabase(dbpath):

    try:
        db=xapian.WritableDatabase(dbpath, xapian.DB_CREATE_OR_OPEN)
        return db
    except:
        return None


def indexFile(dbpath, abspath, relpath, meta_dict, db=None):
    '''Index a new file

    Args:
        dbpath (str): path to xapian database folder.
        abspath (str): abs path to file to index.
        relpath (str): relative (to lib_folder) path of file to index.
                       The relpath will be used as a part of the unique id of
                       a xapian doc.
        meta_dict (DocMeta): meta data dict for the doc.
        db (xapian database): return value of xapian.WritableDatabase().
                              Not sure this would give any speed boost.

    Returns:
        rec (int): 0 if indexed successfully, 1 otherwise.
    '''

    if not os.path.exists(abspath):
        return 1

    if db is None:
        db=xapian.WritableDatabase(dbpath, xapian.DB_CREATE_OR_OPEN)

    #LOGGER.debug('abspath = %s. relpath = %s' %(abspath, relpath))

    #--------------Create xapian document--------------
    doc=xapian.Document()
    term_generator=xapian.TermGenerator()
    term_generator.set_stemmer(xapian.Stem('en'))
    term_generator.set_document(doc)

    #with open(os.devnull, 'w') as devnull:
    #discard stderr
    #proc=subprocess.Popen(['pdftotext', abspath, '-'],
    proc=subprocess.Popen("pdftotext '%s' -" %abspath,
            bufsize=0,
            shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # NOTE: don't use proc.communicate(), which is slow af. Writing and
    # reading from a tmp file is no better

    lines=[]
    while True:
        line=proc.stdout.readline()
        if not line:
            break
        if len(line)>0:
            line=line.decode('utf-8')
            term_generator.index_text(line)
            lines.append(line)

    #--------------------Add fields--------------------
    fields={}

    def addBooleanTerm(key):
        value=meta_dict.get(key)
        if value is not None and len(str(value))>0:
            doc.add_boolean_term('%s%s' %(FIELDS[key], str(value)))
            fields[key]=value
        return

    # add doc id
    addBooleanTerm('id')

    # add unique id
    idterm='Q%s-%s' %(meta_dict['id'],relpath)
    doc.add_boolean_term(idterm)
    # save data for later use
    fields['qid']=idterm
    fields['rel_path']=relpath
    pdf='\n'.join(lines)
    fields['pdf']=pdf

    doc.set_data(json.dumps(fields))
    db.replace_document(idterm, doc)
    #LOGGER.debug('added qid = %s' %idterm)
    #print('# <addBooleanTerm>: qid=',idterm)

    return 0


def delXapianDoc(dbpath, qid):
    '''Delete a xapian doc by unique doc id

    Args:
        dbpath (str): path to xapian database folder.
        qid (str): unique doc id.

    Returns:
        rec (int): 0 if successful, 1 otherwise.
    '''

    try:
        db=xapian.WritableDatabase(dbpath, xapian.DB_OPEN)
        db.delete_document(qid)
        return 0
    except:
        return 1


def delByDocid(dbpath, docid):
    '''Delete xapian doc(s) by doc id

    Args:
        dbpath (str): path to xapian database folder.
        docid (int): doc id.

    Returns:
        rec (int): 0 if successful, 1 otherwise.
    '''

    qids=getByDocid(dbpath, docid)
    for idii in qids:
        delXapianDoc(dbpath, idii)

    return 0


def getByDocid(dbpath, docid):
    '''Get all xapian unique doc ids related to a given docid

    Args:
        dbpath (str): path to xapian database folder.
        docid (int): doc id.

    Returns:
        docs (list): list of unique doc ids in str.
    '''

    try:
        db=xapian.Database(dbpath)
    except:
        raise Exception("Failed to connect to xapian database.")

    #---------------Create query parser---------------
    query=xapian.Query('XID%s' %docid)

    #------------------Create Enquire------------------
    enquire=xapian.Enquire(db)
    enquire.set_query(query)

    doc_count=db.get_doccount()
    mset=enquire.get_mset(0, doc_count)
    docs=[]

    for mm in mset:
        match_fields=json.loads(mm.document.get_data())
        qid=match_fields['qid']
        docs.append(qid)

    return docs


def search(dbpath, querystring, fields, docids=None):
    '''Full text query within some docs

    Args:
        dbpath (str): path to xapian database folder.
        querystring (str): query string.
        fields (list): list of field names to query. Currently only ['pdf',]
                       is expected.
    Kwargs:
        docids (list or None): list of doc ids (note not unique xapian doc ids)
                               to filter the results. If None, no filtering.

    Returns:
        matches (dict): search results in the format of:
            {docid1: {'title': title_text,
                      'authors': authors_text,
                      'pdf': {relpath1: snippet1,
                              relpath2: snippet2, ...
                              }
                        ...}

            ...}
        Note that currently only 'pdf' field is relevant.
    '''

    try:
        db=xapian.Database(dbpath)
    except:
        raise Exception("Failed to connect to xapian database.")

    #---------------Create query parser---------------
    query_parser=xapian.QueryParser()
    query_parser.set_stemmer(xapian.Stem('en'))
    query_parser.set_stemming_strategy(query_parser.STEM_SOME)

    #----------------------Prefix----------------------
    for fii in fields:
        if fii=='publication':
            query_parser.add_boolean_prefix(fii, FIELDS[fii])
        else:
            query_parser.add_prefix(fii, FIELDS[fii])

    query=query_parser.parse_query(querystring)

    #----------------Add docid filter----------------
    LOGGER.debug('docids = %s' %docids)
    if docids is not None:
        docid_queries=[xapian.Query('XID%s' %str(ii)) for ii in docids]
        docid_query=xapian.Query(xapian.Query.OP_OR, docid_queries)
        query=xapian.Query(xapian.Query.OP_FILTER, query, docid_query)

    #------------------Create Enquire------------------
    enquire=xapian.Enquire(db)
    enquire.set_query(query)

    offset=0
    snip_size=400

    #-------------------Get matches-------------------
    doc_count=db.get_doccount()
    matches={}
    mset=enquire.get_mset(offset, doc_count)

    for mm in mset:
        match_fields=json.loads(mm.document.get_data())
        docid=match_fields['id']
        dictmm={}

        for kk in fields:
            vv=match_fields[kk]
            # get a snippet for each match
            snipkk=mset.snippet(vv, snip_size, xapian.Stem('en'),
                    xapian.MSet.SNIPPET_BACKGROUND_MODEL |
                    xapian.MSet.SNIPPET_EMPTY_WITHOUT_MATCH |
                    xapian.MSet.SNIPPET_EXHAUSTIVE,
                    '', '')
                    # do highlighting in qt
                    #'<span style=background-color:yellow><b>',
                    #'</b></span>')
            snipkk=snipkk.decode('utf-8','replace')

            if len(snipkk)>0:
                if kk=='pdf':
                    dictmm[kk]={match_fields['rel_path']: snipkk}
                else:
                    dictmm[kk]=snipkk

        #--------------combine results of the same doc--------------
        if docid not in matches:
            matches[docid]=dictmm
        else:
            if 'pdf' in fields:
                pdf1=matches[docid].get('pdf',{})
                pdf2=dictmm.get('pdf',{})
                pdf1.update(pdf2)
                matches[docid]['pdf']=pdf1


    return matches


def checkDatabase(dbpath, sqlitepath):

    db=xapian.Database(dbpath)
    enquire=xapian.Enquire(db)
    enquire.set_query(xapian.Query.MatchAll)

    doc_count=db.get_doccount()
    mset=enquire.get_mset(0, doc_count)

    for mm in mset:
        match_fields=json.loads(mm.document.get_data())
        docid=match_fields['id']
        qid=match_fields['qid']
        #print('# <checkDatabase>: docid=',docid,'qid=',qid)

    return


def indexFolder(dbpath, lib_folder):

    proc=subprocess.Popen(['omindex', '-d', 'replace', # replace duplicate
        '-e', 'skip', # documents without extracted text
        '-f',         # follow links
        '--db', dbpath,
        '--url', '/', lib_folder, '_collections'], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    rec=proc.communicate()

    print('# <indexFolder>: rec[0]=',rec[0])
    print('# <indexFolder>: rec[1]=',rec[1])

    return 0


def search2(xapianpath, sqlitepath, querystring, docids=None):

    try:
        db=xapian.Database(xapianpath)
    except:
        raise Exception("Failed to connect to xapian database.")

    try:
        sqlitedb=sqlite3.connect(sqlitepath, check_same_thread=False)
    except:
        raise Exception("Failed to connect to sqlite database.")

    #--------------Get path-docid mapping--------------
    query='''SELECT relpath, did FROM DocumentFiles'''
    ret=sqlitedb.execute(query)
    idmap=dict(ret.fetchall())

    #---------------Create query parser---------------
    query_parser=xapian.QueryParser()
    query_parser.set_stemmer(xapian.Stem('en'))
    query_parser.set_stemming_strategy(query_parser.STEM_SOME)
    query=query_parser.parse_query(querystring)

    #----------------Add docid filter----------------
    #LOGGER.debug('docids = %s' %docids)
    if docids is not None:
        filter_paths=['/%s' %kk for kk,vv in idmap.items() if vv in docids]
        docid_queries=[xapian.Query('U%s' %str(ii)) for ii in filter_paths]
        docid_query=xapian.Query(xapian.Query.OP_OR, docid_queries)
        query=xapian.Query(xapian.Query.OP_FILTER, query, docid_query)

    #------------------Create Enquire------------------
    enquire=xapian.Enquire(db)
    enquire.set_query(query)

    #-------------------Get matches-------------------
    offset=0
    doc_count=db.get_doccount()
    mset=enquire.get_mset(offset, doc_count)
    matches={}

    for mm in mset:
        dd=mm.document.get_data().decode('utf-8')
        dlist=dd.split('\n')
        url=dlist[0]
        url=converturl2abspath(url)[5:]
        docid=idmap[url]

        # save match. An awkward format.
        dictmm={'pdf': {url: url}}

        if docid not in matches:
            matches[docid]=dictmm
        else:
            pdf1=matches[docid].get('pdf',{})
            pdf2=dictmm.get('pdf',{})
            pdf1.update(pdf2)
            matches[docid]['pdf']=pdf1


    return matches


def converturl2abspath(url):
    '''Convert a url string to an absolute path
    '''

    path = unquote(str(urlparse(url).path))
    return path



if __name__=='__main__':

    #dbpath='/home/guangzhi/testdb/tt/'
    dbpath='/home/guangzhi/codes/pyrefman_deleted/men/_xapian_dbdd'

    #lib_folder='/home/guangzhi/testxap/'
    lib_folder='/home/guangzhi/codes/pyrefman_deleted/men/'
    sqlitepath='/home/guangzhi/codes/pyrefman_deleted/men.sqlite'

    aa=indexFolder(dbpath, lib_folder)
    #aa=search2(dbpath, 'atmosphere', list(range(0,200)) ,sqlitepath)

    print('# <search2>: aa=',aa)








    #dbpath='./xapian_db'

    #aa=checkDatabase(dbpath, None)

    #dbpath='/home/guangzhi/codes/pyrefman_deleted/men2/_xapian_db'
    #recii=indexFile(dbpath, '../samples/testpdf.pdf', 'testpdf.pdf',
            #{'id':0}, None)
    '''
    aa=search(dbpath, 'enso', ['pdf'], None)
    print(aa)

    '''
    '''
    dirname='/home/guangzhi/Documents/Mendeley Desktop'
    files=os.listdir(dirname)

    for ii,fii in enumerate(files):
        pii=os.path.join(dirname,fii)
        recii=indexFile(dbpath, pii, fii,  {'id':ii}, None)
        print('############### ii=',ii,'recii=',recii)
        if ii>=50:
            break
    '''


    '''
    relpath='samples/sample_pdf1.pdf'
    meta={'id': 100,
            'authors_l': ['f1, l1', 'firstname1, lastname2', 'firstname3, lastname3'],
            'title': 'this is dummy title titles titless on atmosphere',
            'keywords_l': ['key1', 'key2', 'key3'],
            'tags_l': [],
            'folders_l': [('0', 'Default')],
            'publication': 'Nature',
            'abstract': 'this is a dummy abstract',
            'notes': 'this is a note',
            'confirmed': 'true',
            'files_l': ['somefile', relpath]
            }


    lib_folder='../'

    aa=indexFile(dbpath, '../%s' %relpath, relpath, meta)
    print('aa=',aa)

    relpath='samples/sample_pdf2.pdf'
    meta={'id': 101,
            'authors_l': ['firstname1, lastname1', 'f2, l2', 'f3, lastname3'],
            'title': 'this is serious title ',
            'keywords_l': ['key1', 'key2', 'key7'],
            'tags_l': [],
            'folders_l': [('0', 'Default'), ('2', 'NewFolder')],
            'publication': 'Nature',
            'abstract': 'this is a serious abstract on atmospheric',
            'notes': 'this is a note',
            'confirmed': 'false',
            'files_l': [relpath]
            }


    aa=indexFile(dbpath, '../%s' %relpath, relpath, meta)
    print('aa=',aa)


    relpath1='samples/sample_pdf3.pdf'
    relpath2='samples/sample_pdf2.pdf'
    meta={'id': 103,
            'authors_l': ['firstname2, lastname2', 'f3, l2', 'f3, lastname3'],
            'title': 'this is serious title again tile ',
            'keywords_l': ['key1', 'key4', 'key9'],
            'tags_l': [],
            'folders_l': [('3', 'ENSO'), ('2', 'NewFolder')],
            'publication': 'Science',
            'abstract': 'this is a seriously dummy abstract, atmospheres',
            'notes': 'this is a note',
            'confirmed': 'true',
            'files_l': [relpath1, relpath2]
            }


    aa=indexFile(dbpath, '../%s' %relpath1, relpath1, meta)
    aa=indexFile(dbpath, '../%s' %relpath2, relpath2, meta)
    print('aa=',aa)
    '''


    #aa=delXapianDoc(dbpath, 'samples/sample_pdf3.pdf', 103)
    #print('aa=',aa)
    '''
    aa=search(dbpath, 'atmosphere', ['title', 'authors_l', 'keywords_l',
        'tags_l', 'publication', 'notes', 'pdf'],
        '-2',
        pagesize=10)

    pprint(aa)
    '''


    #aa=getByDocid(dbpath, 101)


