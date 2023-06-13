import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import logging

log = logging.getLogger("openjustice")


def xml_jurinet_reader(path_to_file: str, text_tag: str = "TEXTE_ARRET"):
    if path_to_file.endswith(".xml"):
        tree = ET.parse(path_to_file)
        root = tree.getroot()
        arret = root.find(text_tag)
        return arret.text
    else:
        log.warning(f"The file {path_to_file} is not an XML file")


def html_jurica_reader(path_to_file: str, encoding: str = None):
    if path_to_file.endswith(".html"):
        with open(path_to_file, encoding=encoding) as f:
            data = f.read()
        soup = BeautifulSoup(data)
        return soup.text
    else:
        log.warning(f"The file {path_to_file} is not an HTML file")
