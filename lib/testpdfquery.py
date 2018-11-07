from functools import reduce
import re
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

from simpleFC import FCUp, FCDown, FCTria, FCTrap, FCInvTria, FCInvTrap



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




def kmeans(xs,k):
    '''A simple k-means clustering

    <xs>: 1d array to cluster
    <k>: int, number of clusters
    '''
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
    '''Compute the Bayesian Information Criteria
    Not rigorously correct. Used to determine an optimal kmeans clustering
    '''

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
    '''Partition a list into k groups keeping elements' order
    '''

    edges=combinations(range(1,len(collection)),k-1)
    result=[]
    for eii in edges:
        eii=(0,)+eii+(len(collection),)
        rii=[]
        for jj in range(len(eii)-1):
            rii.append(collection[eii[jj]:eii[jj+1]])
        result.append(rii)

    return result




#------------------------Initiate analysis objs------------------------
def init(filename):
    '''Initiate analysis objs
    '''

    fin=open(filename, 'rb')
    # Create a PDF parser object associated with the file object.
    parser = PDFParser(fin)
    document = PDFDocument(parser)

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
    '''Sort objs vertically by y coordinates
    '''

    objdict={}
    for ii in objs:
        objdict[-ii.bbox[3],ii.bbox[0]]=ii

    keys=objdict.keys()
    keys=sorted(keys)

    result=[objdict[ii] for ii in keys]

    return result



def getLineHeight(lineobj,return_type='mean'):
    '''Use the mean char heights as a line obj's height'''
    heights=[]
    for ii in lineobj._objs:
        if hasattr(ii,'height'):
            heights.append(ii.height)
    if return_type=='mean':
        return np.mean(heights)
    elif return_type=='set':
        return set(heights)


def groupLines(line_dict, main_height):

    heights=list(set(line_dict.values()))
    heights.sort(reverse=True)

    groups=[]
    for hii in heights:
        # dont bother lines smaller than main text height
        if hii<=main_height:
            break

        # get lines at current height, sort by y coords
        lsii=[kk for kk,vv in line_dict.items() if vv==hii]
        lsii=sortY(lsii)

        if len(lsii)==1:
            groups.append(lsii)

        elif len(lsii)==2:
            # if only 2 lines, seperate only if gap larger than their own height
            if lsii[0].vdistance(lsii[1])>lsii[0].height:
                groups.append([lsii[0]])
                groups.append([lsii[1]])
            else:
                groups.append(lsii)

        elif len(lsii)>2:
            ysii=[round(ljj.y0,1) for ljj in lsii]
            gapsii=[round(ysii[jj]-ysii[jj+1],1) for jj in range(len(ysii)-1)]

            if len(set(gapsii))==1:
                # if > 2 lines by all seperated by same gap, treat as single
                # block
                groups.append(lsii)
            else:
                # if >= 2 gaps, do a kmeans to group them, using their y0 coords
                costs=[]
                groupingii=[]
                for jj in range(1,len(ysii)):
                    grjj,costjj=kmeans(ysii,jj)
                    costs.append(costjj)
                    groupingii.append(grjj)

                idx=np.argmin(costs)
                for kk in groupingii[idx]:
                    groups.append([lsii[mm] for mm in kk])

    groups2=[]
    for gii in groups:
        gii=sortY(gii)
        groups2.append(gii)

    return groups2




def FCTitleGuess(line_data, doctitle, verbose=False):

    #x_hr=np.arange(0,5)
    #x_y0=np.arange(0,1.1,0.1)
    #x_nottile_fm=np.arange(0,101)
    #x_nwords=np.arange(1,70)
    #x_metatitle_fm=np.arange(0,101)

    y_score=np.arange(0,101)

    hrLow=partial(FCInvTrap, 0, 1.2, 4, 5)
    hrHigh=partial(FCTria, 1.1, 3.0, 4.5)

    y0Low=partial(FCTria, 0.4, 0.5, 1)
    y0High=partial(FCTria, 0.5, 0.7, 1.2)

    notitleFmLow=partial(FCDown, 0, 55)
    notitleFmHigh=partial(FCUp, 45, 100)

    nwordsLow=partial(FCInvTrap, 1, 5, 30, 70)
    nwordsHigh=partial(FCTrap, 4, 8, 20, 35)

    metaTitleFmLow=partial(FCDown, 0, 70)
    metaTitleFmHigh=partial(FCUp, 30, 100)

    scoreLow=partial(FCDown,0,60)
    scoreHigh=partial(FCUp,40,100)

    fuzz_scores=[]
    score_lo=scoreLow(y_score)
    score_hi=scoreHigh(y_score)

    # rules:
    # 1. HR is low, score low; HR is high, score high
    # 2. no-title-match is low, score high; no-ttile-match high, score low
    # 3. nwords is low, score low; nwords is high, score high
    # 4. meta-title-match is low, score low; meta-title-match high, score high
    # 5. y0 is low, score low; y0 is high, score high

    for lii in line_data:
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

        # compute centroid as final result
        yhat=(y_score*agg).sum()/agg.sum()
        #fit=interp1d(y_score,agg,bounds_error=False, fill_value=0)
        #xhat=fit(yhat)

        if verbose:
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

            print('score for %s = %f' %(tii, yhat))

        fuzz_scores.append(yhat)

    return fuzz_scores



