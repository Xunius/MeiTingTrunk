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
from RISparser import readris, read
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

TYPE_DICT={'Report'                : 'RPRT',
           'JournalArticle'        : 'JOUR',
           'article'               : 'JOUR',
           'Book'                  : 'BOOK',
           'book'                  : 'BOOK',
           'BookSection'           : 'CHAP',
           'ConferenceProceedings' : 'CONF',
           'Generic'               : 'GEN',
           'Bill'                  : 'BILL',
           'Case'                  : 'CASE',
           'ComputerProgram'       : 'COMP',
           'EncyclopediaArticle'   : 'ENCYC',
           'Film'                  : 'VIDEO',
           'Hearing'               : 'HEAR',
           'MagazineArticle'       : 'MGZN',
           'NewspaperArticle'      : 'NEWS',
           'Patent'                : 'PAT',
           'Statute'               : 'STAT',
           'Thesis'                : 'THES',
           'WebPage'               : 'ELEC',
           'WorkingPaper'          : 'MANSCPT'
           }

INV_TYPE_DICT=dict([(vv,kk) for kk,vv in TYPE_DICT.items()])

KEYWORD_DICT={'title'       : 'TI',
              'issue'       : 'IS',
              'publication' : 'JO',
              'volume'      : 'VL',
              'doi'         : 'DO',
              'abstract'    : 'AB',
              'edition'     : 'ET',
              'ISBN'        : 'SN',
              'isbn'        : 'SN',
              'ISSN'        : 'SN',
              'issn'        : 'SN',
              'publisher'   : 'PB',
              'notes'       : 'N1',
              'editor'      : 'ED'
              }


DEFAULT_RIS2META_MAP={
        'first_authors'        : 'authors_l',
        'secondary_authors'    : 'authors_l',
        'secondary_authors'    : 'authors_l',
        'tertiary_authors'     : 'authors_l',
        'subsidiary_authors'   : 'authors_l',
        'abstract'             : 'abstract',
        'author_address'       : None,
        'accession_number'     : None,
        'authors'              : 'authors_l',
        'custom1'              : None,
        'custom2'              : None,
        'custom3'              : None,
        'custom4'              : None,
        'custom5'              : None,
        'custom6'              : None,
        'custom7'              : None,
        'custom8'              : None,
        'caption'              : None,
        'call_number'          : None,
        'place_published'      : 'city',
        'date'                 : 'month',
        'name_of_database'     : None,
        'doi'                  : 'doi',
        'database_provider'    : None,
        'end_page'             : None,
        'edition'              : 'edition',
        'id'                   : 'citationkey',
        'number'               : 'issue',
        'alternate_title1'     : 'publication',
        'alternate_title2'     : 'publication',
        'alternate_title3'     : 'publication',
        'journal_name'         : 'publication',
        'keywords'             : 'keywords_l',
        'file_attachments1'    : 'files_l',
        'file_attachments2'    : 'files_l',
        'figure'               : 'files_l',
        'language'             : 'language',
        'label'                : None,
        'note'                 : None,    #####
        'type_of_work'         : 'genre',
        'notes'                : 'notes',
        #'abstract'            : None,    #####
        'number_of_Volumes'    : None,
        'original_publication' : None,
        'publisher'            : 'publisher',
        'year'                 : 'year',
        'reviewed_item'        : 'reviewedArticle',
        'research_notes'       : 'notes',   #########
        'reprint_edition'      : 'reprintEdition',
        'version'              : 'sections',
        'issn'                 : 'issn',
        'start_page'           : None,
        'start_page'           : None,
        'short_title'          : 'shortTitle',
        'primary_title'        : 'title',
        'secondary_title'      : 'title',
        'tertiary_title'       : 'title',
        'translated_author'    : None,    #############
        'title'                : 'title',
        'translated_title'     : None,    #############
        'type_of_reference'    : None,
        'unknown_tag'          : None,
        'url'                  : 'urls_l',   ############
        'volume'               : 'volume',
        'publication_year'     : 'year',
        'access_date'          : 'dateAccessed'
        }



