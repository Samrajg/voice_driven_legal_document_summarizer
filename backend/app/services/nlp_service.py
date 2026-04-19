import os
import re
import pandas as pd
from transformers import pipeline
import nltk
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Ensure NLTK punkt is available
try:
    nltk.download('punkt', quiet=True)
except:
    pass

import speech_recognition as sr
try:
    listener = sr.Recognizer()
except Exception as e:
    listener = None

def transcribe_audio_file(file_path):
    if not listener: return ""
    try:
        with sr.AudioFile(file_path) as source:
            audio_data = listener.record(source)
            text = listener.recognize_google(audio_data)
            return text
    except Exception as e:
        print("Transcription failed:", e)
        return ""

# Load summarizer
print("Loading AI Summarization Model...")
try:
    summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
except Exception as e:
    print(f"Warning: Could not load summarizer, error: {e}")
    summarizer = None

# Load legal terms dictionary
LEGAL_TO_PLAIN = {}
try:
    df = pd.read_pickle(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'models', 'legal_terms.pkl'))
    # Extract English Simple Meaning
    # Column 0 is Index, 1 is Legal Term, 2 is Tamil, 3 is English
    for _, row in df.dropna().iterrows():
        legal_term = str(row.iloc[1]).strip().lower()
        simple_term = str(row.iloc[3]).strip().lower()
        if legal_term and simple_term:
            LEGAL_TO_PLAIN[legal_term] = simple_term
except Exception as e:
    print(f"Error loading legal_terms.pkl: {e}")
    # Fallback to defaults
    LEGAL_TO_PLAIN = {
        "herein": "in this document", "thereof": "of it", "hereby": "by this",
        "aforementioned": "mentioned above", "whereas": "because",
        "notwithstanding": "even though", "pursuant to": "according to",
        "stipulated": "agreed", "indemnify": "protect from loss",
        "breach": "breaking the agreement", "liable": "legally responsible",
        "jurisdiction": "legal authority", "shall": "must", "may": "can",
        "termination": "ending", "renewal": "extension", "amendment": "change",
    }

def simplify_legal_text(text):
    if not text:
        return text
    simplified = text
    for legal, plain in LEGAL_TO_PLAIN.items():
        # Only replace if alphabet boundary matches
        pattern = r"\b" + re.escape(legal) + r"\b"
        simplified = re.sub(pattern, plain, simplified, flags=re.IGNORECASE)
    return simplified

def break_into_points(text):
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    bullets = ""
    for s in sentences[:12]:
        if len(s) > 180:
            s = s[:180] + "..."
        bullets += f"• {s}\n"
    return bullets

def parse_command(command):
    if not command or command.strip() == "":
        return {"mode": "explain", "target_words": 150, "style": "simple_bullets"}
    
    cmd = command.lower()
    
    # Extract requested word count
    length_match = re.search(r'(\d{1,4})\s*(?:word|words)', cmd)
    target_words = int(length_match.group(1)) if length_match else 150
    
    # Detect mode
    if any(w in cmd for w in ["elaborate", "detailed", "long", "explain fully", "more detail", "in detail"]):
        mode = "elaborate"
        target_words = max(target_words, 400)
    elif any(w in cmd for w in ["summarize", "summary", "short", "brief"]):
        mode = "summarize"
        target_words = min(target_words, 120)
    else:
        mode = "explain"
    
    # Detect style
    if any(w in cmd for w in ["bullet", "bullets", "points"]):
        style = "bullets"
    elif any(w in cmd for w in ["simple", "easy", "plain", "like im 15", "beginner"]):
        style = "simple"
    elif any(w in cmd for w in ["technical", "legal", "formal"]):
        style = "technical"
    else:
        style = "simple_bullets"
    
    return {"mode": mode, "target_words": target_words, "style": style}

def analyze_text(text, command=None):
    """
    Main NLP entry point matching the user's process_summary logic.
    """
    if not text or len(text.strip()) < 50:
        return {
            "summary": "Could not extract enough text.",
            "simplified": []
        }
        
    params = parse_command(command)
    
    # Summarize base
    base_summary = text[:200] + "..." # Fallback
    if summarizer:
        try:
            chunk = text[:1600]
            result = summarizer(chunk, max_length=280, min_length=60, do_sample=False)
            base_summary = result[0]["summary_text"]
        except Exception as e:
            print("Summarization failed:", e)

    if params["mode"] == "elaborate":
        long_text = simplify_legal_text(text[:4500])
        easy = break_into_points(long_text) + "\n\n" + base_summary
    elif params["style"] == "bullets" or params["style"] == "simple_bullets":
        easy = break_into_points(simplify_legal_text(base_summary))
    else:
        easy = simplify_legal_text(base_summary)
        
    words = easy.split()
    if len(words) > params["target_words"] + 50:
        easy = " ".join(words[:params["target_words"] + 30]) + "..."
        
    return {
        "summary": easy,
        "parameters": params,
        "raw_base": base_summary
    }

def get_answer(question, document_text):
    if not document_text or len(document_text.strip()) < 50:
        return "Not enough text in document to answer questions."
    
    sentences = sent_tokenize(document_text)
    if not sentences:
        return "No clear sentences found."
        
    all_sentences = sentences + [question]
    vectorizer = TfidfVectorizer().fit_transform(all_sentences)
    similarity = cosine_similarity(vectorizer[-1], vectorizer[:-1])
    index = similarity.argmax()
    return sentences[index]
