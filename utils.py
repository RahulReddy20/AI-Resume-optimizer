import re
import nltk
import spacy
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Load NLP models
try:
    nlp = spacy.load("en_core_web_md")
except:
    print("Please download the spaCy model: python -m spacy download en_core_web_md")
    exit(1)

try:
    stop_words = set(stopwords.words('english'))
except:
    print("Please download NLTK stopwords: python -c \"import nltk; nltk.download('stopwords')\"")
    exit(1)


def preprocess_text(text):
    """Clean and preprocess text for analysis"""
    # Convert to lowercase
    text = text.lower()

    # Remove special characters and numbers
    text = re.sub(r'[^a-zA-Z\s]', '', text)

    # Tokenize and remove stopwords
    tokens = [word for word in text.split() if word not in stop_words]

    return ' '.join(tokens)


def extract_keywords(text, top_n=20):
    """Extract most important keywords from text using spaCy"""
    doc = nlp(text)

    # Extract nouns, proper nouns, and adjectives as keywords
    keywords = []
    for token in doc:
        if token.pos_ in ['NOUN', 'PROPN', 'ADJ'] and token.text.lower() not in stop_words:
            keywords.append(token.text.lower())

    # Count occurrences
    keyword_freq = {}
    for word in keywords:
        if word in keyword_freq:
            keyword_freq[word] += 1
        else:
            keyword_freq[word] = 1

    # Sort by frequency
    sorted_keywords = sorted(keyword_freq.items(),
                             key=lambda x: x[1], reverse=True)

    # Return top N keywords
    return [word for word, freq in sorted_keywords[:top_n]]


def calculate_similarity(text1, text2):
    """Calculate cosine similarity between two texts"""
    # Preprocess texts
    text1_processed = preprocess_text(text1)
    text2_processed = preprocess_text(text2)

    # Create vectors
    vectorizer = CountVectorizer().fit_transform(
        [text1_processed, text2_processed])
    vectors = vectorizer.toarray()

    # Calculate cosine similarity
    return cosine_similarity([vectors[0]], [vectors[1]])[0][0]


def identify_missing_skills(job_description, resume_text):
    """Identify skills in job description that are missing from resume"""
    job_keywords = set(extract_keywords(job_description, top_n=30))
    resume_keywords = set(extract_keywords(resume_text, top_n=50))

    return list(job_keywords - resume_keywords)
