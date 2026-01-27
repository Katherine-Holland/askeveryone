import re
from typing import Dict, Any, List

FRESHNESS = ["today","what's happening","latest", "trending", "what is", "breaking","right now", "who is","now","current","this week","just announced","as of","price","stock","who won","still"]
CITATIONS = ["sources","cite","citation","links","reference","according to","evidence","study","paper","journal","references"]
LOCAL = ["near me","closest","open now","directions","postcode","zip","within","miles","km","in london","in manchester"]
HOWTO = ["how do i","how to","steps","guide","tutorial","setup","install","configure","fix","troubleshoot"]
CODING = ["python","javascript","typescript","node","api","sdk","sql","docker","kubernetes","aws","terraform","git","exception","error:","traceback"]
MATH = ["calculate","probability","optimize","regression","sharpe","volatility","backtest","variance","expected value"]
WRITING = ["rewrite","edit","improve","make it sound","tone","copy","landing page","headline","email","shorter","more persuasive"]
CREATIVE = ["brainstorm","ideas","names","story","script","joke","poem"]
RECO = ["recommend","best","top","which should i","vs","versus","compare"]
SENSITIVE = ["diagnose","symptoms","medication","legal advice","lawsuit","tax advice","invest","loan","debt","suicide","weapon"]

def _contains_any(q: str, terms: List[str]) -> bool:
    ql = q.lower()
    return any(t in ql for t in terms)

def extract_features(query: str) -> Dict[str, bool]:
    ql = query.lower()
    code_like = ("```" in query) or ("traceback" in ql) or bool(re.search(r"\bFile \"|Exception\b|Error:\b", query))
    return {
        "freshness": _contains_any(query, FRESHNESS),
        "citations": _contains_any(query, CITATIONS),
        "local": _contains_any(query, LOCAL) or bool(re.search(r"\bin\s+[A-Z][a-z]+", query)),
        "how_to": _contains_any(query, HOWTO),
        "coding": _contains_any(query, CODING) or code_like,
        "math_quant": _contains_any(query, MATH),
        "writing": _contains_any(query, WRITING),
        "creative": _contains_any(query, CREATIVE),
        "recommendation": _contains_any(query, RECO),
        "sensitive": _contains_any(query, SENSITIVE),
    }

def pre_route(features: Dict[str, bool], query: str) -> Dict[str, Any]:
    # returns hints + whether to short-circuit router
    reasons = []
    if features["sensitive"]:
        reasons.append("SENSITIVE_DOMAIN")
        return {"short_circuit": False, "pre_intent_hint": "SENSITIVE_GUARDED", "pre_multi_call_hint": False, "pre_reason_codes": reasons}

    if features["coding"] and len(query) > 30:
        reasons += ["CODE_PRESENT"]
        multi = ("traceback" in query.lower()) or ("error" in query.lower())
        return {"short_circuit": True, "pre_intent_hint": "CODING_TECH", "pre_multi_call_hint": multi, "pre_reason_codes": reasons}

    if features["local"]:
        reasons += ["LOCAL_INTENT"]
        multi = features["recommendation"]
        return {"short_circuit": True, "pre_intent_hint": "LOCAL_NEAR_ME", "pre_multi_call_hint": multi, "pre_reason_codes": reasons}

    if features["citations"]:
        reasons += ["NEEDS_CITATIONS"]
        return {"short_circuit": True, "pre_intent_hint": "WEB_RESEARCH_CITATIONS", "pre_multi_call_hint": True, "pre_reason_codes": reasons}

    if features["freshness"] and not features["coding"]:
        reasons += ["FRESHNESS_TERMS"]
        return {"short_circuit": True, "pre_intent_hint": "LIVE_FRESH", "pre_multi_call_hint": True, "pre_reason_codes": reasons}

    return {"short_circuit": False, "pre_intent_hint": None, "pre_multi_call_hint": None, "pre_reason_codes": reasons}
