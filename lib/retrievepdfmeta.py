import os
import re
from pprint import pprint
import logging
from pdfminer.pdftypes import resolve1

try:
    from . import sqlitedb
except:
    import sqlitedb

from collections import Counter

from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from PyPDF2 import PdfFileReader

from collections import defaultdict
from xml.etree import ElementTree as ET

RDF_NS = '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}'
XML_NS = '{http://www.w3.org/XML/1998/namespace}'
NS_MAP = {
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#'    : 'rdf',
    'http://purl.org/dc/elements/1.1/'               : 'dc',
    'http://ns.adobe.com/xap/1.0/'                   : 'xap',
    'http://ns.adobe.com/pdf/1.3/'                   : 'pdf',
    'http://ns.adobe.com/xap/1.0/mm/'                : 'xapmm',
    'http://ns.adobe.com/pdfx/1.3/'                  : 'pdfx',
    'http://prismstandard.org/namespaces/basic/2.0/' : 'prism',
    'http://crossref.org/crossmark/1.0/'             : 'crossmark',
    'http://ns.adobe.com/xap/1.0/rights/'            : 'rights',
    'http://www.w3.org/XML/1998/namespace'           : 'xml'
}


#---------Regex pattern for matching dois---------
DOI_PATTERN=re.compile(r'(?:doi:)?\s?(10.[1-9][0-9]{3}/.*$)',
        re.DOTALL|re.UNICODE)

LOGGER=logging.getLogger(__name__)

class XmpParser(object):
    """
    Parses an XMP string into a dictionary.

    Usage:

        parser = XmpParser(xmpstring)
        meta = parser.meta
    """

    def __init__(self, xmp):
        self.tree = ET.XML(xmp)
        self.rdftree = self.tree.find(RDF_NS+'RDF')

    @property
    def meta(self):
        """ A dictionary of all the parsed metadata. """
        meta = defaultdict(dict)
        for desc in self.rdftree.findall(RDF_NS+'Description'):
            for el in desc.getchildren():
                ns, tag =  self._parse_tag(el)
                value = self._parse_value(el)
                meta[ns][tag] = value
        return dict(meta)

    def _parse_tag(self, el):
        """ Extract the namespace and tag from an element. """
        ns = None
        tag = el.tag
        if tag[0] == "{":
            ns, tag = tag[1:].split('}',1)
            if ns in NS_MAP:
                ns = NS_MAP[ns]
        return ns, tag

    def _parse_value(self, el):
        """ Extract the metadata value from an element. """
        if el.find(RDF_NS+'Bag') is not None:
            value = []
            for li in el.findall(RDF_NS+'Bag/'+RDF_NS+'li'):
                value.append(li.text)
        elif el.find(RDF_NS+'Seq') is not None:
            value = []
            for li in el.findall(RDF_NS+'Seq/'+RDF_NS+'li'):
                value.append(li.text)
        elif el.find(RDF_NS+'Alt') is not None:
            value = {}
            for li in el.findall(RDF_NS+'Alt/'+RDF_NS+'li'):
                value[li.get(XML_NS+'lang')] = li.text
        else:
            value = el.text
        return value

def xmp_to_dict(xmp):
    """ Shorthand function for parsing an XMP string into a python dictionary. """
    return XmpParser(xmp).meta

def getPDFMeta_pypdf2(path):

    with open(path, 'rb') as fin:
        pdf = PdfFileReader(fin)
        info = pdf.getDocumentInfo()
        number_of_pages = pdf.getNumPages()

    LOGGER.info('Read PDF file %s. NO. of pages = %d' %(path, number_of_pages))
    LOGGER.debug('Info of PDF file: %s' %info)

    return info


def getPDFMeta_pdfminer(path):

    with open(path, 'rb') as fin:
        parser = PDFParser(fin)
        doc = PDFDocument(parser)

    LOGGER.info('Read PDF file %s.' %path)
    LOGGER.debug('Info of PDF file: %s' %doc.info)

    return doc.info


def getPDFMeta_xmlparse(path):

    with open(path, 'rb') as fin:
        parser = PDFParser(fin)
        doc = PDFDocument(parser)

        if 'Metadata' in doc.catalog:
            metadata = resolve1(doc.catalog['Metadata']).get_data()
            info=xmp_to_dict(metadata)
            #pprint(info)

    return info



def parseToList(text):
    result=[]
    if ' and ' in text:
        delim=' and '
    else:
        delim=',' if ',' in text else ';'
    textlist=text.replace('\n',delim).strip(delim).split(delim)
    for tii in textlist:
        tii=str(tii).strip()
        if len(tii)>0:
            result.append(tii)
    return result

def prepareMeta(meta_dict):


    result=sqlitedb.DocMeta()
    #result={}
    gotdois=[]
    for kk,vv in meta_dict.items():
        if len(vv)>0:
            kk=kk.lower().lstrip('/') # pypdf2 convention starts with /
            if kk=='author':
                result['authors_l']=parseToList(vv)
            elif kk=='keywords':
                result['keywords_l']=parseToList(vv)
            elif kk in ['title', ]:
                result[kk]=str(vv)

            match=DOI_PATTERN.match(vv)
            if match:
                gotdois.append(vv)

    if len(gotdois)>0:
        counter=Counter(gotdois)
        doi=counter.most_common(1)[0][0]
        result['doi']=doi


    return result






if __name__=='__main__':

    FILE_IN='testpdf2.pdf'
    FILE_IN='mypdf2.pdf'



    print('\nget meta data using pdfminer--------------')
    m1=getPDFMeta_pdfminer(FILE_IN)

    print('\nget meta data using pypdf2--------------')
    m2=getPDFMeta_pypdf2(FILE_IN)

    print('\nget meta data using xmlparser--------------')
    m3=getPDFMeta_xmlparse(FILE_IN)

    #result=sqlitedb.DocMeta()
    #result.update(m1[0])

    aa=prepareMeta(m2)
    print('\nmeta from pdf:')
    pprint(aa)
