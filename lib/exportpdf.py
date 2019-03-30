'''
Export PDFs with annotations. This is used in importing Mendeley data.


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2019 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
'''

import os
import PyPDF2
from . import pdfannotation
import logging

LOGGER=logging.getLogger(__name__)


def exportPdf(fin, abpath_out, annotations):
    '''Export PDF with annotations.

    Args:
        fin (str): abspath to input PDF file.
        abpath_out (str): abspath to output PDF file.
        annotations (dict): annotation info. See import_mendeley.py
                            getHighlights() for more info.
    '''

    try:
        inpdf = PyPDF2.PdfFileReader(open(fin, 'rb'))
        if inpdf.isEncrypted:
            # PyPDF2 seems to think some files are encrypted even
            # if they are not. We just ignore the encryption.
            # This seems to work for the one file where I saw this issue
            #inpdf._override_encryption = True
            #inpdf._flatten()
            # UPDATE: trying to decrypt takes a lot of time,
            # as this rarely happens to academic docs I'm skipping this
            # and simply treat as fail
            #raise Exception("Skip encrypt")
            return
    except IOError:
        LOGGER.warning('Could not open pdf file %s' %fin)

    # retain meta data
    meta = inpdf.getDocumentInfo()
    outpdf = PyPDF2.PdfFileWriter()
    outpdf.addMetadata(meta)

    highlights=annotations.get('highlights',None)
    if highlights is None:
        hlpages=[]
    else:
        hlpages=list(highlights.keys())
        hlpages.sort()

    notes=annotations.get('notes',None)
    if notes is None:
        ntpages=[]
    else:
        ntpages=list(notes.keys())
        ntpages.sort()

    #----------------Loop through pages----------------
    pages=range(1,inpdf.getNumPages()+1)

    for pii in pages:
        inpg = inpdf.getPage(pii-1)

        #----------------Process highlights----------------
        if pii in hlpages:
            for hjj in highlights[pii]:
                # Changes suggested by matteosecli: add author of highlight:
                anno = pdfannotation.createHighlight(hjj["rect"],
                        author=hjj['author'],
                        cdate=hjj["cdate"], color=hjj['color'])
                inpg=pdfannotation.addAnnotation(inpg,outpdf,anno)

        #------------------Process notes------------------
        if pii in ntpages:
            for njj in notes[pii]:
                note = pdfannotation.createNote(njj["rect"], \
                        contents=njj["content"], author=njj["author"],\
                        cdate=njj["cdate"])
                inpg=pdfannotation.addAnnotation(inpg,outpdf,note)

        outpdf.addPage(inpg)

    #-----------------------Save-----------------------
    if os.path.isfile(abpath_out):
        os.remove(abpath_out)

    with open(abpath_out, mode='wb') as fout:
        outpdf.write(fout)

    LOGGER.debug('Exported annotated pdf.')

    return

