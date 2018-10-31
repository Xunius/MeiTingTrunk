from pprint import pprint
from collections import Counter
import numpy as np

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

from io import StringIO
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage



'''
idea: to get a guess of the title, fetch the 1st page,
get all LTTextLineHorziontal objs, compare their height attributes,
the one with the largest height (font size) is likely the title.

Also, the one underneath that is likely the author list.

'''


NON_TITLE_LIST=[
        'publication',
        'publications',
        ]

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

def sortY(objs,verbose=True):
    '''Sort objs vertically

    Sort objs with similar x coordinates by y coordinates
    '''

    objdict={}
    for ii in objs:
        objdict[-ii.bbox[3],ii.bbox[0]]=ii

    keys=objdict.keys()
    keys=sorted(keys)

    result=[objdict[ii] for ii in keys]

    return result


def _checkLargetFontLine(lines):

    heights=[round(lii.height,4) for lii in lines]
    __import__('pdb').set_trace()

    #if abs(max(heights)-main_height)<0.1:
        #print('probably something wrong')
        #return

    largest_idx=[ii for ii in range(len(heights)) if heights[ii]==max(heights)]
    largest_lines=[lines[ii] for ii in largest_idx]

    if len(largest_lines)==1:
        guess_title=largest_lines[0].get_text().strip()

        # skip some none title things:
        if guess_title.lower() in NON_TITLE_LIST:
            lines.remove(largest_lines[0])
            guess_title=_checkLargetFontLine(lines)
            return guess_title

        # if too few words, probably not a title
        if len(guess_title.split())<=4:
            lines.remove(largest_lines[0])
            guess_title=_checkLargetFontLine(lines)
            return guess_title

    if len(largest_lines)>1:
        largest_lines=sortY(largest_lines)

    if len(largest_lines)>2:

        # y coordinates
        y_coords=[round(lii.y0,4) for lii in largest_lines]
        y_gaps=[y_coords[ii]-y_coords[ii+1] for ii in range(len(y_coords)-1)]

        if np.std(y_gaps)>2:
            if len(y_gaps)==2:
                popidx=y_gaps.index(max(y_gaps))

            elif len(y_gaps)>2:
                gaps_counters=Counter(y_gaps)
                leastcom=gaps_counters.most_common()[-1][0]
                popidx=y_gaps.index(leastcom)

            largest_lines.pop(popidx)
            guess_title=_checkLargetFontLine(largest_lines)
            return guess_title

    guess_title=' '.join([lii.get_text().strip() for lii in largest_lines])

    return guess_title






if __name__=='__main__':




    FILE_IN='mypdf5.pdf'
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
    #pprint(pages[0]._objs)
    page_w=pages[0].width
    page_h=pages[0].height
    page0=pages[0]._objs

    boxes=[objii for objii in page0 if isinstance(objii, LTTextBoxHorizontal)]

    #boxes=dict([(kk,vv) for kk,vv in enumerate(boxes)])
    lines=[]
    for bii in boxes:
        lines.extend(bii._objs)

    heights=[round(lii.height,4) for lii in lines]

    h_counter=Counter(heights)
    print(h_counter)

    # most comment height should be main text
    main_height=h_counter.most_common()[0][0]

    #------------------Filt by height------------------
    lines=[lii for lii in lines if lii.y0>=page_h//2]
    heights=[round(lii.height,4) for lii in lines]

    guess=_checkLargetFontLine(lines)

    print('guessed title: %s' %guess)






    '''
    #pdf.tree.write('test.xml',pretty_print=True,encoding='utf-8')
    pdf = pdfquery.PDFQuery(FILE_IN)
    pdf.load(0)
    aa=pdf.pq('LTTextLineHorizontal:in_bbox("15,600,100,700")')
    print(aa)
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
