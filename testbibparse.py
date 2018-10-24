import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser import customization as bibcus
import os


def customizations(record):
    """Use some functions delivered by the library

    :param record: a record
    :returns: -- customized record
    """
    record = bibcus.type(record)
    record = bibcus.author(record)
    #record = bibcus.editor(record)
    #record = bibcus.journal(record)
    record = bibcus.keyword(record)
    record = bibcus.link(record)
    record = bibcus.page_double_hyphen(record)
    record = bibcus.doi(record)
    return record


def readBibFile(bibfile):

    bibfile=os.path.abspath(bibfile)
    if not os.path.exists(bibfile):
        return None

    with open(bibfile,'r') as fin:
        parser=BibTexParser()
        parser.homogenize_fields=True
        parser.customization=customizations

        bib=bibtexparser.load(fin,parser=parser)
        print('bib',bib)

    entries=bib.entries
    entries=[splitNames(eii) for eii in entries]

    return entries


def splitNames(entry):

    firstnames=[]
    lastnames=[]
    for nii in entry['author']:
        lii,fii=nii.split(',',1)
        firstnames.append(fii)
        lastnames.append(lii)

    entry['firstNames_l']=firstnames
    entry['lastName_l']=lastnames

    return entry


aa=readBibFile('test.bib')
print(aa[0])

