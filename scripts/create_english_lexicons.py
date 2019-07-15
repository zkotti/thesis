#!/usr/bin/env python
# -*- coding: utf-8 -*-

from future import print_function

import csv
import re
import settings
import spacy
from google.cloud import translate


__author__ = 'Zoe Kotti'
__email__ = 'kotti@ismood.com'
__copyright__ = 'Copyright 2019, isMOOD'


# Load English core from spacy
nlp = spacy.load('en_core_web_lg')

# Load Google Translate Client
translate_client = translate.Client()

# Source of English terms
INPUT_FILE_SWN = 'lexicons/SentiWordNet_3.0.0.csv'

# Mapping dictionary for the SWN POS tags found at:
# https://www.academia.edu/4062253/Using_SentiWordNet_for_Sentiment_Classification_What_is_SentiWordNet
POS_DICT = {
    'a': 'adjective',
    'n': 'noun',
    'r': 'adverb',
    'v': 'verb'
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


def init_swn_v3(swn_v3):
    documents = swn_v3.find({}, {'_id': 1})
    if documents:
        ids_list = []
        for doc in documents:
            ids_list.append(doc['_id'])

    with open(INPUT_FILE_SWN, 'r') as swn_v3_file:
        csv_reader = csv.reader(swn_v3_file, delimiter='\t')

        for row in csv_reader:
            pos_raw = row[0]
            swn_id = row[1]
            pos_id = '{}_{}'.format(pos_raw, swn_id)

            if pos_id in ids_list:
                continue

            pos_score = float(row[2])
            neg_score = float(row[3])
            terms = re.split('\s+', row[4])
            gloss = re.split(';', row[5])

            pos_mapped = POS_DICT[pos_raw]
            obj_score = 1 - (pos_score + neg_score)

            sentiment = {
                'PosScore': pos_score,
                'NegScore': neg_score,
                'ObjScore': obj_score
            }

            explanations = []
            examples = []
            synsets = []

            for sentence in gloss:
                sentence = sentence.strip()

                if sentence.startswith('\"'):
                    these_examples = re.findall(r'"([^"]+)"', sentence)
                    examples.extend(these_examples)
                else:
                    explanations.append(sentence)

            gloss_dict = {
                'explanations': explanations,
                'explanations_count': len(explanations),
                'examples': examples,
                'examples_count': len(examples)
            }

            for term in terms:
                synset = {}
                term_split = term.split('#', 1)
                term = term_split[0]
                # Phrase
                if '_' in term:
                    term = term.replace('_', ' ')
                # Word
                else:
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

                    synset['spacy'] = spacy

                if len(term_split) > 1:
                    sense_number = int(term_split[1])
                else:
                    sense_number = 'Null'

                synset['sense_number'] = sense_number
                synset['term'] = term
                synsets.append(synset)

            insert = {
                '_id': pos_id,
                'pos': pos_mapped,
                'swn_id': swn_id,
                'sentiment': sentiment,
                'synsets': synsets,
                'synsets_count': len(synsets),
                'gloss': gloss_dict
            }

            swn_v3.insert_one(insert)


def init_english_sentiment_terms(swn_v3, english_sentiment_terms):
    documents = swn_v3.find()

    for doc in documents:
        synsets = doc['synsets']
        doc_sentiment = doc['sentiment']

        for synset in synsets:
            term = synset['term']

            if english_sentiment_terms.count({'_id': term}) == 0:

                sentiment = find_sentiment(doc_sentiment['PosScore'], doc_sentiment['NegScore'], doc_sentiment['ObjScore'])

                insert = {
                    '_id': term,
                    'words_count': len(re.split('\s+', term)),
                    'swn_v3_ids': [doc['_id']],
                    'swn_v3_ids_count': 1,
                    'sources': ['swn_v3'],
                    'sources_count': 1,
                    'sentiment': sentiment
                }

                english_sentiment_terms.insert_one(insert)
            else:

                existing_term = english_sentiment_terms.find_one({'_id': term}, {'swn_v3_ids': 1, 'swn_v3_ids_count': 1})

                update = {
                    '$addToSet': {'swn_v3_ids': doc['_id']},
                    '$set': {'swn_v3_ids_count': existing_term['swn_v3_ids_count'] + 1}
                }

                english_sentiment_terms.update({'_id': term}, update)


def populate_lemmas(swn_v3, english_sentiment_terms):
    swn_documents = swn_v3.find({}, {'synsets': 1, 'sentiment': 1}, no_cursor_timeout=True)
    english_documents = english_sentiment_terms.find({}, {'_id': 1}, no_cursor_timeout=True)

    lemmas_dict = {}
    ids = set()

    for doc in english_documents:
        ids.add(doc['_id'].lower())

    for doc in swn_documents:
        swn_v3_id = doc['_id']
        synsets = doc['synsets']
        sentiment = doc['sentiment']

        for synset in synsets:
            if 'spacy' not in synset.keys():
                continue

            spacy = synset['spacy']
            lemma = spacy['lemma'].lower()

            if lemma in lemmas_dict.keys():
                lemma_details = lemmas_dict[lemma]

                if swn_v3_id not in lemma_details['swn_v3_ids']:
                    lemma_details['swn_v3_ids'].append(swn_v3_id)
                    lemma_details['swn_v3_ids_count'] += 1
                    lemma_sentiment = lemma_details['sentiment']
                    lemma_sentiment['PosScore'] += sentiment['PosScore']
                    lemma_sentiment['NegScore'] += sentiment['NegScore']
                    lemma_sentiment['ObjScore'] += sentiment['ObjScore']
            else:
                lemmas_dict[lemma] = {
                    'swn_v3_ids': [swn_v3_id],
                    'swn_v3_ids_count': 1,
                    'sentiment': find_sentiment(sentiment['PosScore'], sentiment['NegScore'], sentiment['ObjScore'])
                }

    for lemma_details in lemmas_dict.values():
        if lemma_details['swn_v3_ids_count'] > 1:
            sentiment = lemma_details['sentiment']
            sentiment['PosScore'] /= lemma_details['swn_v3_ids_count']
            sentiment['NegScore'] /= lemma_details['swn_v3_ids_count']
            sentiment['ObjScore'] /= lemma_details['swn_v3_ids_count']
            lemma_details['sentiment'] = find_sentiment(sentiment['PosScore'], sentiment['NegScore'], sentiment['ObjScore'])

    for lemma, lemma_details in lemmas_dict.items():
        if lemma in ids:
            # Ignore case sensitivity of ids
            existing_lemmas = english_sentiment_terms.find({'_id': {'$regex': '^{}$'.format(lemma.encode('utf-8')), '$options': '-i'}}, {'sources': 1, 'sources_count': 1})

            for existing in existing_lemmas:
                update = {
                    '$addToSet': {'sources': 'lemmas_generated'},
                    '$set': {'sources_count': existing['sources_count'] + 1}
                }

                english_sentiment_terms.update({'_id': existing['_id']}, update)
        else:

            insert = {
                '_id': lemma,
                'words_count': len(re.split('\s+', lemma)),
                'swn_v3_ids': lemma_details['swn_v3_ids'],
                'swn_v3_ids_count': lemma_details['swn_v3_ids_count'],
                'sources': ['lemmas_generated'],
                'sources_count': 1,
                'sentiment': lemma_details['sentiment']
            }

            english_sentiment_terms.insert_one(insert)

    swn_documents.close()
    english_documents.close()


def translate_lexicon(english_sentiment_terms):
    # Mind translation limits: https://cloud.google.com/translate/quotas
    target_language = 'el'
    documents = english_sentiment_terms.find({'translation': {'$exists': 0}}, no_cursor_timeout=True)

    for doc in documents:
        translation = translate_client.translate(doc['_id'], target_language=target_language)

        translated_text = str(translation['translatedText'].encode('utf-8'))

        translation_dict = {
            'raw': translated_text,
            'lowercase': translated_text.lower()
        }

        english_sentiment_terms.update({'_id': doc['_id']}, {'$set': {'translation': translation_dict}})

    documents.close()


def main():
    swn_v3 = settings.MONGO_CLIENT.lexicondb.swn_v3
    english_sentiment_terms = settings.MONGO_CLIENT.lexicondb.english_sentiment_terms

    init_swn_v3(swn_v3)
    init_english_sentiment_terms(swn_v3, english_sentiment_terms)
    populate_lemmas(swn_v3, english_sentiment_terms)
    translate_lexicon(english_sentiment_terms)


if __name__ == '__main__':

    main()