def guessTitle(pdffile):

    document, interpreter, device=init(FILE_IN)

    #------------Fetch title from meta data------------
    docinfo=document.info[0]
    doctitle=docinfo.get('Title',None)
    if doctitle:
        doctitle=doctitle.decode('utf-8')

    #--------------------Get page 1--------------------
    for ii,page in enumerate(PDFPage.create_pages(document)):
        if ii>0:
            break
        interpreter.process_page(page)
        p0 = device.get_result()

    page_h=p0.height
    p0_objs=p0._objs

    boxes=[objii for objii in p0_objs if isinstance(objii, LTTextBoxHorizontal)]

    #------------------Get lines------------------
    lines=[]
    for bii in boxes:
        lines.extend(bii._objs)

    # get all line heights
    heights=[round(getLineHeight(lii),4) for lii in lines]

    # most common height should be main text height
    h_counter=Counter(heights)
    main_height=h_counter.most_common()[0][0]

    # get lines in the top half of the page
    line_dict=dict([(lii,round(getLineHeight(lii),4)) for lii in lines if\
            lii.y0>=page_h//2])

    heights=list(set(line_dict.values()))
    heights.sort(reverse=True)

    #-------------Group lines by heights and y0-------------
    groups=groupLines(line_dict, main_height)

    #-Get texts and prepare data for fuzzy logic check-
    gr_lines=[]

    for gii in groups:
        tii=[ljj.get_text().strip() for ljj in gii]
        tii=' '.join(tii)
        hii=[getLineHeight(ljj) for ljj in gii]
        hii=np.mean(hii)

        # compute input vars for fuzzy
        # height ratio wrt main text height
        hrii=hii/main_height
        # lowest y0
        y0ii=[ljj.y0 for ljj in gii]
        y0ii=np.min(y0ii)/page_h
        # number of words
        nwordsii=len(tii.split(' '))
        # similartiy measure between a predefined list of non-title words
        notitlefmii=[fuzz.token_set_ratio(tii,jj) for jj in NON_TITLE_LIST]
        notitlefmii=np.mean(notitlefmii)

        # similarity measure between title obtained from meta data
        if doctitle:
            metatitlefmii=fuzz.ratio(tii, doctitle)
            gr_lines.append((tii,hii,y0ii,hrii,nwordsii,notitlefmii,metatitlefmii))
        else:
            gr_lines.append((tii,hii,y0ii,hrii,nwordsii,notitlefmii))

    #pprint(gr_lines)

    #----------------Do fuzzy logic----------------
    fuzz_scores=FCTitleGuess(gr_lines, doctitle)

    title_idx=np.argmax(fuzz_scores)
    title_guess=gr_lines[title_idx]
    title_y0=title_guess[2]*page_h
    title_x0=groups[title_idx][0].x0

    #----------------Guess author list----------------
    top_lines=line_dict.keys()
    top_lines=sortY(top_lines)

    authorline_list=[]

    def getLineFonts(lineobj):
        fonts=[]
        for ii in lineobj._objs:
            if hasattr(ii,'fontname'):
                fonts.append(ii.fontname)
        counter=Counter(fonts)
        main_font=counter.most_common()[0][0]

        return main_font

    def getLineY0(lineobj):
        y0s=[]
        for ii in lineobj._objs:
            y0s.append(ii.bbox[1])
        counter=Counter(y0s)
        main=counter.most_common()[0][0]

        return main

    for ii,lii in enumerate(top_lines):
        if lii.y0>=title_y0:
            print('skip line',lii,'y0 = ',lii.y0)
            continue

        if lii.x0<title_x0:
            print('skip line',lii,'x0 = ',lii.x0)
            continue

        if len(authorline_list)==0:
            authorline_list.append(lii)
        else:
            old_font=getLineFonts(authorline_list[0])
            cur_font=getLineFonts(lii)

            old_height=getLineHeight(authorline_list[0],'set')
            cur_height=getLineHeight(lii,'set')

            print('old_font:',old_font, 'new_font', cur_font)
            print('old_height:',old_height, 'new_height', cur_height)

            if cur_font!=old_font:
                break
            if old_height!=cur_height:
                break

            authorline_list.append(lii)

    #-----------------Get author texts-----------------
    author_texts=[]
    char_heights=[]

    for lii in authorline_list:
        charsii=lii._objs
        #char_y0s=[]
        liney0ii=round(lii.bbox[1],1)
        linehii=getLineHeight(lii)

        for cjj in charsii:
            if hasattr(cjj,'bbox'):
                if round(cjj.bbox[1],1)-liney0ii>=linehii/4:
                    continue
            author_texts.append(cjj.get_text())
            '''
            author_texts.append(cjj.get_text())
            if hasattr(cjj,'size'):
                char_heights.append(round(cjj.size,1))
            else:
                char_heights.append(0)
            char_y0s.append(cjj.bbox[1])
            '''

    #char_counter=Counter(char_heights)
    #char_height=char_counter.most_common()[0][0] # or the largest?

    #author_texts2=[]

    #for ii,sii in enumerate(char_heights):
        #if sii==char_height or sii==0:
            #author_texts2.append(author_texts[ii])

    author_texts2=''.join(author_texts)



    #------------------Tidy up string------------------
    sc_pattern=re.compile(r'\s+,')
    and_pattern=re.compile(r',?\s+and\s+', re.I)
    weird_pattern=re.compile(r'''[~!@#$%^&*()_+`\-=\[\]{}|;:'"<>/?]''')

    author_texts2=sc_pattern.sub(',',author_texts2).strip()
    author_texts2=and_pattern.sub(', ',author_texts2).strip()
    author_texts2=weird_pattern.sub('',author_texts2).strip()
    
    print('guess authors:', author_texts2)



    return title_guess














if __name__=='__main__':



    FILE_IN='mypdf9.pdf'

    guess=guessTitle(FILE_IN)
    print('guessed title: ', guess)
