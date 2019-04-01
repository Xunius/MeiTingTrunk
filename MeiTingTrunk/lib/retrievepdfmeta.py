'''
Utitlity functions for extract meta data from PDF file.


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

import re
from pprint import pprint
import logging

try:
    from . import sqlitedb
except:
    import sqlitedb

from collections import Counter

from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from PyPDF2 import PdfFileReader


#---------Regex pattern for matching dois---------
DOI_PATTERN=re.compile(r'(?:doi:)?\s?(10.[1-9][0-9]{3}/.*$)',
        re.DOTALL|re.UNICODE)

LOGGER=logging.getLogger(__name__)



def getPDFMeta_pypdf2(path):
    """Extract meta data from PDF file using PyPDF2

    Args:
        path (str): abspath to PDF file.

    Returns: info (dict): meta data dict.
    """

    with open(path, 'rb') as fin:
        pdf = PdfFileReader(fin)
        info = pdf.getDocumentInfo()
        number_of_pages = pdf.getNumPages()

    LOGGER.info('Read PDF file %s. NO. of pages = %d' %(path, number_of_pages))
    LOGGER.debug('Info of PDF file: %s' %info)

    return info


def getPDFMeta_pdfminer(path):
    """Extract meta data from PDF file using pdfminer

    Args:
        path (str): abspath to PDF file.

    Returns: info (dict): meta data dict.
    """

    with open(path, 'rb') as fin:
        parser = PDFParser(fin)
        doc = PDFDocument(parser)

    LOGGER.info('Read PDF file %s.' %path)
    LOGGER.debug('Info of PDF file: %s' %doc.info)

    return doc.info


def parseToList(text):
    """Convert a field sequence in string to a list.

    Args:
        text (str): string sequence.

    Returns: result (list): sequence split into a list.
    """

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
    """Format meta data got from PDF file

    Args:
        meta_dict (dict): dict of meta data extracted from PDF.

    Returns: DocMeta dict.

    Format changes done in this func:
        * 'author' is changed to 'authors_l', and value is a list.
        * 'keywords' is changed to 'keywords_l', and value is a list.
        * doi is searched in a regex.
    """

    result=sqlitedb.DocMeta()
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

    #result=sqlitedb.DocMeta()
    #result.update(m1[0])

    aa=prepareMeta(m2)
    print('\nmeta from pdf:')
    pprint(aa)
