#!/usr/bin/env python
# -*- coding: utf-8 -*-

from future import print_function

import settings


__author__ = 'Zoe Kotti'
__email__ = 'kotti@ismood.com'
__copyright__ = 'Copyright 2019, isMOOD'


def count_collection(mongodb_col):
    terms_count = mongodb_col.count()
    words_count = mongodb_col.count({'words_count': 1})
    phrases_count = mongodb_col.count({'words_count': {'$gt': 1}})
    chars_count = 0

    terms = mongodb_col.find({}, {'_id': 1})

    for term in terms:
        chars_count += len(term['_id'])

    return terms_count, words_count, phrases_count, chars_count


def count_untranslated_collection(mongodb_col):
    terms_count = mongodb_col.count({'translation': {'$exists': 0}})
    words_count = mongodb_col.count({'$and': [{'translation': {'$exists': 0}}, {'words_count': 1}]})
    phrases_count = mongodb_col.count({'$and': [{'translation': {'$exists': 0}}, {'words_count': {'$gt': 1}}]})
    chars_count = 0

    terms = mongodb_col.find({'translation': {'$exists': 0}}, {'_id': 1})

    for term in terms:
        chars_count += len(term['_id'])

    return terms_count, words_count, phrases_count, chars_count


def main():
    greek_terms = settings.MONGO_CLIENT.lexicondb.greek_terms
    english_sentiment_terms = settings.MONGO_CLIENT.lexicondb.english_sentiment_terms

    gr_terms_count, gr_words_count, gr_phrases_count, gr_chars_count = count_collection(greek_terms)
    en_terms_count, en_words_count, en_phrases_count, en_chars_count = count_collection(english_sentiment_terms)

    un_gr_terms_count, un_gr_words_count, un_gr_phrases_count, un_gr_chars_count = count_untranslated_collection(greek_terms)
    un_en_terms_count, un_en_words_count, un_en_phrases_count, un_en_chars_count = count_untranslated_collection(english_sentiment_terms)

    print("\nTotal Greek terms: {}".format(gr_terms_count))
    print("Total Greek words: {}".format(gr_words_count))
    print("Total Greek phrases: {}".format(gr_phrases_count))
    print("Total Greek characters: {}".format(gr_chars_count))

    print("\nTotal English terms: {}".format(en_terms_count))
    print("Total English words: {}".format(en_words_count))
    print("Total English phrases: {}".format(en_phrases_count))
    print("Total English characters: {}".format(en_chars_count))

    print("\nUntranslated Greek terms: {}".format(un_gr_terms_count))
    print("Untranslated Greek words: {}".format(un_gr_words_count))
    print("Untranslated Greek phrases: {}".format(un_gr_phrases_count))
    print("Untranslated Greek characters: {}".format(un_gr_chars_count))

    print("\nUntranslated English terms: {}".format(un_en_terms_count))
    print("Untranslated English words: {}".format(un_en_words_count))
    print("Untranslated English phrases: {}".format(un_en_phrases_count))
    print("Untranslated English characters: {}\n".format(un_en_chars_count))


if __name__ == '__main__':

    main()
