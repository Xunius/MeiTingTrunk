import os
import re
from pprint import pprint
from RISparser import readris
from RISparser.config import LIST_TYPE_TAGS, TAG_KEY_MAPPING
try:
    from . import sqlitedb
except:
    import sqlitedb
try:
    from .tools import parseAuthors
except:
    from tools import parseAuthors

ALT_KEYS={
        'keywords': 'keywords_l',
        'tag': 'tags_l', # probably no such thing
        'url': 'urls_l'
        }

INV_ALT_KEYS=dict([(vv,kk) for kk,vv in ALT_KEYS.items()])

TYPE_DICT={'Report': 'RPRT',\
           'JournalArticle': 'JOUR',\
           'article': 'JOUR',\
           'Book': 'BOOK',\
           'BookSection': 'CHAP',\
           'ConferenceProceedings': 'CONF',\
           'Generic': 'GEN',\
           'Bill': 'BILL',\
           'Case': 'CASE',\
           'ComputerProgram': 'COMP',\
           'EncyclopediaArticle': 'ENCYC',\
           'Film': 'VIDEO',\
           'Hearing': 'HEAR',\
           'MagazineArticle': 'MGZN',\
           'NewspaperArticle': 'NEWS',\
           'Patent': 'PAT',\
           'Statute': 'STAT',\
           'Thesis': 'THES',\
           'WebPage': 'ELEC',\
           'WorkingPaper': 'MANSCPT'}


KEYWORD_DICT={'title': 'TI',\
              'issue': 'IS',\
              'publication': 'JO',\
              'volume': 'VL',\
              'doi': 'DO',\
              'abstract': 'AB',\
              'edition': 'ET',\
              'ISBN': 'SN',\
              'isbn': 'SN',\
              'ISSN': 'SN',\
              'issn': 'SN',\
              'publisher': 'PB',\
              #'keywords': 'KW',\
              #'path': 'L1',\
              'notes': 'N1',\
              'editor': 'ED'}


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


def splitNames(entry):

    firstnames=[]
    lastnames=[]
    for nii in entry['authors']:
        lii,fii=nii.split(',',1)
        firstnames.append(fii.strip())
        lastnames.append(lii.strip())

    entry['firstNames_l']=firstnames
    entry['lastName_l']=lastnames

    return entry



def readRISFile(filename):

    filename=os.path.abspath(filename)
    if not os.path.exists(filename):
        return None

    results=[]
    with open(filename,'r') as fin:
        entries=readris(fin)
        for eii in entries:

            #eii=altKeys(eii,ALT_KEYS)

            # type
            if eii['type_of_reference']=='JOUR':
                eii['type']='article'
            if eii['type_of_reference']=='BOOK':
                eii['type']='book'

            # authors
            if 'authors' not in eii:
                authors=[]
                for kii in ['first_authors', 'secondary_authors',
                        'tertiary_authors', 'subsidiary_authors']:
                    aii=eii.get(kii)
                    if aii:
                        authors.extend(aii)
                eii['authors']=authors
            eii=splitNames(eii)

            # title
            title=eii.get('title')
            if not title:
                for tii in ['primary_title', 'secondary_title', 'tertiary_title',
                        'translated_title']:
                    if tii in eii:
                        eii['title']=eii[tii]
                        break

            # citationkey
            citationkey=eii.get('id')
            if citationkey:
                eii['citationkey']=citationkey

            # date
            if 'date' in eii:
                year,month,day=eii['date'].split('/')
                eii['year']=year
                eii['month']=month
                eii['day']=day

            # pages
            sp=eii.get('start_page', 'n/a')
            ep=eii.get('end_page', 'n/a')
            eii['pages']='%s-%s' %(sp,ep)

            # publication
            if 'journal_name' in eii and 'publication' not in eii:
                eii['publication']=eii['journal_name']

            # keywords
            kw=eii.get('keywords')
            if kw:
                eii['keywords_l']=kw

            # files
            f1=eii.get('file_attachments1')
            f2=eii.get('file_attachments2')
            files=[fii for fii in [f1,f2] if fii]
            eii['files_l']=files

            # notes
            notes=eii.get('notes')
            if notes:
                eii['notes']='\n\n'.join(notes)

            # urls
            urls=eii.get('url')
            if urls:
                eii['urls_l']=[urls,]

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


