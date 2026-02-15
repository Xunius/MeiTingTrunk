"""
DOI query.


MeiTing Trunk
An open source reference management tool developed in PyQt5 and Python3.

Copyright 2018-2026 Guang-zhi XU

This file is distributed under the terms of the
GPLv3 licence. See the LICENSE file for details.
You may use, distribute and modify this code under the
terms of the GPLv3 license.
"""

from datetime import datetime
import logging
import re
import requests
import xml.etree.ElementTree as ET

from crossref.restful import Works, Etiquette
from PyQt5 import QtWidgets
from PyQt5.QtCore import QTemporaryFile, QDir
from PyQt5.QtCore import Qt

try:
    from . import sqlitedb
except Exception:
    import sqlitedb

__version__ = "v0.2"


ETIQUETTE = Etiquette("MeiTing-Trunk", __version__,
                      "github", "xugzhi1987@gmail.com")

LOGGER = logging.getLogger(__name__)

# doi_pattern = re.compile(
# r"(?:doi:)?\s?(10.[1-9][0-9]{3}/.*$)", re.DOTALL | re.UNICODE
# )

# Updated regex to match both regular DOIs and arXiv URLs
_DOI_PATTERN = re.compile(
    # Regular DOI pattern with optional URL prefix
    r"(?:(?:https?://doi\.org/|doi:)?\s?(10\.[1-9][0-9]{3,}/.*$)|"
    # arXiv URL
    r"(?:https?://)?arxiv\.org/abs/([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?$))",
    re.DOTALL | re.UNICODE
)
# matches these formats:
# Regular DOIs: 10.1234/some.doi
# With prefix: doi:10.1234/some.doi
# arXiv DOIs: 10.48550/arXiv.2301.12345
# DOI URLs: https://doi.org/10.48550/arXiv.2306.08632
# arXiv URLs: https://arxiv.org/abs/2306.08632
# Without https: arxiv.org/abs/2306.08632

#
def strip_tags(text):
    """Remove XML/HTML tags like <jats:title>, <b>, etc. from text

    Args:
        text (str): text with tags

    Returns:
        str: text with all tags removed
    """
    if not text:
        return text

    # Remove all tags (including namespaced ones like <jats:title>)
    return re.sub(r'<[^>]+>', '', text)


def normalize_to_doi(input_string):
    """
    Convert various input formats to standard DOI format.

    Handles:
    - Regular DOIs: '10.1234/xyz'
    - DOIs with prefix: 'doi:10.1234/xyz'
    - arXiv URLs: 'https://arxiv.org/abs/2306.08632'
    - arXiv DOIs: '10.48550/arXiv.2306.08632'

    Returns:
        Normalized DOI string
    """
    input_string = input_string.strip()

    # Check if it's an arXiv URL
    arxiv_url_pattern = re.compile(
        r"(?:https?://)?arxiv\.org/abs/([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)")
    match = arxiv_url_pattern.search(input_string)
    if match:
        arxiv_id = match.group(1)
        # Remove version suffix if present (e.g., 'v1', 'v2')
        arxiv_id = re.sub(r'v[0-9]+$', '', arxiv_id)
        return f"10.48550/arXiv.{arxiv_id}"

    # Remove 'doi:' prefix if present
    if input_string.lower().startswith('doi:'):
        input_string = input_string[4:].strip()

    # Remove URL prefix if present
    if 'doi.org/' in input_string:
        input_string = input_string.split('doi.org/')[-1]

    return input_string


