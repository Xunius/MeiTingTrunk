#from pdfminer.pdfparser import PDFParser, PDFDocument
import os
import re
from pprint import pprint
from pdfminer.pdftypes import resolve1

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

def getPDFMeta(path):

    reader=_meta_pdf_reader()
    __import__('pdb').set_trace()

    with open(path, 'rb') as fin:
        #pdf = PdfFileReader(fin)
        #info = pdf.getDocumentInfo()
        #number_of_pages = pdf.getNumPages()

        aa=reader.read_metadata(fin)

    print('info of file:')
    #pprint(info)
    #print('number of pages:',number_of_pages)
    #author = info.author
    #creator = info.creator
    #producer = info.producer
    #subject = info.subject
    #title = info.title

class _meta_pdf_reader(object):

    def __init__(self):
        self.instance = self.__hash__()
        self.metadata_regex = re.compile('(?:\/(\w+)\s?\(([^\n\r]*)\)\n?\r?)', re.S)
        self.metadata_offset = 2048

    def read_metadata(self, stream):

        """This function reads a PDF file stream and returns its metadata.
        :param file_name: The PDF file stream to read.
        :type file_name: str
        :returns: dict -- The returned metadata as a dictionary of properties.

        """

        # Scan the last 2048 bytes, the most
        # frequent metadata density block
        stream.seek(-self.metadata_offset, os.SEEK_END)
        try:
            #properties = dict(('/' + p.group(1), p.group(2).decode('utf-8')) \
            properties = dict(('/' + p.group(1), p.group(2)) \
                for p in self.metadata_regex.finditer(stream.read(self.metadata_offset).decode('utf-8')))
            if '/Author' in properties:
                return properties
        except UnicodeDecodeError:
            properties.clear()

        # Parse the xref table using pyPdf
        properties = PdfFileReader(stream).documentInfo
        if properties:
            return properties

        return {}


if __name__=='__main__':

    #FILE_IN='mypdf4.pdf'
    #fp = open(FILE_IN, 'rb')
    #parser = PDFParser(fp)
    #doc = PDFDocument(parser)

    #pprint(doc.info)        # The "Info" metadata
    #print('-------------------')

    #if 'Metadata' in doc.catalog:
        #metadata = resolve1(doc.catalog['Metadata']).get_data()
        #pprint(metadata)  # The raw XMP metadata
        #aa=xmp_to_dict(metadata)
        #pprint(aa)

    #print('-------------------')
    #get_info(FILE_IN)

    folder='~/Papers/collection'
    folder=os.path.expanduser(folder)
    filelist=os.listdir(folder)
    n=0
    for fii in filelist:
        if fii[-3:]!='pdf':
            continue
        n+=1
        if n>=80:
            break
        print('\n#############################################')
        print(fii)
        abpathii=os.path.join(folder,fii)
        try:
            getPDFMeta(abpathii)

            #fp = open(abpathii, 'rb')
            #parser = PDFParser(fp)
            #doc = PDFDocument(parser)
            #pprint(doc.info)        # The "Info" metadata
        except:
            print('failed file:',fii)


