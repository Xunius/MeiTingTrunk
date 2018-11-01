from pprint import pprint
from collections import Counter
from functools import partial
import numpy as np
from fuzzywuzzy import fuzz

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
        'journal of',
        ]

def up(a,b,x):
    '''Left half of a triangular membership func'''
    if abs(b-a)<=np.finfo(float).eps:
        return (x>a).astype('float')
    a,b,x=map(lambda x: np.asarray(x,dtype='float'),[a,b,x])
    y=(x-a)/(b-a)
    return np.fmin(np.fmax(0,y),1)


def down(a,b,x):
    '''Right half of a triangular membership func'''
    return 1.-up(a,b,x)


def tria(a,b,c,x):
    '''Triangular membership func'''
    a,b,c=np.sort([a,b,c])
    y=up(a,b,x)*down(b,c,x)
    return np.fmin(np.fmax(0,y),1)


def invTria(a,b,c,x):
    return 1.-tria(a,b,c,x)


def trap(a,b,c,d,x):
    '''Trapezoid membership func'''
    a,b,c,d=np.sort([a,b,c,d])
    y=up(a,b,x)*down(c,d,x)
    return np.fmin(np.fmax(0,y),1)


def invTrap(a,b,c,d,x):
    return 1.-trap(a,b,c,d,x)

class SimpleFC(object):
    def __init__(self,input_scales,output_scales,n_classes,defuzzy_method='centroid'):
        self.input_scales=input_scales
        self.output_scales=output_scales
        self.n_classes=n_classes
        defuzzy_method=defuzzy_method

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



def guessTitle(pdffile):

    # get meta data
    with open(pdffile, 'rb') as fin:
        parser = PDFParser(fin)
        doc = PDFDocument(parser)

    docinfo=doc.info[0]
    doctitle=docinfo.get('Title',None)
    if doctitle:
        doctitle=doctitle.decode('utf-8')

    document, interpreter, device=init(FILE_IN)

    # get page 1
    for ii,page in enumerate(PDFPage.create_pages(document)):
        if ii>0:
            break
        interpreter.process_page(page)
        p0 = device.get_result()

    page_w=p0.width
    page_h=p0.height
    p0_objs=p0._objs

    boxes=[objii for objii in p0_objs if isinstance(objii, LTTextBoxHorizontal)]

    # get all lines
    lines=[]
    for bii in boxes:
        lines.extend(bii._objs)

    # get all line heights
    heights=[round(lii.height,4) for lii in lines]

    # most comment height should be main text
    h_counter=Counter(heights)
    main_height=h_counter.most_common()[0][0]

    #------------------Filt by y coordinates------------------
    lines=[lii for lii in lines if lii.y0>=page_h//2]
    heights=[round(lii.height,4) for lii in lines]

    guess=_checkLargetFontLine(lines)

    print('guessed title: %s' %guess)

    return guess


def guessTitle2(pdffile):

    # get meta data
    with open(pdffile, 'rb') as fin:
        parser = PDFParser(fin)
        doc = PDFDocument(parser)

    docinfo=doc.info[0]
    doctitle=docinfo.get('Title',None)
    if doctitle:
        doctitle=doctitle.decode('utf-8')

    document, interpreter, device=init(FILE_IN)

    # get page 1
    for ii,page in enumerate(PDFPage.create_pages(document)):
        if ii>0:
            break
        interpreter.process_page(page)
        p0 = device.get_result()

    page_w=p0.width
    page_h=p0.height
    p0_objs=p0._objs

    boxes=[objii for objii in p0_objs if isinstance(objii, LTTextBoxHorizontal)]

    # get all lines
    lines=[]
    for bii in boxes:
        lines.extend(bii._objs)

    # get all line heights
    heights=[round(lii.height,4) for lii in lines]

    # most comment height should be main text
    h_counter=Counter(heights)
    main_height=h_counter.most_common()[0][0]

    #------------------Filt by y coordinates------------------
    line_dict=dict([(lii,round(lii.height,4)) for lii in lines if\
            lii.y0>=page_h//2])
    #lsort=sorted(line_dict,key=line_dict.get,reverse=True)

    heights=list(set(line_dict.values()))
    heights.sort(reverse=True)

    __import__('pdb').set_trace()

    #-------------Group by heights and y0-------------
    groups=[]
    for hii in heights:
        print('hii',hii)
        lsii=[kk for kk,vv in line_dict.items() if vv==hii]
        lsii=sortY(lsii)

        # check line gaps
        if len(lsii)>2:
            ysii=[round(ljj.y0,2) for ljj in lsii]
            gapsii=[round(ysii[jj]-ysii[jj+1],2) for jj in range(len(ysii)-1)]
            if len(set(gapsii))==1:
                groups.append(lsii)
            else:
                # kmeans clustering
                costs=[]
                members=[]
                for jj in range(1,len(ysii)):
                    memberjj,costjj=kmeans(ysii,jj)
                    print('jj', jj, 'cjj', costjj, 'memberjj', memberjj)
                    costs.append(costjj)
                    members.append(memberjj)

                idx=np.argmin(costs)
                __import__('pdb').set_trace()
                for kk in members[idx]:
                    groups.append([ysii[ll] for ll in range(len(ysii)) if ll==kk])

                __import__('pdb').set_trace()




    # build fuzzy logic

    x_hr=np.arange(0,5)
    x_nottile_fm=np.arange(0,101)
    x_nwords=np.arange(1,70)
    x_linegap=np.arange(0,200)
    x_metatitle_fm=np.arange(0,101)

    y_score=np.arange(0,101)

    hrLow=partial(invTrap,0,1.5,4,5)
    hrHigh=partial(tria,1.2,3,4)

    nottileFmLow=partial(up,50,100)
    nottileFmHigh=partial(down,0,60)

    nwordsLow=partial(invTrap,1,6,40,70)
    nwordsHigh=partial(tria,5,20,50)

    lineGapLow=partial(invTrap,1,6,40,200)
    lineGapHigh=partial(tria,5,20,50)

    metaTitleFmLow=partial(down,0,70)
    metaTitleFmHigh=partial(up,30,100)





    guess=_checkLargetFontLine(lines)

    print('guessed title: %s' %guess)

    return guess





def kmeans(xs,k,max_iter=250):

    xs=np.array(xs)
    nx=len(xs)

    '''
    if k==1:
        return [0,], np.var(xs)
    elif k==nx:
        return range(len(xs)), 0
    '''

    centers=np.random.randint(xs.min(),xs.max(),size=k).astype('float')
    member=np.zeros(nx)

    for ii in range(max_iter):
        distsii=abs(xs[:,None]-centers[None,:])
        member_new=np.argmin(distsii,axis=1)
        for jj in range(k):
            centers[jj]=np.mean(xs[member_new==jj])

        if all(member_new==member):
            break
        member=member_new

    cost=0
    for ii in range(nx):
        cii=(xs[ii]-centers[int(member[ii])])**2
        cost+=cii

    return member, cost











if __name__=='__main__':



    FILE_IN='mypdf9.pdf'

    guess=guessTitle2(FILE_IN)