def fetchMetaByDOI_arxiv(doi):
    """Fetch metadata for an arXiv DOI and return in crossrefapi-like format.

    Args:
        doi: arXiv DOI string (e.g., '10.48550/arXiv.2301.12345')

    Returns:
        Dictionary in crossrefapi format
    """

    # Normalize input to DOI format
    doi = normalize_to_doi(doi)
    LOGGER.info(f'normalized doi: {doi}')

    # Extract arXiv ID from DOI
    if 'arxiv' not in doi.lower():
        raise ValueError("Not an arXiv DOI")

    # Extract arXiv ID (e.g., '2301.12345' from '10.48550/arXiv.2301.12345')
    arxiv_id = doi.split('arXiv.')[-1]
    LOGGER.info(f'arxiv_id: {arxiv_id}')

    # Query arXiv API
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    LOGGER.info(f'url: {url}')
    response = requests.get(url)
    response.raise_for_status()

    # Parse XML
    root = ET.fromstring(response.content)
    ns = {'atom': 'http://www.w3.org/2005/Atom',
          'arxiv': 'http://arxiv.org/schemas/atom'}

    entry = root.find('atom:entry', ns)
    if entry is None:
        raise ValueError(f"No arXiv entry found for {arxiv_id}")
    LOGGER.info(f'entry: {entry}')

    # Extract metadata
    title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
    LOGGER.info(f'title: {title}')

    # Authors
    authors = []
    for author in entry.findall('atom:author', ns):
        name = author.find('atom:name', ns).text
        # Split name into given and family names (best effort)
        parts = name.split()
        if len(parts) >= 2:
            authors.append({
                'given': ' '.join(parts[:-1]),
                'family': parts[-1],
                'sequence': 'first' if len(authors) == 0 else 'additional'
            })
        else:
            authors.append({
                'family': name,
                'sequence': 'first' if len(authors) == 0 else 'additional'
            })

    # Published date
    published = entry.find('atom:published', ns).text
    pub_date = datetime.fromisoformat(published.replace('Z', '+00:00'))

    # Abstract
    abstract = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')

    # Categories
    categories = [cat.get('term')
                  for cat in entry.findall('atom:category', ns)]
    primary_category = entry.find('arxiv:primary_category', ns)
    primary_cat = primary_category.get(
        'term') if primary_category is not None else None

    # Format in crossrefapi style
    metadata = {
        'doi': doi,
        'type': 'posted-content',
        'subtype': 'preprint',
        'title': [title],
        'author': authors,
        'abstract': abstract,
        'year': pub_date.year,
        'month': pub_date.month,
        'day': pub_date.day,
        'published-online': f'{pub_date.year}-{pub_date.month}-{pub_date.day}',
        'institution': 'arXiv',
        'publication': 'arXiv',
        'url': f"https://arxiv.org/abs/{arxiv_id}",
        'subject': categories,
        'primary-subject': primary_cat,
        'arxivId': arxiv_id
    }

    LOGGER.info(f'metadata: {metadata}')

    return metadata


def fetchMetaByDOI_crossref(doi):
    works = Works(etiquette=ETIQUETTE)
    data = None
    try:
        data = works.doi(doi)
    except Exception as e:
        LOGGER.info(f'e: {e}')
        raise e

    LOGGER.info(f"DOI = {doi}. data = {data}")

    return data


def crossRefToMetaDict(in_dict):

    result = sqlitedb.DocMeta()
    # in_dict = dict([(kk.lower(), vv) for kk, vv in in_dict.items()])

    keys = [
        "title",
        "issue",
        "pages",
        "publication",
        "volume",
        "year",
        "doi",
        "abstract",
        "arxivId",
        "chapter",
        "city",
        "country",
        "edition",
        "institution",
        "isbn",
        "issn",
        "month",
        "day",
        "publisher",
        "series",
        "pmid",
    ]

    # get type
    _type = in_dict.get("type", None)
    if _type == "journal-article":
        result["type"] = "article"
    else:
        # not supported yet
        result["type"] = "article"

    # get authors
    authors = in_dict.get("author", None)
    if authors:
        firstnames = [aii.get("given", "") for aii in authors]
        lastnames = [aii.get("family", "") for aii in authors]
        result["firstNames_l"] = firstnames
        result["lastName_l"] = lastnames

    # get others
    for keyii in keys:
        if keyii in in_dict:
            vii = in_dict[keyii]
            if isinstance(vii, list):
                vii = "".join(vii)  # title is a list

            vii = strip_tags(vii)
            result[keyii] = vii

    # sometimes this is journal name
    if "journal-title" in in_dict:
        result["publication"] = in_dict["journal-title"]
    else:
        if "container-title" in in_dict:
            vii = in_dict["container-title"]
            if isinstance(vii, list):
                vii = "".join(vii)  # title is a list
            result["publication"] = vii

    if "page" in in_dict:
        result["pages"] = in_dict["page"]

    if "url" in in_dict:
        result["urls_l"] = [
            in_dict["url"],
        ]

    # get time
    if "year" not in in_dict:
        if "issued" in in_dict:
            issued = in_dict["issued"]
        elif "published-print" in in_dict:
            issued = in_dict["published-print"]

        if "date-parts" in issued:
            try:
                date = issued["date-parts"][0]
                if len(date) == 2:
                    year, month = date
                    result["year"] = str(year)
                    result["month"] = str(month)
                elif len(date) == 3:
                    year, month, day = date
                    result["year"] = str(year)
                    result["month"] = str(month)
                    result["day"] = str(day)
            except Exception:
                pass

    # result['confirmed']='true'

    return result


