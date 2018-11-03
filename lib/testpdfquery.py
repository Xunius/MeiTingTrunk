from functools import reduce
from scipy.interpolate import interp1d
from itertools import combinations
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


def getLineHeight(lineobj):
    heights=[]
    for ii in lineobj._objs:
        if hasattr(ii,'height'):
            heights.append(ii.height)
    return np.mean(heights)


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
    #heights=[round(lii.height,4) for lii in lines]
    heights=[round(getLineHeight(lii),4) for lii in lines]

    # most comment height should be main text
    h_counter=Counter(heights)
    main_height=h_counter.most_common()[0][0]

    #------------------Filt by y coordinates------------------
    line_dict=dict([(lii,round(getLineHeight(lii),4)) for lii in lines if\
            lii.y0>=page_h//2])
    #lsort=sorted(line_dict,key=line_dict.get,reverse=True)

    heights=list(set(line_dict.values()))
    heights.sort(reverse=True)

    #-------------Group by heights and y0-------------
    groups=[]
    for hii in heights:
        if hii<=main_height:
            break
        print('hii',hii)
        lsii=[kk for kk,vv in line_dict.items() if vv==hii]
        lsii=sortY(lsii)

        if len(lsii)==1:
            groups.append(lsii)
        elif len(lsii)==2:
            if lsii[0].vdistance(lsii[1])>lsii[0].height:
                groups.append([lsii[0]])
                groups.append([lsii[1]])
            else:
                groups.append(lsii)

        # check line gaps
        if len(lsii)>2:
            ysii=[round(ljj.y0,2) for ljj in lsii]
            gapsii=[round(ysii[jj]-ysii[jj+1],1) for jj in range(len(ysii)-1)]
            if len(set(gapsii))==1:
                groups.append(lsii)

            else:
                # kmeans clustering
                costs=[]
                groupingii=[]
                for jj in range(1,len(ysii)):
                    grjj,costjj=kmeans2(ysii,jj)
                    print('jj', jj, 'cjj', costjj, 'grouping', grjj)
                    costs.append(costjj)
                    groupingii.append(grjj)

                idx=np.argmin(costs)
                for kk in groupingii[idx]:
                    groups.append([lsii[mm] for mm in kk])



    # get grouped line texts

    gr_lines=[]
    for gii in groups:
        gii=sortY(gii)
        tii=[ljj.get_text().strip() for ljj in gii]
        tii=' '.join(tii)
        hii=[getLineHeight(ljj) for ljj in gii]
        hii=np.mean(hii)

        # compute input vars for fuzzy
        hrii=hii/main_height
        y0ii=[ljj.y0 for ljj in gii]
        y0ii=np.min(y0ii)/page_h
        nwordsii=len(tii.split(' '))
        notitlefmii=[fuzz.token_set_ratio(tii,jj) for jj in NON_TITLE_LIST]
        notitlefmii=np.mean(notitlefmii)

        if doctitle:
            metatitlefmii=fuzz.ratio(tii, doctitle)
            gr_lines.append((tii,hii,y0ii,hrii,nwordsii,notitlefmii,metatitlefmii))
        else:
            gr_lines.append((tii,hii,y0ii,hrii,nwordsii,notitlefmii))


    pprint(gr_lines)

    # build fuzzy logic

    x_hr=np.arange(0,5)
    x_y0=np.arange(0,1.1,0.1)
    x_nottile_fm=np.arange(0,101)
    x_nwords=np.arange(1,70)
    x_metatitle_fm=np.arange(0,101)

    y_score=np.arange(0,101)

    hrLow=partial(invTrap, 0, 1.2, 4, 5)
    hrHigh=partial(tria, 1.1, 3.0, 4.5)

    y0Low=partial(tria, 0.4, 0.5, 1)
    y0High=partial(tria, 0.5, 0.7, 1.2)

    notitleFmLow=partial(down, 0, 55)
    notitleFmHigh=partial(up, 45, 100)

    nwordsLow=partial(invTrap, 1, 5, 30, 70)
    nwordsHigh=partial(trap, 4, 8, 20, 35)

    metaTitleFmLow=partial(down, 0, 70)
    metaTitleFmHigh=partial(up, 30, 100)

    scoreLow=partial(down,0,60)
    scoreHigh=partial(up,40,100)

    fuzz_scores=[]
    score_lo=scoreLow(y_score)
    score_hi=scoreHigh(y_score)

    # rules:
    # 1. HR is low, score low; HR is high, score high
    # 2. no-title-match is low, score high; no-ttile-match high, score low
    # 3. nwords is low, score low; nwords is high, score high
    # 4. meta-title-match is low, score low; meta-title-match high, score high
    # 5. y0 is low, score low; y0 is high, score high
    #gr_lines=[gr_lines[0], gr_lines[1]]

    for lii in gr_lines:
        if doctitle:
            tii,hii,y0ii,hrii,nwordsii,notitlefmii,metatitlefmii=lii
        else:
            tii,hii,y0ii,hrii,nwordsii,notitlefmii=lii

        act_hr_lo=hrLow(hrii)
        act_hr_hi=hrHigh(hrii)

        act_y0_lo=y0Low(y0ii)
        act_y0_hi=y0High(y0ii)

        act_notitle_lo=notitleFmLow(notitlefmii)
        act_notitle_hi=notitleFmHigh(notitlefmii)

        act_nwords_lo=nwordsLow(nwordsii)
        act_nwords_hi=nwordsHigh(nwordsii)


        # apply rules
        rule1a=np.fmin(act_hr_lo, score_lo)
        rule1b=np.fmin(act_hr_hi, score_hi)
        rule2a=np.fmin(act_notitle_lo, score_hi)
        rule2b=np.fmin(act_notitle_hi, score_lo)
        rule3a=np.fmin(act_nwords_lo, score_lo)
        rule3b=np.fmin(act_nwords_hi, score_hi)
        rule5a=np.fmin(act_y0_lo, score_lo)
        rule5b=np.fmin(act_y0_hi, score_hi)



        if doctitle:
            act_metatitle_lo=metaTitleFmLow(metatitlefmii)
            act_metatitle_hi=metaTitleFmHigh(metatitlefmii)
            rule4a=np.fmin(act_metatitle_lo, score_lo)
            rule4b=np.fmin(act_metatitle_hi, score_hi)

            #agg=reduce(np.fmax, [3*rule1a, 3*rule1b, rule2a, rule2b, rule3a, rule3b,
            agg=reduce(np.add, [rule1a, rule1b, rule2a, rule2b, rule3a, rule3b,
                rule5a, rule5b,
                rule4a, rule4b])
        else:
            #agg=reduce(np.fmax, [3*rule1a, 3*rule1b, rule2a, rule2b, rule3a, rule3b,
            agg=reduce(np.add, [rule1a, rule1b, rule2a, rule2b, rule3a, rule3b,
                rule5a, rule5b])

        '''
        print('---------------------------')
        print(tii)
        print('hrii', hrii, 'act_hr_lo', act_hr_lo, 'act_hr_hi', act_hr_hi)
        print('rule1a', rule1a)
        print('rule1b', rule1b)
        print('\n')
        print('y0ii',y0ii,'act_y0_lo', act_y0_lo, 'act_y0_hi', act_y0_hi)
        print('rule5a', rule5a)
        print('rule5b', rule5b)
        print('\n')
        print('notitlemf',notitlefmii,'act_notitle_lo',act_notitle_lo,'act_nottile_hi',act_notitle_hi)
        print('rule2a', rule2a)
        print('rule2b', rule2b)
        print('\n')
        print('nwords',nwordsii,'act_nwords_lo',act_nwords_lo,'act_nwords_hi',act_nwords_hi)
        print('rule3a',rule3a)
        print('rule3b',rule3b)
        print('\n')
        print('agg',agg)
        '''
        # compute centroid as final result
        yhat=(y_score*agg).sum()/agg.sum()

        fit=interp1d(y_score,agg,bounds_error=False, fill_value=0)
        xhat=fit(yhat)

        pprint('score for %s = %f, xhat = %f' %(tii, yhat, xhat))

        fuzz_scores.append(yhat)




    guess2=gr_lines[np.argmax(fuzz_scores)][0]

    guess=_checkLargetFontLine(lines)

    print('guessed title: %s' %guess)
    print('guessed title2: %s' %guess2)

    return guess


def kmeans2(xs,k):
    partitions=list(part(range(len(xs)),k))

    errors=[]
    for pii in partitions:
        eii=0
        for gjj in pii:
            xjj=np.take(xs,gjj)
            diffjj=np.diff(xjj) if len(xjj)>1 else 0
            #mjj=np.mean(xjj)
            #vjj=np.var(xjj)
            eii+=np.var(diffjj)
        errors.append(BIC(len(xs), k, eii))
        #errors.append(eii)

    idx=np.argmin(errors)

    return partitions[idx], errors[idx]

def BIC(n,lag,variance,verbose=True):

    if np.isscalar(lag):
        shape=1
    else:
        lag=np.asarray(lag)
        shape=lag.shape

    variance=np.asarray(variance)+0.1
    n=n*np.ones(shape)
    
    bic=n*np.log(variance*n/(n-lag))+\
            (lag+np.ones(shape))*np.log(n)

    if np.isscalar(lag):
        bic=np.asscalar(bic)

    return bic


def part(collection,k):

    edges=combinations(range(1,len(collection)),k-1)
    result=[]
    for eii in edges:
        eii=(0,)+eii+(len(collection),)
        rii=[]
        for jj in range(len(eii)-1):
            rii.append(collection[eii[jj]:eii[jj+1]])
        result.append(rii)

    return result














if __name__=='__main__':



    FILE_IN='mypdf9.pdf'

    guess=guessTitle2(FILE_IN)

