'''
Full text search using xapian, xapian-omega and the python binding of xapian.

MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

import os
from urllib.parse import unquote, quote
from urllib.parse import urlparse
import json
import logging
import subprocess
import xapian
import sqlite3
import multiprocessing

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

#######################################################################
#                          General functions                          #
#######################################################################

def converturl2abspath(url):
    '''Convert a url string to an absolute path
    '''

    path = unquote(str(urlparse(url).path))
    return path


def createDatabase(dbpath):

    try:
        db=xapian.WritableDatabase(dbpath, xapian.DB_CREATE_OR_OPEN)
        return db
    except:
        return None


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



#######################################################################
#                           Use xapian only                           #
#######################################################################


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

    NOTE: this function expects a pdf file and calls 'pdftotext' to convert
    it to plain texts, then index it to a given xapian database. It allows
    adding custom metadata to the xapian doc, but it is too slow.
    '''

    if not os.path.exists(abspath):
        return 1

    if db is None:
        db=xapian.WritableDatabase(dbpath, xapian.DB_CREATE_OR_OPEN)

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
    NOTE that this works on database indexed using indexFile().
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


class Worker(multiprocessing.Process):
    def __init__(self, id, func, jobq, outq):
        super(Worker,self).__init__()
        self.id=id
        self.func=func
        self.jobq=jobq
        self.outq=outq

    def run(self):
        while True:
            args=self.jobq.get()
            self.jobq.task_done()
            if args is None:
                self.outq.put(None)
                break
            res=self.func(*args)
            self.outq.put(res)

        return


