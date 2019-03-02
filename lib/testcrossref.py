from crossref.restful import Works, Etiquette
from pprint import pprint
from habanero import Crossref, cn
from sqlitedb import DocMeta


def fetchMetaByDOI(doi):

    eti=Etiquette('MeiTing-Trunk', 'v0.1alpha', 'not published yet',
            'xugzhi1987@gmail.com')
    print(str(eti))
    works=Works(etiquette=eti)
    #aa=works.doi('10.1590/0102-311x00133115')
    aa=works.doi(doi)

def crossRefToMetaDict(in_dict):

    result=DocMeta()
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








if __name__=='__main__':

    doi='10.1126/science.169.3946.635'
    doi='10.1175/1520-0477(2001)082<1377:IOGPPT>2.3.CO;2k'
    doi='10.1029/2002JD002499'
    doi='10.1175/1525-7541(2003)004<1147:tvgpcp>2.0.co;2'

    aa=cn.content_negotiation(ids = doi, format = "bibentry")
    cr=Crossref(mailto='xugzhi1987@gmail.com')
    works=cr.works(ids=doi)
    pprint(works)

    bb=crossRefToMetaDict(works['message'])
    print(bb)

    '''
    eti=Etiquette('MeiTing-Trunk', 'v0.1alpha', 'not published yet',
            'xugzhi1987@gmail.com')
    print(str(eti))
    works=Works(etiquette=eti)
    #aa=works.doi('10.1590/0102-311x00133115')
    aa=works.doi(doi)
    pprint(aa)

    bb=crossRefToMetaDict(aa)
    '''
    '''
    cn.content_negotiation(ids = '10.1126/science.169.3946.635')
    cn.content_negotiation(ids = '10.1126/science.169.3946.635', format = "citeproc-json")
    cn.content_negotiation(ids = "10.1126/science.169.3946.635", format = "rdf-xml")
    cn.content_negotiation(ids = "10.1126/science.169.3946.635", format = "text")
    cn.content_negotiation(ids = "10.1126/science.169.3946.635", format = "text", style = "apa")
    '''
    '''

    cr=Crossref(mailto='xugzhi1987@gmail.com')
    works=cr.works(ids=doi)
    print(works)
    '''



