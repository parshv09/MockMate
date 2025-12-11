# interviewapp/nlp_utils.py
import spacy
nlp = spacy.load("en_core_web_sm")
FILLERS = {"um","uh","like","you know","hmm"}

def analyze_transcript(text, question):
    if not text:
        return {"score": 0, "feedback": "No answer provided."}
    doc = nlp(text)
    tokens = [t.text.lower() for t in doc]
    fillers = sum(1 for t in tokens if t in FILLERS)
    keywords = []
    matched = 0
    if question and question.keywords:
        keywords = [k.strip().lower() for k in question.keywords.split(',') if k.strip()]
        matched = sum(1 for k in keywords if k in text.lower())
    keyword_score = int((matched / max(1, len(keywords))) * 40) if keywords else 20
    length_score = min(20, max(5, len(text.split())))
    grammar_score = 25 - min(10, fillers * 2)
    filler_penalty = min(15, fillers * 3)
    total = max(0, keyword_score + length_score + grammar_score - filler_penalty)
    feedback = f"Keywords matched: {matched}/{len(keywords) if keywords else 0}."
    if fillers:
        feedback += f" Reduce filler words: {fillers} found."
    if len(text.split()) < 10:
        feedback += " Add more detail."
    return {"score": int(total), "feedback": feedback}
