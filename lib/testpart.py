
def partition(collection):
    if len(collection) == 1:
        yield [ collection ]
        return

    first = collection[0]
    for smaller in partition(collection[1:]):
        # insert `first` in each of the subpartition's subsets
        for n, subset in enumerate(smaller):
            yield smaller[:n] + [[ first ] + subset]  + smaller[n+1:]
        # put `first` in its own subset 
        yield [ [ first ] ] + smaller


something = list(range(1,10))

#for n, p in enumerate(partition(something), 1):
    #print(n, sorted(p))



from itertools import combinations
def part(collection,k):

    edges=combinations(range(1,len(collection)),k-1)
    print('edges',edges)

    result=[]
    for eii in edges:
        eii=(0,)+eii+(len(collection),)
        rii=[]
        for jj in range(len(eii)-1):
            rii.append(collection[eii[jj]:eii[jj+1]])
        result.append(rii)

    return result


    
aa=part(something,3)
for ii, pii in enumerate(aa):
    print(ii, pii)


