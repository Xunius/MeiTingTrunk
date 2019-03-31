# MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

## Features

### Libraries

* Create, manage and switch between multiple libraries.

### Folders

* Oragnize documents in a folder tree, with arbirary level of folder nesting.
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

Main interface.

Bulk export.

Duplicate checking results.

Meta data searching.

Actions on documents.


## Platforms and Dependencies

Currently only tested in Linux.

* python3+
* PyQt5
* pdfminer
* PyPDF2
* beautifulsoup4
* bibtexparser
* fuzzywuzzy
* crossrefapi
* RISparser


## Contribution

This software is still in its very early stage. Please consider helping
by trying it out, sending issues, suggestions, ideas or contributing code.

Major features that are still lacking (I greatly appreciate any help with
any of them):

* Format citations into various citation styles, in a format suitable to paste into word
editors.
* Full text searching inside PDFs.
* Import from Zotero and EndNote.
* Other document types aside articles and books.
* Packaing into a format suitable for a few mainstream Linux software management tools.
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
