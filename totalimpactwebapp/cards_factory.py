from totalimpactwebapp.card import ProductNewDiffCard
from totalimpactwebapp.card import ProfileNewDiffCard
from totalimpactwebapp.card import GenreNewDiffCard
from totalimpactwebapp.card import GenreAccumulationCard
from totalimpactwebapp.card import GenreProductsWithMoreThanCard
import configs

import datetime



def make_product_new_metrics_cards(products, url_slug):
    cards = []
    for product in products:

        for metric in product.metrics:
            if ProductNewDiffCard.would_generate_a_card(metric):
                new_card = ProductNewDiffCard(products, product, metric, url_slug)
                cards.append(new_card)

    return cards


def make_product_list_cards(products, card_class, url_slug=None):
    cards = []
    all_possible_metrics_config_dicts = configs.metrics().values()

    for metric_config in all_possible_metrics_config_dicts:
        provider = metric_config["provider"]
        interaction = metric_config["interaction"]

        if "citations" in interaction:
            continue  # we aren't allowed to accumulate scopus, don't want to accumulate PMC ciations

        if card_class.would_generate_a_card(products, provider, interaction):
            new_card = card_class(products, provider, interaction, url_slug)
            cards.append(new_card)

    return cards

def make_profile_new_metrics_cards(products, url_slug):
    return make_product_list_cards(products, ProfileNewDiffCard, url_slug)


def make_genre_cards(products):
    cards = []
    cards += make_product_list_cards(products, GenreAccumulationCard)
    cards += make_product_list_cards(products, GenreProductsWithMoreThanCard)
    cards.sort(key=lambda x: x.sort_by, reverse=True)
    return cards

def make_genre_new_metrics_cards(products):
    cards = []
    cards += make_product_list_cards(products, GenreNewDiffCard)
    return cards




