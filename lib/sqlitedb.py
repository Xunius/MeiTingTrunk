'''Sqlite database read and write functions.

Author: guangzhi XU (xugzhi1987@gmail.com; guangzhi.xu@outlook.com)
Update time: 2018-09-27 19:44:32.
'''


def readSqlite(dbin):

    #-------------------Get folders-------------------
    folder_dict=getFolders(dbin)

    #-------------------Get metadata-------------------
    meta={}
    query='''SELECT DISTINCT id
    FROM Documents
    '''
    docids=dbin.execute(query).fetchall()
    docids=[ii[0] for ii in docids]
    docids.sort()

    folder_data={}

    for idii in docids:
        metaii=getMetaData(dbin,idii)
        meta[idii]=metaii

        folderii=metaii['folders_l']
        # note: convert folder id to str
        # TODO: convert back to int when writing to sqlite
        folderids=[str(ff[0]) for ff in folderii]
        for fii in folderids:
            if fii in folder_data:
                folder_data[fii].append(idii)
            else:
                folder_data[fii]=[idii]

    #----------------Add empty folders----------------
    empty_folderids=list(set(folder_dict.keys()).difference(folder_data.keys()))
    for fii in empty_folderids:
        folder_data[fii]=[]

    return meta, folder_data, folder_dict


def getMetaData(db, docid):
    '''Get meta-data of a doc by docid.
    '''

    # fetch column from Document table
    query_base=\
    '''SELECT Documents.%s
       FROM Documents
       WHERE (Documents.id=?)
    '''

    query_tags=\
    '''
    SELECT DocumentTags.tag
    FROM DocumentTags
    WHERE (DocumentTags.docid=?)
    '''

    query_firstnames=\
    '''
    SELECT DocumentContributors.firstNames
    FROM DocumentContributors
    WHERE (DocumentContributors.docid=?)
    '''

    query_lastnames=\
    '''
    SELECT DocumentContributors.lastName
    FROM DocumentContributors
    WHERE (DocumentContributors.docid=?)
    '''

    query_keywords=\
    '''
    SELECT DocumentKeywords.text
    FROM DocumentKeywords
    WHERE (DocumentKeywords.docid=?)
    '''

    query_folder=\
    '''
    SELECT Folders.id, Folders.name
    FROM Folders
    LEFT JOIN DocumentFolders ON DocumentFolders.folderid=Folders.id
    WHERE (DocumentFolders.docid=?)
    '''

    query_files=\
    '''
    SELECT DocumentFiles.abspath
    FROM DocumentFiles
    WHERE (DocumentFiles.docid=?)
    '''


    '''
    def fetchField(db,query,values,ncol=1):
        aa=db.execute(query,values).fetchall()
        if len(aa)==0:
            return None
        if ncol==1:
            aa=[ii[0] for ii in aa]
        if len(aa)==1:
            return aa[0]
        else:
            return aa
    '''

    def fetchField(db,query,values,ncol=1,ret_type='str'):
        if ret_type not in ['str','list']:
            raise Exception("<ret_type> is one of ['str','list'].")

        aa=db.execute(query,values).fetchall()

        if len(aa)==0:
            if ret_type=='str':
                return None
            else:
                return []

        if ncol==1:
            aa=[ii[0] for ii in aa]
        if ret_type=='str':
            if len(aa)==1:
                return aa[0]
            else:
                return '; '.join(aa)
        else:
            return aa

    #------------------Get file meta data------------------
    fields=['id','citationkey','title','issue','pages',\
            'publication','volume','year','doi','abstract',\
            'arxivId','chapter','city','country','edition','institution',\
            'isbn','issn','month','day','publisher','series','type',\
            'read','favourite','pmid','added','confirmed']

    result={}

    # query single-worded fields, e.g. year, city
    for kii in fields:
        vii=fetchField(db,query_base %(kii), (docid,))
        result[kii]=vii

    # query list fields, .e.g firstnames, tags
    result['firstNames_l']=fetchField(db,query_firstnames,(docid,),1,'list')
    result['lastName_l']=fetchField(db,query_lastnames,(docid,),1,'list')
    result['keywords_l']=fetchField(db,query_keywords,(docid,),1,'list')
    result['files_l']=fetchField(db,query_files,(docid,),1,'list')
    result['folders_l']=fetchField(db,query_folder,(docid,),2,'list')
    result['tags_l']=fetchField(db,query_tags,(docid,),1,'list')

    #if '' in result['firstNames_l']:
        #__import__('pdb').set_trace()
    #if '' in result['lastName_l']:
        #__import__('pdb').set_trace()

    folders=result['folders_l']
    result['folders_l']=folders or [(-1, 'Canonical')] # if no folder name, a canonical doc

    first=result['firstNames_l']
    last=result['lastName_l']
    #authors=['%s, %s' %(ii[0],ii[1]) for ii in zip(last,first)]
    #result['authors_l']=authors
    result['authors_l']=zipAuthors(first,last)

    result['has_file']=False if len(result['files_l'])==0 else True


    return result


