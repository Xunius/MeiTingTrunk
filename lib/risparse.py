'''
Parse ris files into dict format, and export DocMeta dict to ris file.


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
from RISparser import readris
from RISparser.config import LIST_TYPE_TAGS, TAG_KEY_MAPPING
try:
    from . import sqlitedb
except:
    import sqlitedb

LOGGER=logging.getLogger(__name__)

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
    """Read and parse RIS file

    Args:
        filename (str): abspath to ris file.

    Returns: results (list): list of dicts of meta data.
    """

    filename=os.path.abspath(filename)
    if not os.path.exists(filename):
        return None

    results=[]
    with open(filename,'r') as fin:

        entries=readris(fin)
        LOGGER.info('Read in RIS file: %s' %filename)

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

            LOGGER.debug('authors = %s' %eii['authors'])

            # title
            title=eii.get('title')
            if not title:
                for tii in ['primary_title', 'secondary_title', 'tertiary_title',
                        'translated_title']:
                    if tii in eii:
                        eii['title']=eii[tii]
                        break

            LOGGER.debug('title = %s' %eii['title'])

            # citationkey
            citationkey=eii.get('id')
            if citationkey:
                eii['citationkey']=citationkey

            LOGGER.debug('citationkey = %s' %eii['citationkey'])

            # date
            if 'date' in eii:
                year,month,day=eii['date'].split('/')
                eii['year']=year
                eii['month']=month
                eii['day']=day

            LOGGER.debug('year = %s. month = %s. day = %s' %(year,month,day))

            # pages
            sp=eii.get('start_page', 'n/a')
            ep=eii.get('end_page', 'n/a')
            eii['pages']='%s-%s' %(sp,ep)

            # publication
            if 'journal_name' in eii and 'publication' not in eii:
                eii['publication']=eii['journal_name']

            LOGGER.debug('publication = %s' %eii['publication'])

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


def metaDictToRIS(jobid, metadict, path_prefix):
    """A wrapper, export meta data dict to RIS format

    Args:
        jobid (int): job id.
        metadict (dict): meta data dict.
        path_prefix (str): path prefix to prepend to attachment files.

    Returns:
        rec (int): 0 if success, 1 otherwise.
        jobid (int): input jobid.
        docid (int): 'id' value in <metadict>
    """

    try:
        text=parseMeta(metadict,path_prefix)
        return 0,jobid,text,metadict['id']
    except Exception:
        LOGGER.exception('Failed to write to RIS format. Jobid = %s. Doc id = %s'\
                %(str(jobid), metadict['id']))
        return 1,jobid,'',metadict['id']


def parseMeta(metadict, path_prefix):
    """Export meta data dict to RIS format

    Args:
        metadict (dict): meta data dict.
        path_prefix (str): path prefix to prepend to attachment files.

    Returns: string (str): RIS text.
    """

    def getField(doc,field,default=''):
        return doc[field] or default

    page_re=re.compile('(.*?)-+(.*)', re.UNICODE)
    def _subDash(match):
        return '%s--%s' %(match.group(1),match.group(2))

    #--------------------Get type--------------------
    doctype=getField(metadict,'type','article')
    doctype=TYPE_DICT[doctype]
    entries=['TY - %s' %doctype,]

    LOGGER.debug('doctype (TY) = %s' %doctype)

    #-------------------Get authors-------------------
    authors=sqlitedb.zipAuthors(metadict['firstNames_l'], metadict['lastName_l'])
    for aii in authors:
        entries.append('AU - %s' %aii)

        LOGGER.debug('authors (AU) = %s' %aii)
    #authors=latexencode.utf8tolatex(authors)

    #----------------------Get id----------------------
    citationkey=metadict['citationkey']
    if citationkey:
        entries.append('ID - %s' %citationkey)

        LOGGER.debug('citationkey (ID) = %s' %citationkey)

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

    LOGGER.debug('time (PY, DA, Y1) = %s' %time)

    #--------------------Get pages--------------------
    pages=getField(metadict,'pages','')
    if pages!='':
        pmatch=page_re.match(pages)
        if pmatch is None:
            entries.append('SP - %s' %str(pages))
            LOGGER.debug('pages (SP) = %s' %(str(pages)))
        else:
            entries.append('SP - %s' %str(pmatch.group(1)))
            entries.append('EP - %s' %str(pmatch.group(2)))

            LOGGER.debug('pages (SP) = %s' %(str(pmatch.group(1))))
            LOGGER.debug('pages (EP) = %s' %(str(pmatch.group(2))))


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

    LOGGER.debug('city (CY) = %s' %loc)

    #------------------Get file path------------------
    files=metadict['files_l']
    if files:
        # can only store 2 files?
        for fii in files[:2]:
            entries.append('L1 - %s' %os.path.join(path_prefix,fii))

            LOGGER.debug('file (L1) = %s' %fii)

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

                LOGGER.debug('keywords (KW) = %s' %kii)

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

            LOGGER.debug('other key (%s) = %s' %(kk,vv))

    entries.append('ER -\n')
    string='\n'.join(entries)

    LOGGER.info('Done writing to RIS format')

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

