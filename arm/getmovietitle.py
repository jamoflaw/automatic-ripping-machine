#!/usr/bin/python3

import argparse
import urllib
import os
import datetime
import pydvdid
import unicodedata
import xmltodict
import sys # noqa # pylint: disable=unused-import
import re
import logging
import logger # noqa # pylint: disable=unused-import
import classes # noqa # pylint: disable=unused-import


def entry():
    """ Entry to program, parses arguments"""
    parser = argparse.ArgumentParser(description='Get Movie Title from DVD or Blu-Ray')
    parser.add_argument('-p', '--path', help='Mount path to disc', required=True)

    return parser.parse_args()


def getdvdtitle(disc):
    """ Calculates CRC64 for the DVD and calls Windows Media
        Metaservices and returns the Title and year of DVD """
    logging.debug(str(disc))

    # Try to work out title from the disc label
    dvd_title = disc.label.replace("_", " ").replace("16X9", "").replace("4X3", "").replace("_SE", "").replace("THX", "").replace("DTS", "").replace(" AND ", " ")
    
    return callwebservice(omdb_api_key, dvd_title)


def callwebservice(omdb_api_key, dvd_title, year=""):
    """ Queries OMDbapi.org for title information and parses if it's a movie
        or a tv series """

    logging.debug("***Calling webservice with Title: " + dvd_title + " and Year: " + year)
    try:
        strurl = "http://www.omdbapi.com/?t={1}&y={2}&plot=short&r=json&apikey={0}".format(omdb_api_key, dvd_title, year)
        logging.debug("http://www.omdbapi.com/?t={1}&y={2}&plot=short&r=json&apikey={0}".format("key_hidden", dvd_title, year))
        dvd_title_info_json = urllib.request.urlopen(strurl).read()
    except Exception:
        logging.debug("Webservice failed")
        return "fail"
    else:
        doc = json.loads(dvd_title_info_json.decode())
        if doc['Response'] == "False":
            logging.debug("Webservice failed with error: " + doc['Error'])
            return "fail"
        else:
            logging.debug("Webservice successful. DVD Title {} and year is {}".format(doc['Title'], doc['Year']))

            return doc['Title'], doc['Year']


def getbluraytitle(disc):
    """ Get's Blu-Ray title by parsing XML in bdmt_eng.xml """
    try:
        with open(disc.mountpoint + '/BDMV/META/DL/bdmt_eng.xml', "rb") as xml_file:
            doc = xmltodict.parse(xml_file.read())
    except OSError as e:
        logging.error("Disc is a bluray, but bdmt_eng.xml could not be found.  Disc cannot be identified.")
        return[None, None]

    try:
        bluray_title = doc['disclib']['di:discinfo']['di:title']['di:name']
    except KeyError:
        logging.error("Could not parse title from bdmt_eng.xml file.  Disc cannot be identified.")
        return[None, None]

    bluray_modified_timestamp = os.path.getmtime(disc.mountpoint + '/BDMV/META/DL/bdmt_eng.xml')
    bluray_year = (datetime.datetime.fromtimestamp(bluray_modified_timestamp).strftime('%Y'))

    bluray_title = unicodedata.normalize('NFKD', bluray_title).encode('ascii', 'ignore').decode()

    bluray_title = bluray_title.replace(' - Blu-rayTM', '')
    bluray_title = bluray_title.replace(' Blu-rayTM', '')
    bluray_title = bluray_title.replace(' - BLU-RAYTM', '')
    bluray_title = bluray_title.replace(' - BLU-RAY', '')
    bluray_title = bluray_title.replace(' - Blu-ray', '')
    return (bluray_title, bluray_year)


def clean_for_filename(string):
    """ Cleans up string for use in filename """
    string = re.sub('\[(.*?)\]', '', string)
    string = re.sub('\s+', ' ', string)
    string = string.replace(' : ', ' - ')
    string = string.replace(': ', ' - ')
    string = string.strip()
    return re.sub('[^\w\-_\.\(\) ]', '', string)

# pylint: disable=C0103


def main(disc):
    # args = entry()

    disc.hasnicetitle = False
    try:
        disc_title, disc_year = getdvdtitle(disc)
        if disc_title:
            disc_title = clean_for_filename(disc_title)
            logging.info("getmovietitle dvd title found: " + disc_title + " : " + disc_year)
        else:
            logging.warning("DVD title not found")
            disc_title = disc.label
            disc_year = "0000"
    except Exception:
        disc_title, disc_year = getbluraytitle(disc)
        if disc_title:
            disc_title = clean_for_filename(disc_title)
            logging.info("getmovietitle bluray title found: " + disc_title + " : " + disc_year)
            disc.hasnicetitle = True
        return(disc_title, disc_year)
    else:
        logging.info(str(disc_title) + " : " + str(disc_year))
        if disc_title:
            disc.hasnicetitle = True
        logging.info("Returning: " + str(disc_title) + ", " + str(disc_year))
        return(disc_title, disc_year)
