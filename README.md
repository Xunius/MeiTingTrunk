# MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

## Features

### Libraries

* Create, manage and switch between multiple libraries.

### Folders

* Oragnize documents in a folder tree, with arbitrary level of folder nesting.
* Add a document to multiple folders without taking up duplicate storage.

### Import format

* Import via bibtex files.
* Import via RIS files.
* Import PDF files (currently with limited meta data fetching capability).
* Update meta data using DOI.

### Export format

* Export to bibtex.
* Export to RIS.
* Bulk export, per folder, or per document.

### Searching and filtering

* Filter document using authors, keywords, tags or publications.
* Search meta data within folders or library.
* Duplicate checking within folders or library.

### Note taking

* Jot down your thoughts while reading (currently with limited formating options).

### Database

* Meta data saved in sqlite format, transparent and easy to manipulate.
* library saved in a portable manner, backup or share using your prefered online/offline tools.

### Free and open source

* Open to suggestions, bug reports and new ideas.


## Screenshots

Main interface

![](https://user-images.githubusercontent.com/8076931/55284312-b651c700-53a6-11e9-9478-cb6ab8e89cf3.png)

Bulk export.

![](https://user-images.githubusercontent.com/8076931/55284318-d5e8ef80-53a6-11e9-9db9-560082253c2e.png)

Duplicate checking results.

![](https://user-images.githubusercontent.com/8076931/55284321-e4cfa200-53a6-11e9-8b6f-9e686d339acc.png)

Merge duplicates.

![](https://user-images.githubusercontent.com/8076931/55678909-5aea8080-5934-11e9-87bf-575fb99e3697.png)

Meta data searching.

![](https://user-images.githubusercontent.com/8076931/55284338-324c0f00-53a7-11e9-97a1-cd0e197ec012.png)

Actions on documents.

![](https://user-images.githubusercontent.com/8076931/55284334-23fdf300-53a7-11e9-9e34-01a1ae514a72.png)


## Platforms and Dependencies

Currently only tested in Linux.

* python3+
* PyQt5
* sqlite3
* pdfminer.six
* PyPDF2
* beautifulsoup4
* bibtexparser
* fuzzywuzzy
* crossrefapi
* RISparser
* send2trash

## Install

## install using pip


```
pip install meitingtrunk
```

Then launch it in the terminal with


```
$ meitingtrunk
```

## Manual install

You can clone this repo

```
git clone https://github.com/Xunius/MeiTingTrunk
```

and launch it with

```
$ cd MeiTingTrunk
$ python -m MeiTingTrunk.main
```

Check out the dependency list if any module is missing in your python environment.


## Contribution

This software is still in its very early stage. Please consider helping by trying it out, sending issues, suggestions, ideas or contributing code.

Major features that are still lacking (I greatly appreciate any help with any of them):

* Format citations into various citation styles, in a format suitable to paste into word editors.
* Full text searching inside PDFs.
* Import from Zotero and EndNote.
* Other document types aside articles and books.
* Packaging into a format suitable for a few mainstream Linux package management tools.
* Of cource, any stability or performance improvements.


A few ideas that I'd like to hear from your opinions:

* An embedded PDF viewer?
* A PDF preview tab?
* Markdown syntax support in the note tab?
* Custom fields design in the meta data tab?


## Licence

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
