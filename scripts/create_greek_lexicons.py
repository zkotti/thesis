#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Note: Cleaner library is property of isMOOD and is not publicly distributed
# The script fails without this library at the moment

from future import print_function

import Cleaner # TO IMPLEMENT
import csv
import re
import settings
import spacy


__author__ = 'Zoe Kotti'
__email__ = 'kotti@ismood.com'
__copyright__ = 'Copyright 2019, isMOOD'


# Prepare Cleaner -- TO IMPLEMENT
class_setter = {
    'polytonic': True,
    'lower': True
}

# Load Cleaner -- TO IMPLEMENT
cleaner = Cleaner(class_setter)

# Load Greek core from spacy
nlp = spacy.load('el_core_news_md')

# Sources of Greek terms
INPUT_FILE_ASPELL = 'lexicons/el_GR-0.9.csv'
INPUT_FILE_WIKI = 'lexicons/elwords_from_wiktionary.csv'
INPUT_FILE_LEMMAS = 'lexicons/greek_lemmas.csv'

# Mapping dictionary for the spacy POS tags found at:
# https://spacy.io/api/annotation#pos-tagging
POS_DICT = {
    'ADJ': 'adjective',
    'ADP': 'adposition',
    'ADV': 'adverb',
    'AUX': 'auxiliary',
    'CONJ': 'conjunction',
    'CCONJ': 'coordinating_conjunction',
    'DET': 'determiner',
    'INTJ': 'interjection',
    'NOUN': 'noun',
    'NUM': 'numeral',
    'PART': 'particle',
    'PRON': 'pronoun',
    'PROPN': 'proper_noun',
    'PUNCT': 'punctuation',
    'SCONJ': 'subordinating_conjunction',
    'SYM': 'symbol',
    'VERB': 'verb',
    'X': 'other',
    'SPACE': 'space'
}


def find_sentiment(pos_score, neg_score, obj_score):
    scores = [pos_score, neg_score, obj_score]
    scores.sort(reverse=True)

    magic_number = (scores[0] - scores[1]) + (scores[0] - scores[2])
    # Priority is given first to positive, then to negative, and lastly to objective
    if scores[0] == pos_score:
        majority = 'positive'
    elif scores[0] == neg_score:
        majority = 'negative'
    else:
        majority = 'objective'

    sentiment = {
        'PosScore': round(pos_score, 3),
        'NegScore': round(neg_score, 3),
        'ObjScore': round(obj_score, 3),
        'magic_number': round(magic_number, 3),
        'majority': majority
    }

    return sentiment


def prepare_insert(term, source):
    words_count = len(re.split('\s+', term))

    insert = {
        '_id': term,
        'sources': [source],
        'sources_count': 1,
        'clean': cleaner.clean_text(term)['text'],
        'words_count': words_count
    }

    if words_count == 1:
        doc = nlp(term.encode('utf-8'))

        spacy = {
            'lemma': doc[0].lemma_,
            'pos': doc[0].pos_,
            'tag': doc[0].tag_,
            'dep': doc[0].dep_,
            'shape': doc[0].shape_,
            'is_alpha': doc[0].is_alpha,
            'is_stop': doc[0].is_stop
        }

        insert['spacy'] = spacy

    return insert


def init_greek_terms(greek_terms):
    # Aspell
    with open(INPUT_FILE_ASPELL, 'r') as dict_aspell:
        csv_reader = csv.DictReader(dict_aspell)

        for row in csv_reader:
            insert = prepare_insert(row['term'], 'aspell')
            greek_terms.insert_one(insert)

    # Wiktionary
    with open(INPUT_FILE_WIKI, 'r') as dict_wiki:
        csv_reader = csv.DictReader(dict_wiki)

        for row in csv_reader:
            term = row['term']

            if greek_terms.count({'_id': term}) == 0:
                insert = prepare_insert(term, 'wiktionary')
                greek_terms.insert_one(insert)
            else:
                existing_term = greek_terms.find_one({'_id': term}, {'sources_count': 1})

                update = {
                    '$addToSet': {'sources': 'wiktionary'},
                    '$set': {'sources_count': existing_term['sources_count'] + 1}
                }

                greek_terms.update({'_id': term}, update)

    # Greek Lemmas
    with open(INPUT_FILE_LEMMAS, 'r') as dict_lemmas:
        csv_reader = csv.DictReader(dict_lemmas)

        for row in csv_reader:
            term = row['term']

            if greek_terms.count({'_id': term}) == 0:
                insert = prepare_insert(term, 'greek_lemmas')
                greek_terms.insert_one(insert)
            else:
                existing_term = greek_terms.find_one({'_id': term}, {'sources_count': 1})

                update = {
                    '$addToSet': {'sources': 'greek_lemmas'},
                    '$set': {'sources_count': existing_term['sources_count'] + 1}
                }

                greek_terms.update({'_id': term}, update)


def populate_lemmas(greek_terms):
    documents = greek_terms.find({'spacy': {'$exists': 1}}, {'spacy': 1}, no_cursor_timeout=True)
    lemmas = set()
    ids = set()

    for doc in documents:
        spacy = doc['spacy']
        lemmas.add(spacy['lemma'].lower())
        ids.add(doc['_id'].lower())

    for lemma in lemmas:
        if lemma in ids:
            # Ignore case sensitivity of ids
            existing_lemmas = greek_terms.find({'_id': {'$regex': '^{}$'.format(lemma.encode('utf-8')), '$options': '-i'}}, {'sources': 1, 'sources_count': 1})

            for existing in existing_lemmas:
                update = {
                    '$addToSet': {'sources': 'lemmas_generated'},
                    '$set': {'sources_count': existing['sources_count'] + 1}
                }

                greek_terms.update({'_id': existing['_id']}, update)
        else:

            insert = prepare_insert(lemma, 'lemmas_generated')
            greek_terms.insert_one(insert)

    documents.close()


