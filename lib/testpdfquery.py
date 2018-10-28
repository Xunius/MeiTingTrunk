from pprint import pprint
import pdfquery
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LTTextBox, LTTextLine, LTAnno,\
        LTTextBoxHorizontal, LTTextLineHorizontal, LTChar

from PyPDF2 import PdfFileReader

FILE_IN='mypdf2.pdf'


'''
idea: to get a guess of the title, fetch the 1st page,
get all LTTextLineHorziontal objs, compare their height attributes,
the one with the largest height (font size) is likely the title.

Also, the one underneath that is likely the author list.

'''

#------------------------Initiate analysis objs------------------------
def init(filename,verbose=True):
    '''Initiate analysis objs
    '''

    fp = open(filename, 'rb')
    # Create a PDF parser object associated with the file object.
    parser = PDFParser(fp)
    # Create a PDF document object that stores the document structure.
    # Supply the password for initialization.
    document = PDFDocument(parser)
    # Check if the document allows text extraction. If not, abort.
    if not document.is_extractable:
        raise PDFTextExtractionNotAllowed
    # Create a PDF resource manager object that stores shared resources.
    rsrcmgr = PDFResourceManager()
    # Create a PDF device object.
    device = PDFDevice(rsrcmgr)
    # Create a PDF interpreter object.
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    # Set parameters for analysis.
    laparams = LAParams()

    # Create a PDF page aggregator object.
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    return document, interpreter, device


pdf = pdfquery.PDFQuery(FILE_IN)

pdf.load(0)
aa=pdf.pq('LTTextLineHorizontal:in_bbox("15,600,100,700")')
print(aa)

#pdf.tree.write('test.xml',pretty_print=True,encoding='utf-8')

document, interpreter, device=init(FILE_IN)

with open(FILE_IN, 'rb') as fin:
    pdf2=PdfFileReader(fin)
    print(pdf2.getNumPages())


pages=[]
for ii,page in enumerate(PDFPage.create_pages(document)):

    if ii>0:
        break
    print(ii,page)
    interpreter.process_page(page)
    layout = device.get_result()
    pages.append(layout)

print(pages)
pprint(pages[0]._objs)

'''
pdf.extract( [
     ('with_parent','LTPage[pageid=1]'),
     ('with_formatter', 'text'),

     ('last_name', 'LTTextLineHorizontal:in_bbox("315,680,395,700")'),
     ('spouse', 'LTTextLineHorizontal:in_bbox("170,650,220,680")'),

     ('with_parent','LTPage[pageid=2]'),

     ('oath', 'LTTextLineHorizontal:contains("perjury")', lambda match: match.text()[:30]+"..."),
     ('year', 'LTTextLineHorizontal:contains("Form 1040A (")', lambda match: int(match.text()[-5:-1]))
 ])
'''