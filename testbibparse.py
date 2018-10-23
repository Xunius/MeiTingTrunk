import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import *
import os


def readBibFile(bibfile):

    bibfile=os.path.abspath(bibfile)
    if not os.path.exists(bibfile):
        return None

    with open(bibfile,'r') as fin:
        bib=bibtexparser.load(fin)
        print('bib',bib)

    entries=bib.entries

    return entries


def customizations(record):
    """Use some functions delivered by the library

    :param record: a record
    :returns: -- customized record
    """
    record = type(record)
    record = author(record)
    #record = editor(record)
    #record = journal(record)
    record = keyword(record)
    record = link(record)
    record = page_double_hyphen(record)
    record = doi(record)
    return record


aa=readBibFile('test.bib')
print(aa)

parser=BibTexParser()
parser.homogenize_fields=True
parser.customization=customizations

with open('test.bib', 'r') as fin:
    bibstr=fin.read()

print(bibstr)

bibs=bibtexparser.loads(bibstr,parser)
print('---------')
