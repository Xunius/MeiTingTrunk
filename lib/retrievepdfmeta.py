#from pdfminer.pdfparser import PDFParser, PDFDocument
from pdfminer.pdftypes import resolve1

from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument

#fp = open('mypdf.pdf', 'rb')
#parser = PDFParser(fp)
#doc = PDFDocument()
#parser.set_document(doc)
#doc.set_parser(parser)
#doc.initialize()





fp = open('mypdf.pdf', 'rb')
parser = PDFParser(fp)
doc = PDFDocument(parser)

print(doc.info)        # The "Info" metadata

if 'Metadata' in doc.catalog:
    metadata = resolve1(doc.catalog['Metadata']).get_data()
    print(metadata)  # The raw XMP metadata
