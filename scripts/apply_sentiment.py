#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Note: Cleaner library is property of isMOOD and is not publicly distributed
# The script fails without this library at the moment

from future import print_function

import Cleaner # TO IMPLEMENT
import csv
import json
import settings
import spacy
from spacy.lang.el import Greek


__author__ = 'Zoe Kotti'
__email__ = 'kotti@ismood.com'
__copyright__ = 'Copyright 2019, isMOOD'


# Prepare Cleaner -- TO IMPLEMENT
class_setter = {
    'rt': True,
    'hashtag': True,
    'mention': True,
    'polytonic': True,
    'links': True,
    'numbers': True,
    'only_alpha': True,
    'consecutives': True,
    'stopWords': True,
    'lower': True,
    'punctuation': True
}

# Load Cleaner -- TO IMPLEMENT
cleaner = Cleaner(class_setter)

# Load Greek core from spacy
nlp = spacy.load('el_core_news_md')


def init_greek_lexicon(greek_sentiment_terms):
    greek_lexicon = {}

    for term in greek_sentiment_terms:
        term_sentiment = term['sentiment']

        greek_lexicon[term['_id']] = {
            'positive': term_sentiment['PosScore'],
            'negative': term_sentiment['NegScore'],
            'objective': term_sentiment['ObjScore']
        }

    return greek_lexicon


def find_sentence_sentiment(sentence_document, greek_lexicon):
    sentence_sentiment = {'positive': 0, 'negative': 0, 'objective': 0}
    terms_count = 0

    for token in sentence_document:
        term_sentiment = None
        if token.text in greek_lexicon.keys():
            term_sentiment = greek_lexicon[token.text]
        elif token.lemma_ in greek_lexicon.keys():
            term_sentiment = greek_lexicon[token.lemma_]

        if term_sentiment:
            sentence_sentiment['positive'] += term_sentiment['positive']
            sentence_sentiment['negative'] += term_sentiment['negative']
            sentence_sentiment['objective'] += term_sentiment['objective']
            terms_count += 1

    if not terms_count:
        return None

    sentence_sentiment['positive'] /= terms_count
    sentence_sentiment['negative'] /= terms_count
    sentence_sentiment['objective'] /= terms_count

    return sentence_sentiment


def find_text_sentiment(text, greek_lexicon):
    doc = nlp(text)
    text_sentiment = {'positive': 0, 'negative': 0, 'objective': 0}
    sentences_count = 0

    for sentence in doc.sents:
        sentence_clean = unicode(cleaner.clean_text(sentence.text)['text'], 'utf-8') # TO IMPLEMENT
        sentence_document = nlp(sentence_clean)
        sentence_sentiment = find_sentence_sentiment(sentence_document, greek_lexicon)

        if sentence_sentiment:            
            text_sentiment['positive'] += sentence_sentiment['positive']
            text_sentiment['negative'] += sentence_sentiment['negative']
            text_sentiment['objective'] += sentence_sentiment['objective']
            sentences_count += 1

    if not sentences_count:
        return None

    text_sentiment['positive'] /= sentences_count
    text_sentiment['negative'] /= sentences_count
    text_sentiment['objective'] /= sentences_count
    max_score = max(text_sentiment['positive'], text_sentiment['negative'], text_sentiment['objective'])

    # Priority is given first to negative, then to positive, and lastly to objective
    if max_score == text_sentiment['negative']:
        text_sentiment['majority'] = 'negative'
    elif max_score == text_sentiment['positive']:
        text_sentiment['majority'] = 'positive'
    else:
        text_sentiment['majority'] = 'objective'
    
    return text_sentiment


def print_text_sentiment(text, text_sentiment):
    if not text_sentiment:
        print("No sentiment found.")
        return
    print("\nText: {}\n".format(text.encode('utf-8')))
    print("Sentiment: {}\n".format(text_sentiment['majority']))
    print("Avg Positive Score: {}".format(round(text_sentiment['positive'], 3)))
    print("Avg Negative Score: {}".format(round(text_sentiment['negative'], 3)))
    print("Avg Objective Score: {}\n".format(round(text_sentiment['objective'], 3)))


def test_examples(greek_lexicon):
    examples = []
    examples.append(u'<b>Η άπληστη πολυεθνική Πρόκτερ & Γκαμπλ ανέλαβε να ολοκληρώσει τη βρωμοδουλειά '\
        u'με το σκάνδαλο της Τραπέζης Κρήτης. 2 δεκαετίες μετά ο γερμανοαμερικανικός κολοσσός μπαίνει δυναμικά '\
        u'στο χορό των δημοτικών & νομαρχιακών εκλογών χρηματοδοτώντας τη προεκλογική εκστρατεία του Κώστα Νιζάμη '\
        u'για τη δημαρχία του πρώτου λιμανιού της χώρας.</b>')
    examples.append(u'RT @enikos_gr: Αρνείται κατηγορηματικά τη διαρροή για την Huawei ο τέως υπουργός Άμυνας '\
        u'της Βρετανίας https://t.co/ozowmea5xR')
    examples.append(u'Τα ολιγοπώλια των τραπεζών. Με το έτσι θέλω, χωρίς να με ρωτήσουν, η Τράπεζα Πειραιώς '\
        u'μου πήρε 6 ευρώ για έκδοση νέας χρεωστικής κάρτας... – ενοχλημένος')

    for text in examples:
        text_sentiment = find_text_sentiment(text, greek_lexicon)
        print_text_sentiment(text, text_sentiment)


def cross_validate(greek_lexicon):
    sentiment_dict = {
        1: 'positive',
        -1: 'negative',
        0: 'objective'
    }

    data = json.load(open("test_data/test_nbg.json", 'r'))

    with open("test_results/nbg_results.csv", 'w') as results_file:
        results_writer = csv.writer(results_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        results_writer.writerow(['text', 'user_sentiment', 'lexicon_sentiment', 'positive', 'negative', 'objective'])

        for post in data['posts']:
            if 'was_sentiment' not in post['analysis'] or not post.get('text').strip():
                continue
            try:
                user_sentiment = sentiment_dict[post['analysis']['sentiment']]
                lexicon_sentiment = find_text_sentiment(post['text'], greek_lexicon)
                if not user_sentiment:
                    user_sentiment = None
                if not lexicon_sentiment:
                    lexicon_sentiment = {
                        'positive': None,
                        'negative': None,
                        'objective': None,
                        'majority': None
                    }           

                results_writer.writerow([post['text'].encode('utf-8'), user_sentiment, lexicon_sentiment['majority'], lexicon_sentiment['positive'], lexicon_sentiment['negative'], lexicon_sentiment['objective']])
            except:
                pass
    
    with open("test_results/nbg_results.csv", 'r') as results_file:
        csv_reader = csv.DictReader(results_file, delimiter=',')
        matches = 0
        posts = 0

        for row in csv_reader:
            if not row['user_sentiment'] or not row['lexicon_sentiment']:
                continue
            posts += 1
            if row['user_sentiment'] == row['lexicon_sentiment']:
                matches += 1

    if not posts:
        return
    agreement_rate = (matches / float(posts)) * 100
    print("Agreement Rate of Cross-Validation: {} %".format(round(agreement_rate, 2)))          
    

def main():
    greek_sentiment_terms = settings.MONGO_CLIENT.lexicondb.greek_sentiment_terms.find({}, {'sentiment': 1})
    greek_lexicon = init_greek_lexicon(greek_sentiment_terms)

    test_examples(greek_lexicon)
    cross_validate(greek_lexicon)


if __name__ == '__main__':

    main()
