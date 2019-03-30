'''
DOI query.


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

import logging
from crossref.restful import Works, Etiquette
#from habanero import Crossref, cn
try:
    from . import sqlitedb
except:
    import sqlitedb
#from ..gui import __version__

__version__='v0.1alpha'


ETIQUETTE=Etiquette('MeiTing-Trunk', __version__, 'github',
        'xugzhi1987@gmail.com')

LOGGER=logging.getLogger(__name__)



def fetchMetaByDOI(doi):

    works=Works(etiquette=ETIQUETTE)
    try:
        data=works.doi(doi)
    except:
        rec=1

    if data is None:
        rec=1
    else:
        rec=0

    LOGGER.info('DOI = %s. Rec of doi query = %s' %(doi, rec))

    return rec,data




def crossRefToMetaDict(in_dict):

    result=sqlitedb.DocMeta()
    in_dict=dict([(kk.lower(),vv) for kk,vv in in_dict.items()])

    keys=['title', 'issue', 'pages', 'publication', 'volume', 'year', 'doi',
            'abstract', 'arxivId', 'chapter', 'city', 'country', 'edition',
            'institution', 'isbn', 'issn', 'month', 'day', 'publisher',
            'series', 'pmid' ]

    # get type
    _type=in_dict.get('type',None)
    if _type=='journal-article':
        result['type']='article'
    else:
        # not supported yet
        result['type']='article'

    # get authors
    authors=in_dict.get('author',None)
    if authors:
        firstnames=[aii.get('given','') for aii in authors]
        lastnames=[aii.get('family','') for aii in authors]
        result['firstNames_l']=firstnames
        result['lastName_l']=lastnames

    # get others
    for keyii in keys:
        if keyii in in_dict:
            vii=in_dict[keyii]
            if isinstance(vii, list):
                vii=''.join(vii) # title is a list
            result[keyii]=vii

    # sometimes this is journal name
    if 'journal-title' in in_dict:
        result['publication']=in_dict['journal-title']
    else:
        if 'container-title' in in_dict:
            vii=in_dict['container-title']
            if isinstance(vii, list):
                vii=''.join(vii) # title is a list
            result['publication']=vii

    if 'page' in in_dict:
        result['pages']=in_dict['page']

    if 'url' in in_dict:
        result['urls_l']=[in_dict['url'],]

    # get time
    if 'year' not in in_dict:
        if 'issued' in in_dict:
            issued=in_dict['issued']
        elif 'published-print' in in_dict:
            issued=in_dict['published-print']

        if 'date-parts' in issued:
            try:
                date=issued['date-parts'][0]
                if len(date)==2:
                    year,month=date
                    result['year']=str(year)
                    result['month']=str(month)
                elif len(date)==3:
                    year,month,day=date
                    result['year']=str(year)
                    result['month']=str(month)
                    result['day']=str(day)
            except:
                pass

    #result['confirmed']='true'

    return result
