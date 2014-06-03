from __future__ import division
import math
import time

def make_awards_list(user):

    awards_list = []

    award = OAAward()
    # eventually the first param here is user.about...
    # but right now that doesn't exist.
    award.calculate({}, user.product_objects)

    awards_list.append(award)
    return awards_list





class ProfileAward(object):
    def __init__(self):
        self.level = 0
        self.level_names = ["Gold", "Silver", "Bronze", "Basic", "None"]
        self.name = "generic award"
        self.level_justification = "we said so"
        self.needed_for_next_level = None
        self.call_to_action = None
        self.timestamp = int(time.time())
        self.bins = []
        self.extra = {}

    def as_dict(self):
        return {
            "name": self.name,
            "level": self.level,
            "award_badge": not self.is_bottom_level(),
            "is_perfect": self.is_perfect(),
            "level_name": self.level_name(),
            "level_justification": self.level_justification,
            "needed_for_next_level": self.needed_for_next_level,
            "call_to_action": self.call_to_action,
            "timestamp": self.timestamp,
            "extra": self.extra
        }

    def calculate(self, about, products):
        raise NotImplementedError  # override in children

    def level_name(self):
        return self._value_for_level(self.level_names)

    def next_level_name(self):
        return self._value_for_level(self.level_names, True)

    def level_cutoff(self):
        return self._value_for_level(self.bins)

    def next_level_cutoff(self):
        return self._value_for_level(self.bins, True)

    def bottom_level(self):
        return len(self.bins) + 1

    def is_bottom_level(self):
        return self.level == self.bottom_level()

    def _value_for_level(self, values, next_level=False):
        if next_level:
            i = self.level - 2
        else:
            i = self.level - 1

        if i < 0:
            return None

        try:
            return values[i]
        except IndexError:
            return None









class OAAward(ProfileAward):

    def __init__(self):
        ProfileAward.__init__(self)
        self.name = "Open Access"
        self.bins =[
            .80,  # ~10% users
            .50,  # 15%
            .30,  # 25%
            .10   # 50%
        ]

    def is_perfect(self):
        return self.extra["oa_articles_proportion"] == 1

    def calculate(self, about, products):

        article_products = [p for p in products if p.biblio.genre == "article"]
        article_count = len(article_products)
        self.extra["articles_count"] = article_count

        oa_articles = [p for p in article_products if p.biblio.free_fulltext_host]
        oa_article_count = len(oa_articles)
        self.extra["oa_articles_count"] = oa_article_count

        try:
            oa_proportion = oa_article_count / article_count
        except ZeroDivisionError:
            oa_proportion = 0

        self.extra["oa_articles_proportion"] = oa_proportion
        
        # calculate level
        self.level = self.bottom_level()

        # print "starting level check"

        for i, bin_edge_val in enumerate(self.bins):
            this_level = i+1  # levels start with 1

            # print "checking level ", this_level, " (", bin_edge_val, ") against oa proportion of ", oa_proportion
            if oa_proportion >= bin_edge_val:
                self.level = this_level
                break



        # justification
        self.level_justification = "{oa_perc}% of {article_count} listed articles free for anyone to read.".format(
            oa_perc=int(round(oa_proportion*100)),
            article_count=article_count
        )


        # needed for next level
        # print "next level cutoff", self.next_level_cutoff()

        if self.next_level_cutoff() is not None:
            oa_articles_in_next_level = int(
                math.ceil(self.next_level_cutoff() * article_count))

            fulltext_urls_needed = oa_articles_in_next_level - oa_article_count

            self.needed_for_next_level = "You're just {needed} freely-readable articles away from {next_level} level.".format(
                needed=fulltext_urls_needed,
                next_level=self.next_level_name()
            )

            if self.is_bottom_level():
                thing_you_want = "Get the Open Access badge"
            else:
                thing_you_want = "Advance to the {next_level}-level Open Access badge".format(
                    next_level=self.next_level_name()
                )

            self.extra["needed_for_next_level_product_page"] = "{thing_you_want} by adding free fulltext to this and {more_needed} more articles.".format(
                thing_you_want=thing_you_want,
                more_needed=fulltext_urls_needed-1
            )

            self.call_to_action = "To add more, click any article missing the <i class='icon-unlock-alt'></i> icon and add links to free fulltext."

        else:
            self.needed_for_next_level = "Congrats, that's the highest level we've got--you're one of the OA elite!"