def metaDictToRIS(jobid,metadict):

    try:
        text=parseMeta(metadict)
        return 0,jobid,text,metadict['id']
    except:
        return 1,jobid,'',metadict['id']


def parseMeta(metadict):

    def getField(doc,field,default=''):
        return doc[field] or default

    page_re=re.compile('(.*?)-+(.*)', re.UNICODE)
    def _subDash(match):
        return '%s--%s' %(match.group(1),match.group(2))

    #--------------------Get type--------------------
    doctype=getField(metadict,'type','article')
    doctype=TYPE_DICT[doctype]

    entries=['TY - %s' %doctype,]

    #-------------------Get authors-------------------
    authors=sqlitedb.zipAuthors(metadict['firstNames_l'], metadict['lastName_l'])
    for aii in authors:
        entries.append('AU - %s' %aii)
    #authors=latexencode.utf8tolatex(authors)
    
    #----------------------Get id----------------------
    citationkey=metadict['citationkey']
    if citationkey:
        entries.append('ID - %s' %citationkey)

    #---------------------Get time---------------------
    year=getField(metadict,'year','')
    month=getField(metadict,'month','')
    day=getField(metadict,'day','')
    time=[]
    for ii in [year,month,day]:
        try:
            ii=str(int(ii))
        except:
            # vv is nan
            ii=''
        time.append(ii)
    if year!='':
        entries.append('PY - %s' %time[0])
    time='%s/%s/%s/' %(time[0],time[1],time[2])
    entries.append('DA - %s' %time)
    entries.append('Y1 - %s' %time)

    #--------------------Get pages--------------------
    pages=getField(metadict,'pages','')
    if pages!='':
        pmatch=page_re.match(pages)
        if pmatch is None:
            entries.append('SP - %s' %str(pages))
            #entries.append('SP - %s' %tools.deu(pages))
        else:
            entries.append('SP - %s' %str(pmatch.group(1)))
            entries.append('EP - %s' %str(pmatch.group(2)))
            #entries.append('SP - %s' %tools.deu(pmatch.group(1)))
            #entries.append('EP - %s' %tools.deu(pmatch.group(2)))

    #-----------------Get city/country-----------------
    loc=''
    city=getField(metadict,'city','')
    country=getField(metadict,'country','')
    if city!='':
        loc=u'%s, %s' %(loc,city)
    if country!='':
        loc=u'%s, %s' %(loc,country)
    if len(loc)>0:
        entries.append('CY - %s' %loc)

    #------------------Get file path------------------
    files=metadict['files_l']
    if files:
        # can only store 2 files?
        for fii in files[:2]:
            entries.append('L1 - %s' %fii)

    #--------------Populate other fields--------------
    for kk,vv in metadict.items():
        if vv is None:
            continue
        if kk in ['type','firstnames','lastname','docid','year','month',\
                'day','pages','city','country', 'path']:
            continue

        if kk =='keywords_l' and len(vv)>0:
            for kii in vv:
                entries.append('KW - %s' %kii)

	#-----------Specifiy issn and isbn-----------------
        if kk.lower()=='issn':
            vv='issn %s' %vv
        if kk.lower()=='isbn':
            vv='isbn %s' %vv

        #--------------------All others--------------------
        kk=KEYWORD_DICT.get(kk,None)
        if kk is None:
            continue
            entries.append('%s - %s' %(kk,vv))

    entries.append('ER -\n')
    string='\n'.join(entries)

    return string


if __name__=='__main__':

    filename='../testris4.ris'

    '''
    print('list tags',LIST_TYPE_TAGS)

    with open(filename,'r') as fin:
        entries=readris(fin)
        for eii in entries:
            pprint(eii)
    '''
    results=readRISFile(filename)
    km=TAG_KEY_MAPPING

    for ii in results:
        print('#################################\n')
        pprint(ii)

        #rii=parseMeta(ii)
        #pprint(rii)
        rii=metaDictToRIS(0,ii)
        print(rii)

