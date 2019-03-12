import six
import pybtex.database.input.bibtex
import pybtex.plugin



if __name__=='__main__':


    filename='test.bib'
    with open(filename,'r') as fin:
        strings=fin.readlines()

    strings=''.join(strings)

    print(strings)

    style = pybtex.plugin.find_plugin('pybtex.style.formatting', 'plain')()
    backend = pybtex.plugin.find_plugin('pybtex.backends', 'docutils')()
    parser = pybtex.database.input.bibtex.Parser()
    #data = parser.parse_stream(six.StringIO(u"""
    data = parser.parse_stream(six.StringIO(strings))
    '''
    @Book{1985:lindley,
      author =    {D. Lindley},
      title =     {Making Decisions},
      publisher = {Wiley},
      year =      {1985},
      edition =   {2nd},
    }
    """))
    '''
    entries=style.format_entries(six.itervalues(data.entries))
    for entry in entries:
        print(backend.paragraph(entry))