def map_sentiment(greek_terms, english_sentiment_terms):
    english_documents = english_sentiment_terms.find({}, {'sentiment': 1, 'translation': 1}, no_cursor_timeout=True).sort('_id', 1)
    index = 0

    for doc in english_documents:
        print("Index: {}".format(index))

        translation = doc['translation']
        translation_lowercase = translation['lowercase']
        en_sentiment = doc['sentiment']

        greek_documents = greek_terms.find({'_id': {'$regex': '^{}$'.format(translation_lowercase.encode('utf-8')), '$options': '-i'}}, {'sentiment': 1})

        if greek_documents.count():
            for gr_doc in greek_documents:
                if 'sentiment' in gr_doc.keys():
                    gr_sentiment = gr_doc['sentiment']

                    pos_score = gr_sentiment['PosScore'] + en_sentiment['PosScore']
                    neg_score = gr_sentiment['NegScore'] + en_sentiment['NegScore']
                    obj_score = gr_sentiment['ObjScore'] + en_sentiment['ObjScore']
                    occurrences = gr_sentiment['occurrences'] + 1
                else:
                    pos_score = en_sentiment['PosScore']
                    neg_score = en_sentiment['NegScore']
                    obj_score = en_sentiment['ObjScore']
                    occurrences = 1

                update = {
                    '$set': {
                        'sentiment': {
                            'PosScore': pos_score,
                            'NegScore': neg_score,
                            'ObjScore': obj_score,
                            'occurrences': occurrences
                        }
                    }
                }

                greek_terms.update({'_id': gr_doc['_id']}, update)
                print("Index: {} -- Term: {}".format(index, gr_doc['_id'].encode('utf-8')))
        index += 1

    english_documents.close()

    greek_documents = greek_terms.find({'sentiment': {'$exists': 1}}, {'sentiment': 1}, no_cursor_timeout=True)

    for doc in greek_documents:
        gr_sentiment = doc['sentiment']

        pos_score = gr_sentiment['PosScore'] / gr_sentiment['occurrences']
        neg_score = gr_sentiment['NegScore'] / gr_sentiment['occurrences']
        obj_score = gr_sentiment['ObjScore'] / gr_sentiment['occurrences']

        sentiment = find_sentiment(pos_score, neg_score, obj_score)

        greek_terms.update({'_id': doc['_id']}, {'$set': {'sentiment': sentiment}})

    greek_documents.close()


def init_greek_sentiment_terms(greek_terms, greek_sentiment_terms):
    gr_terms_documents = greek_terms.find({'$and': [{'sentiment': {'$exists': 1}}, {'words_count': 1}]}, {'clean': 1, 'sentiment': 1, 'spacy': 1}, no_cursor_timeout=True)

    for doc in gr_terms_documents:
        clean = doc['clean']
        spacy = doc['spacy']
        sentiment = doc['sentiment']
        pos_score = sentiment['PosScore']
        neg_score = sentiment['NegScore']
        obj_score = sentiment['ObjScore']

        gr_doc = greek_sentiment_terms.find_one({'_id': clean})

        # Clean term exists
        if gr_doc:
            # Clean term has sentiment
            if 'sentiment' in gr_doc.keys():
                gr_sentiment = gr_doc['sentiment']
                pos_score += gr_sentiment['PosScore']
                neg_score += gr_sentiment['NegScore']
                obj_score += gr_sentiment['ObjScore']

            update = {
                '$push': {
                    'pos': POS_DICT[spacy['pos']]
                },
                '$set': {
                    'sources_count': gr_doc['sources_count'] + 1,
                    'sentiment': {
                        'PosScore': pos_score,
                        'NegScore': neg_score,
                        'ObjScore': obj_score
                    }
                }
            }

            greek_sentiment_terms.update({'_id': clean}, update)

        # Clean term does not exist
        else:

            insert = {
                '_id': clean,
                'sources_count': 1,
                'words_count': len(re.split('\s+', clean)),
                'pos': [POS_DICT[spacy['pos']]],
                'sentiment': {
                    'PosScore': pos_score,
                    'NegScore': neg_score,
                    'ObjScore': obj_score
                }
            }

            greek_sentiment_terms.insert_one(insert)

    gr_terms_documents.close()

    greek_documents = greek_sentiment_terms.find({}, {'sentiment': 1, 'pos': 1, 'sources_count': 1}, no_cursor_timeout=True)

    for gr_doc in greek_documents:
        gr_sentiment = gr_doc['sentiment']
        pos_score = gr_sentiment['PosScore'] / gr_doc['sources_count']
        neg_score = gr_sentiment['NegScore'] / gr_doc['sources_count']
        obj_score = gr_sentiment['ObjScore'] / gr_doc['sources_count']
        sentiment = find_sentiment(pos_score, neg_score, obj_score)

        update = {
            '$set': {
                'sentiment': sentiment,
                'pos': max(gr_doc['pos'], key=gr_doc['pos'].count)
            }
        }

        greek_sentiment_terms.update({'_id': gr_doc['_id']}, update)

    greek_documents.close()


def main():
    greek_terms = settings.MONGO_CLIENT.lexicondb.greek_terms
    greek_sentiment_terms = settings.MONGO_CLIENT.lexicondb.greek_sentiment_terms
    english_sentiment_terms = settings.MONGO_CLIENT.lexicondb.english_sentiment_terms

    init_greek_terms(greek_terms)
    populate_lemmas(greek_terms)
    map_sentiment(greek_terms, english_sentiment_terms)
    init_greek_sentiment_terms(greek_terms, greek_sentiment_terms)


if __name__ == '__main__':

    main()