def RIStoMetaDoc(ris_dict):

    meta={}
    got_keys=[]  # store keys accessed from ris_dict

    def getKey(key):
        if key in ris_dict:
            got_keys.append(key)
            return ris_dict[key]
        else:
            raise KeyError

    #---------------------Get type---------------------
    meta['type']=INV_TYPE_DICT[ris_dict['type_of_reference']]
    got_keys.append('type_of_reference')

    #-------------------Get authors-------------------
    try:
        authors=getKey('authors')
    except KeyError:
        authors=[]
        for kii in ['first_authors', 'secondary_authors',
                'tertiary_authors', 'subsidiary_authors']:
            aii=ris_dict.get(kii)
            if aii:
                authors.extend(aii)
                got_keys.append(kii)

    firstnames, lastnames=splitNames(authors)
    meta['firstNames_l']=firstnames
    meta['lastName_l']=lastnames

    #--------------------Get title--------------------
    try:
        title=getKey('title')
    except KeyError:
        title=None
        for tii in ['primary_title', 'short_title', 'secondary_title',
                'tertiary_title', 'translated_title']:
            if tii in ris_dict:
                title=ris_dict[tii]
                got_keys.append(tii)
                break

    if title:
        meta['title']=title

    #---------------------Get date---------------------
    if 'date' in ris_dict:
        # try /year/month/day format
        try:
            year,month,day=ris_dict['date'].split('/')
        except:
            pass
        else:
            got_keys.append('date')
            #ris_dict['year']=year
            #ris_dict['month']=month
            #ris_dict['day']=day
            meta['year']=year
            meta['month']=month
            meta['day']=day

    #---------------------Get year---------------------
    try:
        year=getKey('publication_year')  # 'Y1'
    except KeyError:
        try:
            year=getKey('year')  # 'PY'
        except KeyError:
            if 'year' in meta:
                year=meta['year']
            else:
                year=None

    if year:
        meta['year']=year

    #-----------------Get citationkey-----------------
    try:
        citationkey=getKey('id')
    except KeyError:
        if len(authors)>0:
            a1=authors[0].split(',', 1)[1]
            if year:
                citationkey='%s%s' %(a1, str(year))
            else:
                citationkey=a1
        citationkey=None

    if citationkey:
        meta['citationkey']=citationkey

    #--------------------Get pages--------------------
    pages=[]
    try:
        sp=getKey('start_page')
    except KeyError:
        pass
    else:
        pages.append(sp)
    try:
        ep=getKey('end_page')
    except KeyError:
        pass
    else:
        pages.append(ep)

    pages='-'.join(pages)
    if pages:
        meta['pages']=pages

    #-----------------Get publication-----------------
    try:
        publication=getKey('journal_name')  # 'JO
    except KeyError:
        try:
            publication=getKey('secondary_title')  # 'T2'
        except KeyError:
            try:
                publication=getKey('alternate_title1')  # 'J2'
            except KeyError:
                publication=None

    if publication:
        meta['publication']=publication

    #-------------------Get keywords-------------------
    try:
        kw=getKey('keywords')
    except KeyError:
        pass
    else:
        meta['keywords_l']=kw

    #--------------------Get files--------------------
    files=[]
    for kk in ['file_attachemnts1', 'file_attachments2']:
        try:
            fkk=getKey(kk)
            files.append(fkk)
        except:
            pass
    meta['files_l']=files

    #--------------------Get notes--------------------
    try:
        notes=getKey('notes')
    except KeyError:
        pass
    else:
        meta['notes']='\n\n'.join(notes)

    #---------------------Get urls---------------------
    try:
        urls=getKey('url')
    except KeyError:
        pass
    else:
        meta['urls_l']=[urls,]

    #--------------------All others--------------------
    left_keys=list(set(ris_dict.keys()).difference(got_keys))
    LOGGER.debug('left_keys: %s' %left_keys)

    for kk in left_keys:
        vv=ris_dict[kk]
        # what this key maps to in DocMeta
        kk2=DEFAULT_RIS2META_MAP[kk]
        if kk2 is None:
            continue
        # update if not already covered
        if kk2 not in meta:
            LOGGER.debug('Update key = %s, newkey = %s, value = %s'\
                    %(kk, kk2, vv))
            if kk2.endswith('_l'):
                if isinstance(vv, (list, tuple)):
                    meta[kk2]=vv
                else:
                    meta[kk2]=[vv,]
            else:
                meta[kk2]=vv

    return meta