def zipAuthors(firstnames,lastnames):
    if len(firstnames)!=len(lastnames):
        print('zipAuthors')
        print('firstnames',firstnames)
        print('lastnames',lastnames)
        raise Exception("Exception")
    authors=[]
    for ii in range(len(firstnames)):
        fii=firstnames[ii]
        lii=lastnames[ii]
        if fii!='' and lii!='':
            authors.append('%s, %s' %(lii,fii))
        elif fii=='' and lii!='':
            authors.append(lii)
        elif fii!='' and lii=='':
            authors.append(fii)

    return authors




def getFolders(db):

    #-----------------Get all folders-----------------
    query='''SELECT id, name, parentId
    FROM Folders
    '''
    ret=db.execute(query)
    data=ret.fetchall()

    # dict, key: folderid, value: (folder_name, parent_id)
    # note: convert id to str
    df=dict([(str(ii[0]), (ii[1], str(ii[2]))) for ii in data])

    return df

def fetchMetaData(meta_dict,key,docids,unique,sort):
    if not isinstance(docids, (tuple,list)):
        docids=[docids,]

    result=[]
    for idii in docids:
        vv=meta_dict[idii].get(key,None)
        # NOTE: don't use if vv:
        # as there are '' entries that will also trigger the if
        if vv is not None:
            if isinstance(vv, (tuple,list)):
                result.extend(vv)
            else:
                result.append(vv)

    if unique:
        result=list(set(result))
    if sort:
        result.sort()

    return result


def getAuthors(meta_dict,docids):
    if not isinstance(docids, (tuple,list)):
        docids=[docids,]

    result=[]
    fs=[]
    ls=[]
    for idii in docids:
        firsts=meta_dict[idii].get('firstNames',None)
        lasts=meta_dict[idii].get('lastName',None)
        
        if firsts is None or lasts is None:
            __import__('pdb').set_trace()

        if isinstance(firsts, (tuple,list)) and not isinstance(lasts,(tuple,list)):
            __import__('pdb').set_trace()

        if not isinstance(firsts, (tuple,list)) and isinstance(lasts,(tuple,list)):
            __import__('pdb').set_trace()
        if firsts=='':
            __import__('pdb').set_trace()
        if isinstance(firsts, (tuple,list)) and isinstance(lasts,(tuple,list)):
            fs.extend(firsts)
            ls.extend(lasts)
            #result.extend(vv)
        else:
            #result.append(vv)
            fs.append(firsts)
            ls.append(lasts)

        if len(fs)!=len(ls):
            __import__('pdb').set_trace()

    result=['%s, %s' %(ls[ii],fs[ii]) for ii in range(len(fs))]

    aa=fetchMetaData(meta_dict,'firstNames',docids,
            unique=False,sort=False)
    bb=fetchMetaData(meta_dict,'lastName',docids,
            unique=False,sort=False)

    return result

def filterDocs(meta_dict,folder_data,filter_type,filter_text,current_folder):

    results=[]
    if current_folder=='0':
        docids=meta_dict.keys()
    else:
        docids=folder_data[current_folder]

    print('docids',docids)

    if filter_type=='Filter by authors':
        t_last,t_first=map(str.strip,filter_text.split(','))
        print('t_last: %s, t_first: %s, text: %s' %(t_last,t_first,filter_text))
        for kk in docids:
            authors=meta_dict[kk]['authors_l']
            if filter_text in authors:
                results.append(kk)

    elif filter_type=='Filter by tags':
        for kk in docids:
            tags=meta_dict[kk]['tags_l'] or []
            if filter_text in tags:
                results.append(kk)

    elif filter_type=='Filter by publications':
        for kk in docids:
            pubs=meta_dict[kk]['publication'] or []
            if filter_text in pubs:
                results.append(kk)

    elif filter_type=='Filter by keywords':
        for kk in docids:
            keywords=meta_dict[kk]['keywords_l'] or []
            if filter_text in keywords:
                results.append(kk)

    print(results)

    return results





