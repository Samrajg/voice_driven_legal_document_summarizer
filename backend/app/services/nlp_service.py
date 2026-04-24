import os
import re
import requests
import pandas as pd
from transformers import pipeline, BartTokenizer
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
    MODEL_NAME = "sshleifer/distilbart-cnn-12-6"
    tokenizer = BartTokenizer.from_pretrained(MODEL_NAME)
    summarizer = pipeline("summarization", model=MODEL_NAME, tokenizer=tokenizer, device=-1)
except Exception as e:
    print(f"Warning: Could not load summarizer, error: {e}")
    summarizer = None
    tokenizer = None

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

def parse_instruction(instruction: str) -> dict:
    cfg = {}
    if not instruction:
        instruction = "summarize"
    text = instruction.lower().strip()

    m = re.search(r"(\d+)\s*words?", text)
    cfg["words"] = int(m.group(1)) if m else None

    m = re.search(r"(\d+)\s*para(?:graph)?s?", text)
    cfg["paragraphs"] = int(m.group(1)) if m else None

    m = re.search(r"(\d+)\s*sentences?", text)
    cfg["sentences"] = int(m.group(1)) if m else None

    m = re.search(r"(\d+)\s*(?:points?|lines?|items?|facts?|bullets?)", text)
    cfg["points"] = int(m.group(1)) if m else None

    if any(w in text for w in ["bullet", "point", "list", "item", "line"]):
        cfg["format"] = "bullets"
    elif cfg.get("paragraphs"):
        cfg["format"] = "paragraphs"
    else:
        cfg["format"] = "prose"

    if any(w in text for w in ["eli5", "explain like", "simple", "layman", "easy"]):
        cfg["style"] = "simple"
    elif any(w in text for w in ["key takeaway", "main point", "highlight", "important"]):
        cfg["style"] = "takeaways"
    elif any(w in text for w in ["tldr", "tl;dr", "short", "brief", "quick"]):
        cfg["style"] = "brief"
    elif any(w in text for w in ["detail", "technical", "expert", "thorough"]):
        cfg["style"] = "detailed"
    else:
        cfg["style"] = "standard"

    return cfg

def chunk_by_tokens(text: str, chunk_size: int = 800, overlap: int = 50) -> list:
    if not tokenizer: return [text[:3000]]
    tokens = tokenizer.encode(text, add_special_tokens=False)
    chunks = []
    i = 0
    while i < len(tokens):
        chunk_tokens = tokens[i:i + chunk_size]
        chunk_text = tokenizer.decode(chunk_tokens, skip_special_tokens=True)
        chunks.append(chunk_text)
        i += chunk_size - overlap
    return chunks

def summarize_with_hf(text: str, min_len: int = 60, max_len: int = 200) -> str:
    if not summarizer: return text[:500] + "..."
    chunks = chunk_by_tokens(text, chunk_size=800, overlap=50)
    summaries = []

    for i, chunk in enumerate(chunks[:5]):
        if len(chunk.strip()) < 100:
            continue
        try:
            result = summarizer(chunk, max_length=max_len, min_length=min(min_len, max_len - 10), do_sample=False, truncation=True)
            summaries.append(result[0]["summary_text"])
        except Exception as e:
            print("Summarization chunk error:", e)

    if not summaries:
        return "Could not generate summary."

    combined = " ".join(summaries)
    if len(summaries) > 1 and tokenizer:
        combined_tokens = tokenizer.encode(combined, add_special_tokens=False)
        if len(combined_tokens) > 800:
            combined = tokenizer.decode(combined_tokens[:800], skip_special_tokens=True)
        try:
            final = summarizer(combined, max_length=max_len, min_length=min_len, do_sample=False, truncation=True)
            return final[0]["summary_text"]
        except Exception as e:
            print("Final summarization pass error:", e)

    return combined

def extract_sentences_from_doc(text: str, n: int) -> list:
    raw_sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    cleaned = [s.strip() for s in raw_sentences if len(s.strip().split()) >= 6]
    if not cleaned: return []
    if len(cleaned) >= n:
        step = len(cleaned) / n
        return [cleaned[int(i * step)] for i in range(n)]
    return cleaned

def apply_constraints(summary: str, cfg: dict, raw_text: str = "") -> str:
    sentences = re.split(r'(?<=[.!?])\s+', summary.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    if cfg.get("points"):
        n = cfg["points"]
        doc_sentences = extract_sentences_from_doc(raw_text, n) if raw_text else []
        if doc_sentences:
            numbered = [f"{i+1}. {s}" for i, s in enumerate(doc_sentences)]
        else:
            numbered = [f"{i+1}. {s}" for i, s in enumerate(sentences[:n])]
        while len(numbered) < n:
            numbered.append(f"{len(numbered)+1}. (Refer to document for more details)")
        return "\n".join(numbered)

    if cfg.get("sentences"):
        sentences = sentences[:cfg["sentences"]]
        summary = " ".join(sentences)

    if cfg.get("words"):
        summary = " ".join(summary.split()[:cfg["words"]])
        if not summary.endswith((".", "!", "?")):
            summary += "."

    if cfg.get("format") == "bullets":
        summary = "\n".join(f"  - {s}" for s in sentences[:10] if s)
    elif cfg.get("format") == "paragraphs" and cfg.get("paragraphs"):
        n = cfg["paragraphs"]
        per = max(1, len(sentences) // n)
        paras = [" ".join(sentences[i*per:(i+1)*per]) for i in range(n)]
        summary = "\n\n".join(p for p in paras if p)

    if cfg.get("style") == "simple":
        summary = "In simple words:\n\n" + summary
    elif cfg.get("style") == "takeaways":
        summary = "Key Takeaways:\n\n" + "\n".join(f"  - {s}" for s in sentences[:5] if s)
    elif cfg.get("style") == "brief":
        summary = sentences[0] if sentences else summary

    return summary.strip()

def analyze_text(text, command=None):
    if not text or len(text.strip()) < 50:
        return {
            "summary": "Could not extract enough text.",
            "simplified": []
        }
        
    cfg = parse_instruction(command)
    
    if cfg.get("words"):
        max_len = max(50, min(cfg["words"] * 2, 300))
        min_len = max(20, cfg["words"] // 2)
    elif cfg["style"] == "brief":
        max_len, min_len = 60, 20
    elif cfg["style"] == "detailed":
        max_len, min_len = 300, 100
    elif cfg.get("points"):
        max_len = min(cfg["points"] * 40, 400)
        min_len = min(cfg["points"] * 15, 150)
    else:
        max_len, min_len = 180, 60

    raw_summary = summarize_with_hf(text, min_len=min_len, max_len=max_len)
    
    if cfg.get("style") == "simple":
        raw_summary = simplify_legal_text(raw_summary)

    final_output = apply_constraints(raw_summary, cfg, raw_text=text)

    return {
        "summary": final_output,
        "parameters": cfg,
        "raw_base": raw_summary
    }

def get_answer(question, document_text):
    if not document_text or len(document_text.strip()) < 50:
        return "Not enough text in document to answer questions."
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
            prompt = f"Context from legal document:\n{document_text[:10000]}\n\nUser Question: {question}\n\nProvide a helpful, precise answer based on the document context."
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print("Gemini API error:", e)
            # Fallback to tf-idf
    
    sentences = sent_tokenize(document_text)
    if not sentences:
        return "No clear sentences found."
        
    all_sentences = sentences + [question]
    vectorizer = TfidfVectorizer().fit_transform(all_sentences)
    similarity = cosine_similarity(vectorizer[-1], vectorizer[:-1])
    index = similarity.argmax()
    return sentences[index]
