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
import json
import logging
from pprint import pprint
import subprocess
import tempfile
import xapian


LOGGER=logging.getLogger(__name__)


FIELDS={'authors_l'   : 'A',
        'abstract'    : 'B',
        'keywords_l'  : 'K',
        'tags_l'      : 'XTAG',
        'note'        : 'XNOTE',
        'title'       : 'S',
        'publication' : 'XPUB',
        'pdf'         : 'XPDF'
        }

def hasPdftotext():

    proc=subprocess.Popen(['which','pdftotext'], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    rec=proc.communicate()
    if len(rec[0])==0 and len(rec[1])>0:
        return False
    return True


def indexFile(dbpath, relpath, meta_dict, lib_folder):

    if not hasPdftotext():
        return 1

    if os.path.isabs(relpath):
        filepath=relpath
    else:
        filepath=os.path.join(lib_folder, relpath)

    if not os.path.exists(filepath):
        return 1

    try:
        db=xapian.WritableDatabase(dbpath, xapian.DB_CREATE_OR_OPEN)
    except:
        return 1

    print('# <indexFile>: relpath=',relpath)
    print('# <indexFile>: filepath=',filepath)

    proc=subprocess.Popen(['pdftotext', filepath, '-'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    stdout, stderr=proc.communicate()
    if len(stdout)==0 and len(stderr)>0:
        return 1

    file_idx=meta_dict['files_l'].index(relpath)
    print('# <indexFile>: file_idx=',file_idx)

    #--------------Create xapian document--------------
    doc=xapian.Document()
    term_generator=xapian.TermGenerator()
    term_generator.set_stemmer(xapian.Stem('en'))
    term_generator.set_document(doc)

    #--------------------Add fields--------------------
    fields={}

    for fii,prefixii in FIELDS.items():

        if fii=='publication':
            continue
        if fii=='pdf':
            valueii=stdout.decode('utf-8','replace')
        elif fii.endswith('_l'):
            valueii='; '.join(meta_dict[fii])
        else:
            valueii=str(meta_dict[fii])

        fields[fii]=valueii

        # add prefix
        term_generator.index_text(valueii, 1, prefixii)
        term_generator.index_text(valueii)
        term_generator.increase_termpos()

    # add publication
    pub=meta_dict['publication']
    doc.add_boolean_term('%s%s' %(FIELDS['publication'], pub))

    idterm='Q%s-%s' %(meta_dict['id'],file_idx)
    fields['docid']=meta_dict['id']
    print('# <indexFile>: fii=',fii,'prefixii=',prefixii,'id=',idterm)

    doc.set_data(json.dumps(fields))
    doc.add_boolean_term(idterm)
    db.replace_document(idterm, doc)

    return 0





def delXapianDoc(dbpath, relpath, meta_dict):

    try:
        db=xapian.WritableDatabase(dbpath, xapian.DB_OPEN)
    except:
        return 1

    if relpath not in meta_dict['files_l']:
        raise Exception("file not in dict")

    file_idx=meta_dict['files_l'].index(relpath)
    doc_idx=meta_dict['id']
    idterm='Q%s-%s' %(doc_idx, file_idx)

    print('# <indexFile>: doc_idx=',doc_idx, 'file_idx=',file_idx,'idterm=',idterm)

    db.delete_document(idterm)

    return 0


def search(dbpath, querystring, fields, pagesize=10):

    try:
        db=xapian.Database(dbpath)
    except:
        return 1, None

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

    #------------------Create Enquire------------------
    enquire=xapian.Enquire(db)
    enquire.set_query(query)

    offset=0
    snip_size=400

    #-------------------Get matches-------------------
    doc_count=db.get_doccount()
    print('# <search>: doc_count=',doc_count)
    matches={}
    __import__('pdb').set_trace()

    mset=enquire.get_mset(offset, pagesize)

    for mm in mset:
        match_fields=json.loads(mm.document.get_data())

        #print('# <search>: match_fields',match_fields)
        docid=match_fields['docid']
        dictmm={}

        for kk,vv in match_fields.items():
            if kk=='docid':
                continue
            snipkk=mset.snippet(vv, snip_size, xapian.Stem('en'),
                    xapian.MSet.SNIPPET_BACKGROUND_MODEL |
                    xapian.MSet.SNIPPET_EMPTY_WITHOUT_MATCH |
                    xapian.MSet.SNIPPET_EXHAUSTIVE)
            snipkk=snipkk.decode('utf-8','replace')

            if len(snipkk)>0:
                dictmm[kk]=snipkk

        if docid not in matches:
            matches[docid]=dictmm
        else:
            # need to combine 2 docs
            pass

        #matches.append(match_fields['docid'])

    return matches






if __name__=='__main__':

    relpath='samples/sample_pdf1.pdf'
    meta={'id': 100,
            'authors_l': ['f1, l1', 'firstname1, lastname2', 'firstname3, lastname3'],
            'title': 'this is dummy title titles titless',
            'keywords_l': ['key1', 'key2', 'key3'],
            'tags_l': [],
            'publication': 'Nature',
            'abstract': 'this is a dummy abstract',
            'note': 'this is a note',
            'files_l': ['somefile', relpath]
            }

    dbpath='./xapian_db'

    lib_folder='../'

    #aa=indexFile(dbpath, relpath, meta, lib_folder)
    #print('aa=',aa)

    relpath='samples/sample_pdf2.pdf'
    meta={'id': 101,
            'authors_l': ['firstname1, lastname1', 'f2, l2', 'f3, lastname3'],
            'title': 'this is serious title ',
            'keywords_l': ['key1', 'key2', 'key7'],
            'tags_l': [],
            'publication': 'Nature',
            'abstract': 'this is a serious abstract',
            'note': 'this is a note',
            'files_l': [relpath]
            }


    #aa=indexFile(dbpath, relpath, meta, lib_folder)
    #print('aa=',aa)


    relpath='samples/sample_pdf3.pdf'
    meta={'id': 103,
            'authors_l': ['firstname2, lastname2', 'f3, l2', 'f3, lastname3'],
            'title': 'this is serious title again tile ',
            'keywords_l': ['key1', 'key4', 'key9'],
            'tags_l': [],
            'publication': 'Science',
            'abstract': 'this is a seriously dummy abstract',
            'note': 'this is a note',
            'files_l': [relpath]
            }


    #aa=indexFile(dbpath, relpath, meta, lib_folder)
    #print('aa=',aa)

    #aa=delXapianDoc(dbpath, relpath, meta)
    #print('aa=',aa)
    aa=search(dbpath, 'atmosphere', ['title', 'authors_l', 'keywords_l',
        'tags_l', 'publication', 'note', 'pdf'],
        pagesize=10)

    pprint(aa)


