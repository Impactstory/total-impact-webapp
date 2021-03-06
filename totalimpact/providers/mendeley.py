from __future__ import absolute_import

from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderAuthenticationError
from totalimpact import tiredis
from retry import Retry
from totalimpactwebapp.countries import iso_code_from_name
from totalimpactwebapp.aliases import normalize_alias_tuple
from util import remove_punctuation

import simplejson, urllib, os, string, itertools
import requests
import requests.auth
import redis
from urllib import urlencode
from urlparse import parse_qs, urlsplit, urlunsplit

# need to get system mendeley library
from mendeley.exception import MendeleyException
import mendeley as mendeley_lib

import logging
logger = logging.getLogger('ti.providers.mendeley')

class Mendeley(Provider):  

    example_id = ("doi", "10.1371/journal.pcbi.1000361")

    url = "http://www.mendeley.com"
    descr = "A research management tool for desktop and web."

    static_meta_dict = {
        "readers": {
            "display_name": "readers",
            "provider": "Mendeley",
            "provider_url": "http://www.mendeley.com/",
            "description": "The number of people who have added this item to their Mendeley library",
            "icon": "http://www.mendeley.com/favicon.ico",
        },   
        "discipline": {
            "display_name": "discipline",
            "provider": "Mendeley",
            "provider_url": "http://www.mendeley.com/",
            "description": "readers by discipline",
            "icon": "http://www.mendeley.com/favicon.ico",
        },   
        "career_stage": {
            "display_name": "career stage",
            "provider": "Mendeley",
            "provider_url": "http://www.mendeley.com/",
            "description": "readers by career_stage",
            "icon": "http://www.mendeley.com/favicon.ico",
        },   
        "country": {
            "display_name": "country, top 3 percentages",
            "provider": "Mendeley",
            "provider_url": "http://www.mendeley.com/",
            "description": "readers by country",
            "icon": "http://www.mendeley.com/favicon.ico",
        }
    }

    def __init__(self):
        self.session = None
        super(Mendeley, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        relevant = (namespace in ["doi", "pmid", "arxiv", "biblio"])
        return(relevant)

    @property
    def provides_aliases(self):
         return True

    @property
    def provides_biblio(self):
         return True

    @property
    def provides_metrics(self):
         return True

    def _connect(self):
        mendeley_client = mendeley_lib.Mendeley(
            client_id=os.getenv("MENDELEY_OAUTH2_CLIENT_ID"), 
            client_secret=os.getenv("MENDELEY_OAUTH2_SECRET"))
        auth = mendeley_client.start_client_credentials_flow()
        session = auth.authenticate()
        return session

    def _get_doc_by_id(self, namespace, aliases_dict):
        try:
            nid = aliases_dict[namespace][0]
            kwargs = {namespace:nid, "view":'stats'}
            doc = self.session.catalog.by_identifier(**kwargs)
        except (KeyError, MendeleyException):
            doc = None
        return doc

    def _get_doc_by_title(self, aliases_dict):
        doc = None
        try:
            biblio = aliases_dict["biblio"][0]
            biblio_title = remove_punctuation(biblio["title"]).lower()
            biblio_year = str(biblio["year"])
            if biblio_title and biblio_year:
                try:
                    doc = self.session.catalog.advanced_search(
                            title=biblio_title, 
                            min_year=biblio_year, 
                            max_year=biblio_year,
                            view='stats').list(page_size=1).items[0]
                except (UnicodeEncodeError, IndexError):
                    biblio_title = remove_punctuation(biblio["title"].encode('ascii','ignore'))
                    try:
                        doc = self.session.catalog.advanced_search(
                                title=biblio_title, 
                                min_year=biblio_year, 
                                max_year=biblio_year,
                                view='stats').list(page_size=1).items[0]
                    except (IndexError):
                        return None

                mendeley_title = remove_punctuation(doc.title).lower()
                if biblio_title != mendeley_title:
                    logger.debug(u"Mendeley: titles don't match so not using this match /biblio_print %s and %s" %(
                        biblio_title, mendeley_title))
                    doc = None
        except (KeyError, MendeleyException):
            # logger.info(u"No biblio found in _get_doc_by_title")
            pass
        return doc




    def _get_doc(self, aliases):
        from totalimpactwebapp.aliases import alias_dict_from_tuples
        aliases_dict = alias_dict_from_tuples(aliases)

        if not self.session:
            self.session = self._connect()
        doc = None

        lookup_by = [namespace for namespace in aliases_dict.keys() if namespace in ["doi", "pmid", "arxiv"]]
        if lookup_by:
            doc = self._get_doc_by_id(lookup_by[0], aliases_dict)
            
        if not doc and ("biblio" in aliases_dict):
            doc = self._get_doc_by_title(aliases_dict)

        return doc


    def metrics(self, 
            aliases,
            provider_url_template=None, # ignore this because multiple url steps
            cache_enabled=True):

        metrics_and_drilldown = {}
        doc = self._get_doc(aliases)

        if doc:  
            try:
                drilldown_url = doc.link
                metrics_and_drilldown["mendeley:readers"] = (doc.reader_count, drilldown_url)
                metrics_and_drilldown["mendeley:career_stage"] = (doc.reader_count_by_academic_status, drilldown_url)

                by_discipline = {}
                by_subdiscipline = doc.reader_count_by_subdiscipline
                if by_subdiscipline:
                    for discipline, subdiscipline_breakdown in by_subdiscipline.iteritems():
                        by_discipline[discipline] = sum(subdiscipline_breakdown.values())
                    metrics_and_drilldown["mendeley:discipline"] = (by_discipline, drilldown_url)

                by_country_iso = {}
                by_country_names = doc.reader_count_by_country
                if by_country_names:
                    for country_name, country_breakdown in by_country_names.iteritems():
                        iso = iso_code_from_name(country_name)
                        if iso:
                            by_country_iso[iso] = country_breakdown
                        else:
                            logger.error(u"Can't find country {country} in lookup".format(
                                country=country_name))
                    if by_country_iso:
                        metrics_and_drilldown["mendeley:countries"] = (by_country_iso, drilldown_url)

            except KeyError:
                pass

        return metrics_and_drilldown


    def biblio(self, 
            aliases,
            provider_url_template=None,
            cache_enabled=True):

        biblio = {}
        doc = self._get_doc(aliases)
        if doc:  
            biblio["url"] = doc.link  
            biblio["abstract"] = doc.abstract  
            if "issn" in doc.identifiers:
                biblio["issn"] = doc.identifiers["issn"]
                if provider.is_issn_in_doaj(biblio["issn"]):
                    biblio["free_fulltext_url"] = self.get_best_url(aliases)

        return biblio

    # overriding
    def aliases(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True):            

        # have reported all of these to mendeley, ie http://support.mendeley.com/customer/en/portal/questions/11307109-wrong-pmid?new=11307109
        bad_mendeley_aliases = [
            ("pmid", "19016882"),  # http://www.mendeley.com/catalog/scientific-workflow-management-kepler-system-1/
            ("pmid", "22170219"),  #http://www.mendeley.com/catalog/social-network-analysis-animal-behaviour-promising-tool-study-sociality-1/
            ("pmid", "20433197")  #http://support.mendeley.com/customer/en/portal/questions/11494864-wrong-pmid?new=11494864
        ]

        doc = self._get_doc(aliases)
        new_aliases = []
        if doc:  
            if doc.identifiers:
                from totalimpactwebapp.aliases import alias_dict_from_tuples
                aliases_dict = alias_dict_from_tuples(aliases)
                for namespace in doc.identifiers:
                    if namespace in ["doi", "arxiv", "pmid", "scopus"] and (namespace not in aliases_dict):
                        new_alias = normalize_alias_tuple(namespace, doc.identifiers[namespace])
                        if new_alias and new_alias not in bad_mendeley_aliases:
                            new_aliases += [new_alias]

            new_aliases += [("url", doc.link)]
            new_aliases += [("mendeley_uuid", doc.id)]
            new_aliases = [alias for alias in new_aliases if alias not in aliases]

        return new_aliases