def download_arxiv_pdf(metadata):
    """Download PDF for an arXiv paper and save with naming convention:
    1stauthor_year_title.pdf
    """

    # Extract arXiv ID from metadata
    arxiv_id = metadata['arxivId']

    # Download PDF from arXiv
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    LOGGER.info(f"Downloading: {pdf_url}")
    response = requests.get(pdf_url, stream=True)
    response.raise_for_status()

    # Create temp file
    temp_file = QTemporaryFile(QDir.tempPath() + "/MTT_XXXXXXX.pdf")
    temp_file.setAutoRemove(False)
    if temp_file.open():
        for chunk in response.iter_content(chunk_size=8192):
            temp_file.write(chunk)

        # Get absolute path
        pdf_path = temp_file.fileName()
        temp_file.close()

    LOGGER.info(f"PDF saved to: {pdf_path}")

    return pdf_path


def fetchMetaByDOI(doi, status_bar):
    """Query meta data via doi in response to doi button click"""

    if not doi:
        return None

    # use waiting cursor
    QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
    status_bar.showMessage(f'Searching for {doi} ...')
    QtWidgets.QApplication.processEvents()

    LOGGER.info("doi = %s" % doi)

    try:
        # validate DOI format
        match = _DOI_PATTERN.match(doi)
        LOGGER.debug("match = %s" % match)

        if not match:
            _show_error_dialog("Failed to retrieve metadata from doi")
            return None

        # fetch metadata
        try:
            if 'arxiv' in doi.lower():
                doi_dict = fetchMetaByDOI_arxiv(doi)
            else:
                doi_dict = fetchMetaByDOI_crossref(doi)
        except Exception as e:
            LOGGER.error(e)
            LOGGER.warning("Failed to fetch from doi.")
            _show_error_dialog("Failed to retrieve metadata from doi")
            return None

        # convert to meta dict
        meta_dict = crossRefToMetaDict(doi_dict)
        if 'arxiv' in doi.lower():
            # download PDF
            try:
                status_bar.showMessage(f'Downloading PDF for {doi} ...')
                QtWidgets.QApplication.processEvents()
                pdf_path = download_arxiv_pdf(meta_dict)
            except Exception as e:
                LOGGER.error(e)
                LOGGER.warning("Failed to download PDF from doi.")
            else:
                status_bar.showMessage(f'Downloaded PDF for {doi}.')
                QtWidgets.QApplication.processEvents()
                meta_dict['files_l'].append(pdf_path)

        LOGGER.debug(f"Got meta_dict from doi: {meta_dict}")
        LOGGER.debug(f"citationkey = {meta_dict['citationkey']}")

        status_bar.showMessage(f'Fetched {doi}.')
        return meta_dict

    finally:
        # restore cursor
        QtWidgets.QApplication.restoreOverrideCursor()
        QtWidgets.QApplication.processEvents()

    return


def _show_error_dialog(message):
    """Show error dialog with given message"""

    msg = QtWidgets.QMessageBox()
    msg.resize(500, 500)
    msg.setIcon(QtWidgets.QMessageBox.Information)
    msg.setWindowTitle("Error")
    msg.setText("Oopsie.")
    msg.setInformativeText(message)
    msg.exec_()

    return