def convertPDF(abspath, relpath, meta_dict):
    '''Call pdftotext to convert a pdf file

    Args:
        abspath (str): abs path to file to index.
        relpath (str): relative (to lib_folder) path of file to index.
                       The relpath will be used as a part of the unique id of
                       a xapian doc.
        meta_dict (DocMeta): meta data dict for the doc.

    Returns:
        rec (int): 0 if indexed successfully, 1 otherwise.
    '''

    if not os.path.exists(abspath):
        return 1

    #with open(os.devnull, 'w') as devnull:
    #discard stderr
    #proc=subprocess.Popen(['pdftotext', abspath, '-'],
    proc=subprocess.Popen("pdftotext '%s' -" %abspath,
            bufsize=0,
            shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    lines=[]
    while True:
        line=proc.stdout.readline()
        if not line:
            break
        if len(line)>0:
            line=line.decode('utf-8')
            lines.append(line)

    return relpath, meta_dict, lines


def writeToXapian(dbpath, jobq):
    '''Update to xapian database

    Args:
        dbpath (str): path to xapian database folder.
        jobq (multiprocessing.Queue): queue sending in jobs.
    Returns:
        rec (int): 0 if indexed successfully, 1 otherwise.

    convertPDF() and writeToXapian() are my attempts to speed up the indexing
    process. Using indexFile() is too slow. Using this consumer-provider
    does gain speed, but i still have to handle formats other than PDFs.
    Omega is still more appealing in that regard.
    '''

    db=xapian.WritableDatabase(dbpath, xapian.DB_CREATE_OR_OPEN)

    results=[]
    while True:
        args=jobq.get()
        if args is None:
            break

        relpath, meta_dict, lines=args

        #--------------Create xapian document--------------
        doc=xapian.Document()
        term_generator=xapian.TermGenerator()
        term_generator.set_stemmer(xapian.Stem('en'))
        term_generator.set_document(doc)

        lines='\n'.join(lines)
        term_generator.index_text(lines)

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
        pdf=lines
        fields['pdf']=pdf

        doc.set_data(json.dumps(fields))
        db.replace_document(idterm, doc)

        results.append(0)

    return results


#######################################################################
#                           Use xapian-omega                           #
#######################################################################

class OmindexWorker(multiprocessing.Process):
    def __init__(self, dbpath, lib_folder):
        super(Worker,self).__init__()
        self.func=indexFolder
        self.dbpath=dbpath
        self.lib_folder=lib_folder

    def run(self):
        while True:
            args=self.jobq.get()
            self.jobq.task_done()
            if args is None:
                self.outq.put(None)
                break
            res=self.func(*args)
            self.outq.put(res)

        return


def indexFolder(dbpath, lib_folder):
    '''Use omindex to index a folder

    Args:
        dbpath (str): path to the xapian database.
        lib_folder (str): path to the MTT library folder.

    Returns:
        rec (int): 0 if successful, 1 otherwise.
    '''

    try:
        proc=subprocess.Popen(['omindex', '-d', 'replace', # replace duplicate
            '-e', 'skip', # documents without extracted text
            '-f',         # follow links
            '--db', dbpath,
            '--url', '/', lib_folder, '_collections'], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        rec=proc.communicate()
        if len(rec[0])>0:
            LOGGER.debug('stdout = %s' %rec[0])
        if len(rec[1])>0:
            LOGGER.debug('stderr = %s' %rec[1])
        return 0
    except:
        LOGGER.exception('Failed to call omindex')
        return 1


def search2(xapianpath, sqlitepath, querystring, docids=None):
    '''Full text query within some docs

    Args:
        xapianpath (str): path to xapian database folder.
        sqlitepath (str): path to sqlite database folder.
        querystring (str): query string.
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
    NOTE that this works on database indexed using indexFolder().
    '''

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
    if docids is not None:
        # get relpath(s) from docid
        filter_paths=[quote('/%s' %kk) for kk,vv in idmap.items() if vv in docids]
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

        #-------------------Get snippet-------------------
        # NOTE this only works if the omindex source has been modified to save
        # the 'dump' as document data. To make the change, one needs to add
        # these lines to the index_file.cc:
        #
        #        if (dump.empty()) {
        #            record = "dump=";
        #        } else {
        #            record += "\ndump=";
        #            record += dump;
        #        }
        #
        # before the line:
        #
        #        newdocument.set_data(record);
        #
        # then re-compile xapian-omega.
        # . This is tricker than allowing the
        # user to use package managers to install xapian. Plus, their snippet()
        # function seems to only give 1 snippet at most. Probably not worth
        # doing snippet in that case.

        # find dump field
        ii=1
        while True:
            if ii>=len(dlist):
                break
            lii=dlist[ii]
            if lii[:5]=='dump=':
                break
            else:
                ii+=1

        #---------------------Has dump---------------------
        if ii<len(dlist):
            dump=' '.join(dlist[ii:])
            snip_size=400
            if len(dump)>0:
                snips=getSnippets(mset, dump[5:], snip_size)
            else:
                snips=[]
            dictmm={'pdf': {url: snips}}
        #---------------------No dump---------------------
        else:
            dictmm={'pdf': {url: os.path.split(url)[1]}}

        if docid not in matches:
            matches[docid]=dictmm
        else:
            pdf1=matches[docid].get('pdf',{})
            pdf2=dictmm.get('pdf',{})
            pdf1.update(pdf2)
            matches[docid]['pdf']=pdf1


    return matches


def getByDocid2(dbpath, sqlitepath, docid):
    '''Get all xapian unique doc ids related to a given docid

    Args:
        dbpath (str): path to xapian database folder.
        sqlitepath (str): path to sqlite database folder.
        docid (int): doc id.

    Returns:
        docs (list): list of unique doc ids in str.
    '''

    try:
        db=xapian.Database(dbpath)
    except:
        raise Exception("Failed to connect to xapian database.")

    try:
        sqlitedb=sqlite3.connect(sqlitepath, check_same_thread=False)
    except:
        raise Exception("Failed to connect to sqlite database.")

    #--------------Get relpaths of docid--------------
    query='''SELECT relpath FROM DocumentFiles
    WHERE (DocumentFiles.did=?)'''
    ret=sqlitedb.execute(query,(docid,))
    filter_paths=[]
    for uii in ret.fetchall():
        # add / at the begining, and quote
        filter_paths.append('/%s' %quote(uii[0]))

    #------------------Create Enquire------------------
    docid_queries=[xapian.Query('U%s' %ii) for ii in filter_paths]
    query=xapian.Query(xapian.Query.OP_OR, docid_queries)
    enquire=xapian.Enquire(db)
    enquire.set_query(query)

    doc_count=db.get_doccount()
    mset=enquire.get_mset(0, doc_count)
    docs=[]

    for mm in mset:
        docs.append(mm.docid)

    return docs


def delByDocid2(dbpath, sqlitepath, docid):
    '''Delete xapian doc(s) by doc id

    Args:
        dbpath (str): path to xapian database folder.
        sqlitepath (str): path to sqlite database folder.
        docid (int): doc id.

    Returns:
        rec (int): 0 if successful, 1 otherwise.
    '''

    qids=getByDocid2(dbpath, sqlitepath, docid)
    for idii in qids:
        delXapianDoc(dbpath, idii)

    return 0


def getSnippets(mset, text, snip_size):

    block_size=snip_size+200  # this seems to require a number > snip_size
    snippets=[]
    idx1=0
    while True:
        if idx1>=len(text):
            break

        idx2=idx1+block_size
        snip=mset.snippet(text[idx1:idx2], snip_size, xapian.Stem('en'),
                xapian.MSet.SNIPPET_BACKGROUND_MODEL |
                xapian.MSet.SNIPPET_EMPTY_WITHOUT_MATCH |
                xapian.MSet.SNIPPET_EXHAUSTIVE,
                '', '', '...')
                # do highlighting in qt
        if len(snip)>0:
            snip=snip.decode('utf-8','replace')
            snippets.append(snip)

        idx1+=block_size

    return snippets


if __name__=='__main__':

    #dbpath='/home/guangzhi/testdb/tt/'
    dbpath='/home/guangzhi/codes/pyrefman_deleted/men/_xapian_db'

    #lib_folder='/home/guangzhi/testxap/'
    lib_folder='/home/guangzhi/codes/pyrefman_deleted/men/'
    sqlitepath='/home/guangzhi/codes/pyrefman_deleted/men.sqlite'

    #aa=indexFolder(dbpath, lib_folder)
    #aa=search2(dbpath, sqlitepath, 'atmosphere', list(range(0,200)))

    #bb=getByDocid2(dbpath, sqlitepath, 1008)
    pp=multiprocessing.Process(target=indexFolder, args=(dbpath,lib_folder))
    pp.start()

    '''
    jobq=multiprocessing.JoinableQueue()
    outq=multiprocessing.Queue()

    def func(arg):
        print(arg)
    #worker=Worker(0, func, jobq, outq)
    worker=Worker(0, indexFolder, jobq, outq)
    worker.daemon=False
    worker.start()

    import time

    for ii in range(15):
        time.sleep(1)
        print(ii)

        if ii==5:
            jobq.put((dbpath, lib_folder))
            #jobq.put(('aaa',))
            jobq.put(None)

        if ii==10:
            #jobq.put(('aaa',))
            jobq.put((dbpath, lib_folder))
            jobq.put(None)

    '''



    """
    dbpath='./xapian_db'

    #aa=checkDatabase(dbpath, None)

    #dbpath='/home/guangzhi/codes/pyrefman_deleted/men2/_xapian_db'
    #recii=indexFile(dbpath, '../samples/testpdf.pdf', 'testpdf.pdf',
            #{'id':0}, None)
    '''
    aa=search(dbpath, 'enso', ['pdf'], None)
    print(aa)

    '''
    jobq=multiprocessing.JoinableQueue()
    outq=multiprocessing.Queue()

    workers=[]
    for ii in range(4):
        wii=Worker(ii,convertPDF,jobq,outq)
        workers.append(wii)
        wii.daemon=True
        wii.start()

    dirname='/home/guangzhi/Documents/Mendeley Desktop'
    files=os.listdir(dirname)

    for ii,fii in enumerate(files):
        pii=os.path.join(dirname,fii)
        #recii=indexFile(dbpath, pii, fii,  {'id':ii}, None)
        #print('############### ii=',ii,'recii=',recii)
        jobq.put((pii, fii, {'id':ii}))
        if ii>=300:
            for jj in range(len(workers)):
                jobq.put(None)
            break

    #outq2=multiprocessing.Queue()
    #writer=Worker(10, writeToXapian, outq, outq2)
    #writer.start()
    #pp=multiprocessing.Process(target=writeToXapian, args=(dbpath,outq))
    #pp.start()
    aa=writeToXapian(dbpath, outq)
    """


