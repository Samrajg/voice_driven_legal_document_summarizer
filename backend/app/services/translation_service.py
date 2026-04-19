from deep_translator import GoogleTranslator

def translate_text(text, target_lang):
    """
    Translate text using deep-translator (Google Translator backend for MVP).
    Supported target_langs for India: 'ta' (Tamil), 'hi' (Hindi), 'ml' (Malayalam), 'te' (Telugu)
    """
    if not text or target_lang == 'en':
        return text
        
    try:
        translator = GoogleTranslator(source='auto', target=target_lang)
        # Deep translator has a length limit per request (usually 5k chars)
        # For MVP, we will only translate summaries and short descriptions safely.
        
        if len(text) > 4000:
            chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
            translated_chunks = []
            for chunk in chunks:
                translated_chunks.append(translator.translate(chunk))
            return " ".join(translated_chunks)
            
        return translator.translate(text)
    except Exception as e:
        print(f"Translation error: {e}")
        return text # Fallback to original text

def translate_analysis(analysis_result, target_lang):
    """Translates the analysis fields for the frontend."""
    if target_lang == 'en':
        return analysis_result
        
    if getattr(analysis_result, 'summary', None):
        analysis_result.summary = translate_text(analysis_result.summary, target_lang)
        
    if getattr(analysis_result, 'risks_json', None):
        for risk in analysis_result.risks_json:
            risk['description'] = translate_text(risk['description'], target_lang)
            
    if getattr(analysis_result, 'simplified_clauses_json', None):
        for clause in analysis_result.simplified_clauses_json:
            clause['simple'] = translate_text(clause['simple'], target_lang)
            
    return analysis_result
