'''
Parse bibtex files into dict format, and export DocMeta dict to bibtex file.


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

import os
import re
import logging
from pprint import pprint
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser import customization as bibcus
try:
    from . import sqlitedb
except:
    import sqlitedb
try:
    from .tools import parseAuthors
except:
    from tools import parseAuthors

# replace dict keys
ALT_KEYS={
        'keyword': 'keywords_l',
        'tag': 'tags_l',
        'url': 'urls_l',
        'file': 'files_l',
        'folder': 'folders_l'
        }

INV_ALT_KEYS=dict([(vv,kk) for kk,vv in ALT_KEYS.items()])

# for testing only
OMIT_KEYS=[
        'read', 'favourite', 'added', 'confirmed', 'firstNames_l',
        'lastName_l', 'deletionPending', 'folders_l', 'type', 'id'
        ]

LOGGER=logging.getLogger(__name__)



def splitFields(record, key, sep=',|;'):
    """Split keyword field into a list

    Args:
        record (dict): record dict.
        key (str): key in record dict to split its value.

    Kwargs:
        sep (str): pattern used for the splitting regexp.

    Returns: record (dict): the modified record

    """
    if key in record:
        record[key] = [i.strip() for i in re.split(sep, record[key].replace('\n', ''))]

    return record


def getPublication(record):
    '''Use journal field and publication

    maybe just for ARTICLE type??
    '''
    if 'journal' in record and 'publication' not in record:
        record['publication']=record['journal']

    return record


def customizations(record):
    """Use some functions delivered by the library

    Args:
        record (dict): record dict.

    Returns: record (dict): the modified record
    """
    record = bibcus.type(record)
    record = bibcus.author(record)
    #record = bibcus.editor(record)
    #record = bibcus.journal(record)
    record = bibcus.keyword(record)
    #record = bibcus.link(record)
    record = bibcus.page_double_hyphen(record)
    #record = bibcus.doi(record)
    record = splitFields(record, 'folder')
    record = splitFields(record, 'url', '\n')
    record = splitFields(record, 'file', ',|;|\n')
    record = getPublication(record)
    return record


def splitNames(entry):
    """Split authors list into a list of firstnames and a list of lastnames

    Args:
        entry (dict): meta data dict.

    Returns: entry (dict): meta data dict with a new 'firstNames_l' and
                           'lastName_l' key
    """

    firstnames=[]
    lastnames=[]
    for nii in entry['author']:
        lii,fii=nii.split(',',1)
        firstnames.append(fii.strip())
        lastnames.append(lii.strip())

    entry['firstNames_l']=firstnames
    entry['lastName_l']=lastnames

    return entry


def altKeys(entry_dict, alt_dict):

    for kk in alt_dict.keys():
        if kk in entry_dict:
            entry_dict[alt_dict[kk]]=entry_dict[kk]
            del entry_dict[kk]

    return entry_dict


def readBibFile(bibfile):
    """Read and parse bibtex file.

    Args:
        bibfile (str): abspath to input bibtex file.

    Returns: results (list): DocMeta dicts, each for an parsed entry in the
                             bibtex file.
    """

    bibfile=os.path.abspath(bibfile)
    if not os.path.exists(bibfile):
        return None

    with open(bibfile,'r') as fin:
        parser=BibTexParser()
        parser.homogenize_fields=True
        parser.customization=customizations
        bib=bibtexparser.load(fin,parser=parser)

        LOGGER.info('Read in bib file: %s' %bibfile)

    results=[]

    for eii in bib.entries:
        eii=splitNames(eii)
        eii=altKeys(eii,ALT_KEYS)
        eii['citationkey']=eii['ID']

        if 'folders_l' in eii:
            del eii['folders_l']

        docii=sqlitedb.DocMeta()
        docii.update(eii)
        results.append(docii)

    return results


def toOrdinaryDict(metadict, alt_dict, omit_keys, path_prefix):
    """Convert a DocMeta dict to an ordinary dict for bibtex export

    Args:
        metadict (DocMeta): meta dict of a doc.
        alt_dict (dict): dict for key changes.
        omit_keys (list): keys to omit in the converted dict.
        path_prefix (str): folder path to prepend to attachment file paths.

    Returns: result (dict): standard python dict containing meta data copied
                            from input <metadict> with a format suitable
                            for bibtex export.
    """

    result={}

    for kk,vv in metadict.items():
        if kk in omit_keys:
            continue

        if vv is None:
            continue

        if kk in alt_dict:
            if isinstance(vv,(tuple,list)):
                if len(vv)==0:
                    continue
                if kk in ['folders_l',]:
                    vv=[vii[1] for vii in vv]
                if kk == 'files_l':
                    vv=[os.path.join(path_prefix,vii) for vii in vv]
                vv='; '.join(vv)
            result[alt_dict[kk]]=vv
        else:
            result[kk]=str(vv)

        #LOGGER.debug('key = %s, value = %s' %(str(kk), str(vv)))

    authors=parseAuthors(metadict['authors_l'])[2]
    authors=' and '.join(authors)
    result['author']=authors

    doctype=metadict['type']
    if doctype is None or doctype.lower()=='journalarticle':
        doctype='article'
    result['ENTRYTYPE']=doctype

    ID=metadict['citationkey'].replace('(','').replace(')','')
    result['ID']=ID

    #LOGGER.debug('authors = %s' %authors)
    #LOGGER.debug('ENTRYTYPE = %s' %doctype)
    #LOGGER.debug('ID = %s' %ID)

    return result


def metaDictToBib(jobid, metadict, omit_keys, path_prefix):
    """Export meta data to bibtex format

    Args:
        jobid (int): id of job.
        metadict (DocMeta): meta dict of a doc.
        alt_dict (dict): dict for key changes.
        omit_keys (list): keys to omit in the converted dict.
        path_prefix (str): folder path to prepend to attachment file paths.

    Returns:
        rec (int): 0 if successful, 1 otherwise.
        jobid (int): the input jobid as it is.
        dbtext (str): formated bibtex entry, '' if <rec>==1.
        docid (int): id of the processed document.
    """

    try:
        alt_dict=INV_ALT_KEYS
        ord_dict=toOrdinaryDict(metadict,alt_dict,omit_keys,path_prefix)

        db=BibDatabase()
        db.entries=[ord_dict,]
        writer=BibTexWriter()
        writer.indent='    '
        writer.comma_first=False
        dbtext=writer.write(db)

        return 0,jobid,dbtext,metadict['id']

    except Exception:
        LOGGER.exception('Failed to write to bibtex')
        return 1,jobid,'',metadict['id']




if __name__=='__main__':
    aa=readBibFile('test.bib')
    pprint(aa[-1])


    # test export

    entries=[]
    for eii in aa:
        dii=toOrdinaryDict(eii,INV_ALT_KEYS,OMIT_KEYS,'/home/')
        entries.append(dii)

    db=BibDatabase()
    db.entries=entries
    writer=BibTexWriter()
    writer.indent='    '
    writer.comma_first=False

    with open('testexport.bib','w') as fout:
        dbtext=writer.write(db)
        print('dbtext',dbtext)
        fout.write(dbtext)

