import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser import customization as bibcus
try:
    from . import sqlitedb
except:
    import sqlitedb
from pprint import pprint
import os
import re

ALT_KEYS={
        'keyword': 'keywords_l',
        'tag': 'tags_l',
        'url': 'urls_l',
        'file': 'files_l',
        'folder': 'folders_l'
        }


def splitFields(record, key, sep=',|;'):
    """
    Split keyword field into a list.

    :param record: the record.
    :type record: dict
    :param sep: pattern used for the splitting regexp.
    :type record: string, optional
    :returns: dict -- the modified record.

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

    :param record: a record
    :returns: -- customized record
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
    record = splitFields(record, 'url')
    record = getPublication(record)
    return record

def splitNames(entry):

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

    bibfile=os.path.abspath(bibfile)
    if not os.path.exists(bibfile):
        return None

    with open(bibfile,'r') as fin:
        parser=BibTexParser()
        parser.homogenize_fields=True
        parser.customization=customizations
        bib=bibtexparser.load(fin,parser=parser)

    results=[]

    for eii in bib.entries:
        eii=splitNames(eii)
        eii=altKeys(eii,ALT_KEYS)

        eii['citationkey']=eii['ID']
        del eii['citationkey']

        # WARNING: temporary removing folders_l, as this is not supposed to
        # be in a native bib entry
        if 'folders_l' in eii:
            del eii['folders_l']

        docii=sqlitedb.DocMeta()
        docii.update(eii)
        results.append(docii)

    return results

if __name__=='__main__':
    aa=readBibFile('test.bib')
    pprint(aa[-1])