#--------------Get folder id and name list in database----------------
def getFolderList(db,folder,verbose=True):
    '''Get folder id and name list in database

    <folder>: select folder from database.
              If None, select all folders/subfolders.
              If str, select folder <folder>, and all subfolders. If folder
              name conflicts, select the one with higher level.
              If a tuple of (id, folder), select folder with name <folder>
              and folder id <id>, to avoid name conflicts.

    Return: <folders>: list, with elements of (id, folder_tree).
            where <folder_tree> is a str of folder name with tree structure, e.g.
            test/testsub/testsub2.

    Update time: 2016-06-16 19:38:15.
    '''

    # get all folders with id, name, parentid
    query=\
    '''SELECT Folders.id,
              Folders.name,
              Folders.parentID
       FROM Folders
    '''
    # get folder by name
    query1=\
    '''SELECT Folders.id,
              Folders.name,
              Folders.parentID
       FROM Folders
       WHERE (Folders.name="%s")
    '''%folder

    #-----------------Get all folders-----------------
    ret=db.execute(query)
    data=ret.fetchall()

    # dict, key: folderid, value: (folder_name, parent_id)
    df=dict([(ii[0],ii[1:]) for ii in data])

    allfolderids=[ii[0] for ii in data]

    #---------------Select target folder---------------
    if folder is None:
        folderids=allfolderids
    if type(folder) is str:
        folderids=db.execute(query1).fetchall()
        folderids=[ii[0] for ii in folderids]
    elif isinstance(folder, (tuple,list)):
        # get folder from gui
        #seldf=df[(df.folderid==folder[0]) & (df.folder==folder[1])]
        #folderids=fetchField(seldf,'folderid')
        folderids=[folder[0]]

    #----------------Get all subfolders----------------
    if folder is not None:
        folderids2=[]
        for ff in folderids:
            folderids2.append(ff)
            subfs=getSubFolders(df,ff)
            folderids2.extend(subfs)
    else:
        folderids2=folderids

    #---------------Remove empty folders---------------
    folderids2=[ff for ff in folderids2 if not isFolderEmpty(db,ff)]

    #---Get names and tree structure of all non-empty folders---
    folders=[]
    for ff in folderids2:
        folders.append(getFolderTree(df,ff))

    #----------------------Return----------------------
    if folder is None:
        return folders
    else:
        if len(folders)==0:
            print("Given folder name not found in database or folder is empty.")
            return []
        else:
            return folders


#--------------------Check a folder is empty or not--------------------
def isFolderEmpty(db,folderid,verbose=True):
    '''Check a folder is empty or not
    '''

    query=\
    '''SELECT Documents.title,
              DocumentFolders.folderid,
              Folders.name
       FROM Documents
       LEFT JOIN DocumentFolders
           ON Documents.id=DocumentFolders.documentId
       LEFT JOIN Folders
           ON Folders.id=DocumentFolders.folderid
    '''

    fstr='(Folders.id="%s")' %folderid
    fstr='WHERE '+fstr
    query=query+' '+fstr

    ret=db.execute(query)
    data=ret.fetchall()
    if len(data)==0:
        return True
    else:
        return False

#-------------------Get subfolders of a given folder-------------------
def getChildFolders(df,folderid,verbose=True):
    '''Get subfolders of a given folder

    <df>: dict, key: folderid, value: (folder_name, parent_id).
    <folderid>: int, folder id
    '''
    results=[]
    for idii in df:
        fii,pii=df[idii]
        if pii==folderid:
            results.append(idii)
    results.sort()
    return results

#-------------------Get subfolders of a given folder-------------------
def getSubFolders(df,folderid,verbose=True):
    '''Get subfolders of a given folder

    <df>: dict, key: folderid, value: (folder_name, parent_id).
    <folderid>: int, folder id
    '''

    getParentId=lambda df,id: df[id][1]
    results=[]

    for idii in df:
        fii,pii=df[idii]
        cid=idii
        while True:
            pid=getParentId(df,cid)
            if pid==-1 or pid==0:
                break
            if pid==folderid:
                results.append(idii)
                break
            else:
                cid=pid

    results.sort()
    return results

#-------------Get folder tree structure of a given folder-------------
def getFolderTree(df,folderid,verbose=True):
    '''Get folder tree structure of a given folder

    <df>: dict, key: folderid, value: (folder_name, parent_id).
    <folderid>: int, folder id
    '''

    getFolderName=lambda df,id: df[id][0]
    getParentId=lambda df,id: df[id][1]

    folder=getFolderName(df,folderid)

    #------------Back track tree structure------------
    cid=folderid
    while True:
        pid=getParentId(df,cid)
        if pid==-1 or pid==0:
            break
        else:
            pfolder=getFolderName(df,pid)
            folder=u'%s/%s' %(pfolder,folder)
        cid=pid

    return folderid,folder


#----------Get a list of docids from a folder--------------
def getFolderDocList(db,folderid,verbose=True):
    '''Get a list of docids from a folder

    Update time: 2018-07-28 20:11:09.
    '''

    query=\
    '''SELECT Documents.id
       FROM Documents
       LEFT JOIN DocumentFolders
           ON Documents.id=DocumentFolders.documentId
       WHERE (DocumentFolders.folderid=%s)
    ''' %folderid

    ret=db.execute(query)
    data=ret.fetchall()
    docids=[ii[0] for ii in data]
    docids.sort()
    return docids