def splitNames(author_list):

    firstnames=[]
    lastnames=[]
    for nii in author_list:
        nameii=nii.split(',',1)
        if len(nameii)>1:
            lii,fii=nameii
            fii=fii.strip()
            lii=lii.strip()
        else:
            fii=''
            lii=nameii[0].strip()
        firstnames.append(fii)
        lastnames.append(lii)

    return firstnames, lastnames


def correctEncoding(fin):
    '''Correct for BOM encoding issues

    Args:
        fin (file object): opened file object.

    Returns:
        lines (list): list of lines read from fin.

    See https://stackoverflow.com/a/17912811/2005415 for details
    '''

    lines=fin.readlines()
    l1=lines[0]
    if len(l1) >= 3 and (l1[0], l1[1], l1[2]) == ('\xef', '\xbb', '\xbf'):
        lines[0]=l1[3:]
    elif len(l1) >= 1 and l1[0] == '\ufeff':
        lines[0]=l1[1:]
    else:
        pass

    return lines


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

        lines=correctEncoding(fin)
        # NOTE that an BOM encoding bug in RISparser makes some files encoded
        # in utf-8-sig failed to be read by readris(). When decoded by utf-8,
        # these files gives a first char of '\ufeff', and RISparser will fail
        # to recognize it. So read all lines in and use read() instead.
        #entries=readris(fin)
        entries=read(lines)
        LOGGER.info('Read in RIS file: %s' %filename)

        for eii in entries:
            metadocii=sqlitedb.DocMeta()
            docii=RIStoMetaDoc(eii)
            metadocii.update(docii)
            results.append(metadocii)

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
    entries=['TY  - %s' %doctype,]

    LOGGER.debug('doctype (TY) = %s' %doctype)

    #-------------------Get authors-------------------
    authors=sqlitedb.zipAuthors(metadict['firstNames_l'], metadict['lastName_l'])
    for aii in authors:
        entries.append('AU  - %s' %aii)

        LOGGER.debug('authors (AU) = %s' %aii)
    #authors=latexencode.utf8tolatex(authors)

    #----------------------Get id----------------------
    citationkey=metadict['citationkey']
    if citationkey:
        entries.append('ID  - %s' %citationkey)

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
        entries.append('PY  - %s' %time[0])
        entries.append('Y1  - %s' %year)
        time='%s/%s/%s' %(time[0],time[1],time[2])
        entries.append('DA  - %s' %time)

        LOGGER.debug('time (PY, DA, Y1) = %s' %time)

    #--------------------Get pages--------------------
    pages=getField(metadict,'pages','')
    if pages!='':
        pmatch=page_re.match(pages)
        if pmatch is None:
            entries.append('SP  - %s' %str(pages))
            LOGGER.debug('pages (SP) = %s' %(str(pages)))
        else:
            entries.append('SP  - %s' %str(pmatch.group(1)))
            entries.append('EP  - %s' %str(pmatch.group(2)))

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
        entries.append('CY  - %s' %loc)

    LOGGER.debug('city (CY) = %s' %loc)

    #------------------Get file path------------------
    files=metadict['files_l']
    if files:
        # can only store 2 files?
        for fii in files[:2]:
            entries.append('L1  - %s' %os.path.join(path_prefix,fii))

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
                entries.append('KW  - %s' %kii)

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
        entries.append('%s  - %s' %(kk,vv))
        LOGGER.debug('other key (%s) = %s' %(kk,vv))

    entries.append('ER  - \n')
    string='\n'.join(entries)

    LOGGER.info('Done writing to RIS format')

    return string




if __name__=='__main__':

    filename='/home/guangzhi/btsync_manjaro/aaa(1).txt'
    filename='./MeiTingTrunk/samples/sample_ris1.ris'

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
        rii=metaDictToRIS(0,ii, 'aaa')
        print(rii)

