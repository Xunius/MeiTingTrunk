from collections import MutableMapping

class DocMeta(MutableMapping):

    def __init__(self, *args, **kwargs):
        self.store = {'read':False,
                'favourite':False}
        self.update(dict(*args, **kwargs))  # use the free update to set keys

    def __getitem__(self, key):
        if key=='citationkey':
            ck=self.store.get('citationkey','abcde')
            print(ck)
            return ck
        return self.store[key]

    def __setitem__(self, key, value):
        if not isinstance(key,str):
            raise Exception("accept only str type keys")
        if key.endswith('_l'):
            if not isinstance(value,(tuple,list)):
                raise Exception("keys end with '_l' accepts only list or tuple.")

        self.store[key] = value

    def __delitem__(self, key):
        del self.store[key]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __repr__(self):
        return self.store.__repr__()


fields=['id','citationkey','title','issue','pages',\
        'publication','volume','year','doi','abstract',\
        'arxivId','chapter','city','country','edition','institution',\
        'isbn','issn','month','day','publisher','series','type',\
        'read','favourite','pmid','added','confirmed']


dd=DocMeta()

for ii,ff in enumerate(fields):
    dd[ff]=ii

print(dd)
