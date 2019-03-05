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

INV_ALT_KEYS=dict([(vv,kk) for kk,vv in ALT_KEYS.items()])

OMIT_KEYS=[
        'read', 'favourite', 'added', 'confirmed', 'firstNames_l',
        'lastName_l', 'pend_delete', 'folders_l', 'type', 'id'
        ]

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
    record = splitFields(record, 'url', '\n')
    record = splitFields(record, 'file', ',|;|\n')
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
        #del eii['citationkey']

        # WARNING: temporary removing folders_l, as this is not supposed to
        # be in a native bib entry
        if 'folders_l' in eii:
            del eii['folders_l']

        # WARNING TEMP solution
        #eii['urls_l']=[eii['urls_l'],]

        docii=sqlitedb.DocMeta()
        docii.update(eii)
        results.append(docii)

    return results



def toOrdinaryDict(metadict,alt_dict,omit_keys):

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
                print('# <toOrdinaryDict>: kk=',kk,'vv=',vv)
                if kk in ['folders_l',]:
                    vv=[vii[1] for vii in vv]
                vv='; '.join(vv)
            result[alt_dict[kk]]=vv
        else:
            result[kk]=str(vv)

    authors=parseAuthors(metadict['authors_l'])[2]
    authors=' and '.join(authors)
    result['author']=authors

    doctype=metadict['type']
    if doctype is None or doctype.lower()=='journalarticle':
        doctype='article'
    result['ENTRYTYPE']=doctype

    result['ID']=metadict['citationkey'].replace('(','').replace(')','')

    return result


def metaDictToBib(jobid,metadict,omit_keys):

    try:
        alt_dict=INV_ALT_KEYS
        ord_dict=toOrdinaryDict(metadict,alt_dict,omit_keys)

        db=BibDatabase()
        db.entries=[ord_dict,]
        writer=BibTexWriter()
        writer.indent='    '
        writer.comma_first=False

        dbtext=writer.write(db)

        return 0,jobid,dbtext,metadict['id']
    except:
        return 1,jobid,'',metadict['id']




if __name__=='__main__':
    aa=readBibFile('test.bib')
    pprint(aa[-1])


    # test export

    entries=[]
    for eii in aa:
        dii=toOrdinaryDict(eii,INV_ALT_KEYS,OMIT_KEYS)
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

