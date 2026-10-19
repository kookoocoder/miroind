"""Deterministic, offline text stress testing for the MiroInd MVP.

This module intentionally has no connection to the graph, simulation, report,
Zep, OASIS, or LLM services.  It provides a small rules-and-templates engine
that is inspectable and reproducible on an offline installation.
"""

from __future__ import annotations

import copy
import json
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any, Mapping

from ..config import Config


RUN_ID_PATTERN = re.compile(r"^miroind_[a-f0-9]{24}$")


class MiroIndValidationError(ValueError):
    """A safe, client-facing validation error for the MiroInd contract."""

    def __init__(self, fields: dict[str, str]):
        self.fields = fields
        super().__init__("MiroInd payload validation failed")


# A short alias is useful to callers that want a generic service validation
# error without coupling to the longer public class name.
ValidationError = MiroIndValidationError


# The templates are deliberately research lenses.  They describe questions a
# researcher can test, rather than demographic assumptions about Indian users.
PERSONA_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "id": "value_conscious_decision_maker",
        "label": "Value-conscious decision-maker",
        "label_hi": "मूल्य-सचेत निर्णयकर्ता",
        "research_lens": "Compares stated value, total cost, and trade-offs before acting.",
        "research_lens_hi": "कार्रवाई से पहले बताए गए लाभ, कुल लागत और विकल्पों की तुलना करता है।",
        "priorities": ("value", "clarity"),
    },
    {
        "id": "first_time_digital_adopter",
        "label": "First-time digital adopter",
        "label_hi": "पहली बार डिजिटल सेवा अपनाने वाला",
        "research_lens": "Looks for a clear first step, understandable instructions, and low friction.",
        "research_lens_hi": "स्पष्ट पहला कदम, समझने योग्य निर्देश और कम झंझट खोजता है।",
        "priorities": ("clarity", "access"),
    },
    {
        "id": "privacy_and_trust_evaluator",
        "label": "Privacy and trust evaluator",
        "label_hi": "गोपनीयता और भरोसा परखने वाला",
        "research_lens": "Checks evidence, data handling, consent, and whether promises are verifiable.",
        "research_lens_hi": "सबूत, डेटा प्रबंधन, सहमति और वादों की जांच करता है।",
        "priorities": ("trust", "evidence"),
    },
    {
        "id": "time_poor_professional",
        "label": "Time-poor professional",
        "label_hi": "समय-सचेत पेशेवर",
        "research_lens": "Assesses whether the message quickly explains the benefit and next action.",
        "research_lens_hi": "देखता है कि संदेश लाभ और अगला कदम जल्दी समझाता है या नहीं।",
        "priorities": ("clarity", "convenience"),
    },
    {
        "id": "community_informed_researcher",
        "label": "Community-informed researcher",
        "label_hi": "समुदाय-सूचित शोधकर्ता",
        "research_lens": "Seeks context, local relevance, and signals that can be checked with peers.",
        "research_lens_hi": "संदर्भ, स्थानीय प्रासंगिकता और साथियों से जांचे जा सकने वाले संकेत खोजता है।",
        "priorities": ("local_fit", "evidence"),
    },
    {
        "id": "language_access_navigator",
        "label": "Language-access navigator",
        "label_hi": "भाषा-पहुंच परखने वाला",
        "research_lens": "Tests whether wording, idioms, and instructions travel well across language contexts.",
        "research_lens_hi": "परखता है कि शब्द, मुहावरे और निर्देश अलग भाषा संदर्भों में समझ आते हैं या नहीं।",
        "priorities": ("language", "clarity"),
    },
    {
        "id": "evidence_checker",
        "label": "Evidence checker",
        "label_hi": "सबूत जांचने वाला",
        "research_lens": "Separates a useful claim from an absolute claim and looks for proof.",
        "research_lens_hi": "उपयोगी दावे और पूर्ण दावे में अंतर करके प्रमाण खोजता है।",
        "priorities": ("evidence", "trust"),
    },
    {
        "id": "convenience_oriented_buyer",
        "label": "Convenience-oriented buyer",
        "label_hi": "सुविधा-केंद्रित खरीदार",
        "research_lens": "Looks for a simple, relevant outcome without unnecessary steps or pressure.",
        "research_lens_hi": "अनावश्यक चरणों या दबाव के बिना सरल और प्रासंगिक परिणाम खोजता है।",
        "priorities": ("convenience", "clarity"),
    },
    {
        "id": "risk_sensitive_essential_buyer",
        "label": "Risk-sensitive essential buyer",
        "label_hi": "जोखिम-सचेत आवश्यक खरीदार",
        "research_lens": "Prioritizes reversibility, transparent terms, and avoiding costly surprises.",
        "research_lens_hi": "वापसी की सुविधा, पारदर्शी शर्तों और महंगे आश्चर्यों से बचने को प्राथमिकता देता है।",
        "priorities": ("trust", "value"),
    },
    {
        "id": "repeat_customer_loyalty_lens",
        "label": "Repeat-customer loyalty lens",
        "label_hi": "दोबारा ग्राहक बनने का दृष्टिकोण",
        "research_lens": "Checks whether the message supports a credible long-term relationship, not just a click.",
        "research_lens_hi": "देखता है कि संदेश केवल क्लिक नहीं बल्कि विश्वसनीय दीर्घकालिक संबंध बनाता है या नहीं।",
        "priorities": ("trust", "relationship"),
    },
)


MAX_LENGTHS = {
    "brand.name": 120,
    "brand.positioning": 500,
    "brand.tone": 160,
    "brand.audience_relationship": 300,
    "brand.red_lines[]": 160,
    "brand.preferred_vocabulary[]": 100,
    "asset.title": 200,
    "asset.content": 20_000,
    "audience.region": 120,
    "audience.language": 80,
    "audience.age_band": 80,
    "audience.occupation": 120,
    "audience.city_tier": 80,
    "audience.income_band": 80,
}


TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "report_title": "MiroInd text stress-test report",
        "scenario": "Scenario",
        "audience_summary": "Audience summary",
        "overall_image_impact_direction": "Overall image impact direction",
        "positive_reactions": "Positive reactions",
        "negative_reactions": "Negative reactions",
        "mixed_reactions": "Mixed reactions",
        "risk_points": "Risk points",
        "misunderstandings": "Potential misunderstandings",
        "persona_reactions": "Persona reactions",
        "disagreements": "Disagreements",
        "recommendations": "Recommendations",
        "rewrite_options": "Rewrite options",
        "assumptions": "Assumptions",
        "uncertainty": "Uncertainty",
        "limitations": "Limitations",
        "usage_metadata": "Usage metadata",
        "positive": "positive",
        "negative": "negative",
        "mixed": "mixed",
        "neutral": "neutral",
        "scenario_summary": "{brand} presents a {tone} message for {relationship} with the audience.",
        "audience_summary_text": "The lens covers {region}, {language}, {age}, {occupation}, {city}, and {income}.",
        "positive_default": "The message gives a concrete starting point for evaluating the offer.",
        "positive_value": "The stated benefit can help readers compare the offer with their needs.",
        "positive_clarity": "The short-post format makes the next action relatively easy to scan.",
        "positive_language": "The wording can be adapted to the audience's language context without changing the core idea.",
        "negative_default": "The message may leave important decision criteria unstated.",
        "negative_risk": "The signal {signal} may reduce confidence until its terms or evidence are clear.",
        "mixed_default": "Readers may appreciate the direct message while still asking for context or proof.",
        "persona_reaction": "This lens is likely to {positive} while checking {check}.",
        "check_value": "value and total cost",
        "check_clarity": "the first step and wording",
        "check_trust": "data handling and proof",
        "check_local_fit": "local relevance and context",
        "check_language": "language fit and idioms",
        "check_evidence": "evidence for the claim",
        "check_convenience": "effort and convenience",
        "check_relationship": "long-term credibility",
        "positive_action": "see a useful starting point",
        "positive_benefit": "recognize a relevant benefit",
        "concern_context": "the missing context",
        "concern_proof": "the proof behind the promise",
        "concern_language": "whether the wording travels across contexts",
        "disagreement_text": "The value and convenience lenses may respond positively, while trust and evidence lenses ask for clearer proof.",
        "recommendation_clarity": "State the user benefit and the next step in one plain sentence.",
        "recommendation_terms": "Add the material price, eligibility, time window, or other terms behind the offer.",
        "recommendation_proof": "Replace absolute claims with a specific, checkable proof point.",
        "recommendation_language": "Review idioms and provide a language-appropriate version for the supplied audience.",
        "rewrite_clarity": "Clarity-first",
        "rewrite_trust": "Trust-first",
        "rewrite_clarity_text": "{brand}: {positioning}. {content}",
        "rewrite_trust_text": "{brand}: {content} Terms and evidence should be easy to verify.",
        "rewrite_clarity_reason": "Makes the benefit and positioning easier to scan.",
        "rewrite_trust_reason": "Creates room for transparent terms and evidence.",
        "assumption_1": "The supplied audience fields describe a research context, not a claim about every person in that group.",
        "assumption_2": "The asset is evaluated as a short text post and not as a complete campaign.",
        "uncertainty_1": "Reactions are directional hypotheses; real response depends on placement, history, and execution.",
        "uncertainty_2": "The supplied audience language is used as a fit signal and is not a measure of language proficiency.",
        "limitation_1": "This offline engine uses deterministic keyword and template rules; it does not infer sentiment from a learned model.",
        "limitation_2": "Hindi output uses concise deterministic translations and should be reviewed by a fluent reader for nuance.",
        "quality_note": "Hindi labels and concise templates are deterministic translations; review language quality and cultural nuance before publication.",
        "no_risk": "No configured risk signal was detected in the supplied text and audience context.",
        "risk_pricing_label": "Pricing or urgency",
        "risk_trust_label": "Trust or privacy",
        "risk_claims_label": "Exaggerated claims",
        "risk_language_label": "Regional or language fit",
        "risk_pricing_why": "Price pressure or urgency can hide eligibility, cost, or time-window details.",
        "risk_trust_why": "Trust-sensitive readers may need clear consent, data handling, or evidence details.",
        "risk_claims_why": "Absolute promises can create expectations that the message cannot substantiate.",
        "risk_language_why": "A language or regional mismatch can change meaning, tone, or the practical next step.",
        "signal_none": "an unstated decision criterion",
        "signal_pricing": "pricing or urgency wording",
        "signal_trust": "trust or privacy wording",
        "signal_claims": "an absolute claim",
        "signal_language": "a language-fit mismatch",
    },
    "hi": {
        "report_title": "MiroInd टेक्स्ट स्ट्रेस-टेस्ट रिपोर्ट",
        "scenario": "परिदृश्य",
        "audience_summary": "दर्शक सारांश",
        "overall_image_impact_direction": "समग्र छवि प्रभाव दिशा",
        "positive_reactions": "सकारात्मक प्रतिक्रियाएं",
        "negative_reactions": "नकारात्मक प्रतिक्रियाएं",
        "mixed_reactions": "मिश्रित प्रतिक्रियाएं",
        "risk_points": "जोखिम बिंदु",
        "misunderstandings": "संभावित गलतफहमियां",
        "persona_reactions": "पर्सोना प्रतिक्रियाएं",
        "disagreements": "असहमतियां",
        "recommendations": "सुझाव",
        "rewrite_options": "पुनर्लेखन विकल्प",
        "assumptions": "मान्यताएं",
        "uncertainty": "अनिश्चितता",
        "limitations": "सीमाएं",
        "usage_metadata": "उपयोग मेटाडेटा",
        "positive": "सकारात्मक",
        "negative": "नकारात्मक",
        "mixed": "मिश्रित",
        "neutral": "तटस्थ",
        "scenario_summary": "{brand} दर्शकों के साथ {relationship} संबंध के लिए {tone} संदेश प्रस्तुत करता है।",
        "audience_summary_text": "यह दृष्टिकोण {region}, {language}, {age}, {occupation}, {city} और {income} को ध्यान में रखता है।",
        "positive_default": "संदेश प्रस्ताव को परखने के लिए एक ठोस शुरुआती बिंदु देता है।",
        "positive_value": "बताया गया लाभ पाठकों को अपनी जरूरतों से प्रस्ताव की तुलना करने में मदद कर सकता है।",
        "positive_clarity": "छोटे पोस्ट का प्रारूप अगले कदम को जल्दी समझने योग्य बनाता है।",
        "positive_language": "मूल विचार बदले बिना शब्दों को दर्शक की भाषा के अनुसार ढाला जा सकता है।",
        "negative_default": "संदेश निर्णय के लिए जरूरी कुछ मानदंड स्पष्ट नहीं करता।",
        "negative_risk": "{signal} भरोसा घटा सकता है, जब तक उसकी शर्तें या प्रमाण स्पष्ट न हों।",
        "mixed_default": "पाठक सीधे संदेश को पसंद कर सकते हैं, फिर भी संदर्भ या प्रमाण मांग सकते हैं।",
        "persona_reaction": "यह दृष्टिकोण {positive} और साथ ही {check} की जांच करेगा।",
        "check_value": "मूल्य और कुल लागत",
        "check_clarity": "पहला कदम और शब्दों की स्पष्टता",
        "check_trust": "डेटा प्रबंधन और प्रमाण",
        "check_local_fit": "स्थानीय प्रासंगिकता और संदर्भ",
        "check_language": "भाषा की उपयुक्तता और मुहावरे",
        "check_evidence": "दावे के प्रमाण",
        "check_convenience": "मेहनत और सुविधा",
        "check_relationship": "लंबे समय का भरोसा",
        "positive_action": "उपयोगी शुरुआती बिंदु देखेगा",
        "positive_benefit": "प्रासंगिक लाभ पहचान सकेगा",
        "concern_context": "छूटे हुए संदर्भ",
        "concern_proof": "वादे के पीछे का प्रमाण",
        "concern_language": "क्या शब्द अलग संदर्भों में समझ आते हैं",
        "disagreement_text": "मूल्य और सुविधा वाले दृष्टिकोण सकारात्मक हो सकते हैं, जबकि भरोसा और प्रमाण वाले दृष्टिकोण स्पष्ट सबूत मांगेंगे।",
        "recommendation_clarity": "उपयोगकर्ता का लाभ और अगला कदम एक सरल वाक्य में बताएं।",
        "recommendation_terms": "ऑफर की कीमत, पात्रता, समय-सीमा या अन्य जरूरी शर्तें जोड़ें।",
        "recommendation_proof": "पूर्ण दावों को किसी खास और जांचे जा सकने वाले प्रमाण से बदलें।",
        "recommendation_language": "मुहावरों की समीक्षा करें और दिए गए दर्शक के लिए उपयुक्त भाषा संस्करण दें।",
        "rewrite_clarity": "स्पष्टता पहले",
        "rewrite_trust": "भरोसा पहले",
        "rewrite_clarity_text": "{brand}: {positioning}। {content}",
        "rewrite_trust_text": "{brand}: {content} शर्तें और प्रमाण आसानी से जांचे जा सकने चाहिए।",
        "rewrite_clarity_reason": "लाभ और पोजिशनिंग को जल्दी समझने योग्य बनाता है।",
        "rewrite_trust_reason": "पारदर्शी शर्तों और प्रमाण के लिए जगह बनाता है।",
        "assumption_1": "दिए गए दर्शक क्षेत्र को शोध संदर्भ माना गया है, हर व्यक्ति के बारे में दावा नहीं।",
        "assumption_2": "एसेट को पूरे अभियान के बजाय छोटे टेक्स्ट पोस्ट के रूप में परखा गया है।",
        "uncertainty_1": "प्रतिक्रियाएं दिशात्मक परिकल्पनाएं हैं; वास्तविक असर स्थान, इतिहास और निष्पादन पर निर्भर करेगा।",
        "uncertainty_2": "दर्शक की भाषा को फिट संकेत माना गया है, भाषा दक्षता का माप नहीं।",
        "limitation_1": "यह ऑफलाइन इंजन नियत कीवर्ड और टेम्पलेट नियमों का उपयोग करता है; यह सीखा हुआ भावना मॉडल नहीं है।",
        "limitation_2": "हिंदी आउटपुट संक्षिप्त नियत अनुवादों पर आधारित है; सूक्ष्मता के लिए धाराप्रवाह पाठक से समीक्षा कराएं।",
        "quality_note": "हिंदी लेबल और संक्षिप्त टेम्पलेट नियत अनुवाद हैं; प्रकाशन से पहले भाषा गुणवत्ता और सांस्कृतिक सूक्ष्मता की समीक्षा करें।",
        "no_risk": "दिए गए टेक्स्ट और दर्शक संदर्भ में कोई कॉन्फ़िगर किया गया जोखिम संकेत नहीं मिला।",
        "risk_pricing_label": "कीमत या जल्दबाजी",
        "risk_trust_label": "भरोसा या गोपनीयता",
        "risk_claims_label": "बढ़ा-चढ़ाकर किए गए दावे",
        "risk_language_label": "क्षेत्रीय या भाषा उपयुक्तता",
        "risk_pricing_why": "कीमत का दबाव या जल्दबाजी पात्रता, लागत या समय-सीमा छिपा सकती है।",
        "risk_trust_why": "भरोसा-सचेत पाठकों को सहमति, डेटा प्रबंधन या प्रमाण का स्पष्ट विवरण चाहिए।",
        "risk_claims_why": "पूर्ण वादे ऐसी उम्मीदें बना सकते हैं जिन्हें संदेश साबित नहीं कर सकता।",
        "risk_language_why": "भाषा या क्षेत्र का मेल न होने से अर्थ, लहजा या अगला कदम बदल सकता है।",
        "signal_none": "अनकहा निर्णय मानदंड",
        "signal_pricing": "कीमत या जल्दबाजी वाली भाषा",
        "signal_trust": "भरोसे या गोपनीयता वाली भाषा",
        "signal_claims": "पूर्ण दावा",
        "signal_language": "भाषा-फिट का अंतर",
    },
}


RISK_RULES: tuple[dict[str, Any], ...] = (
    {
        "category": "pricing_urgency",
        "label_key": "risk_pricing_label",
        "why_key": "risk_pricing_why",
        "signal_key": "signal_pricing",
        "terms": (
            "₹",
            "rs.",
            "rs ",
            "price",
            "pricing",
            "discount",
            "sale",
            "offer",
            "cashback",
            "emi",
            "free",
            "limited time",
            "last chance",
            "hurry",
            "today only",
            "अब",
            "आज",
            "जल्दी",
            "मुफ़्त",
        ),
    },
    {
        "category": "trust_privacy",
        "label_key": "risk_trust_label",
        "why_key": "risk_trust_why",
        "signal_key": "signal_trust",
        "terms": (
            "privacy",
            "private",
            "personal data",
            "data",
            "otp",
            "aadhaar",
            "secure",
            "security",
            "permission",
            "camera",
            "contacts",
            "गोपनीयता",
            "निजी डेटा",
            "ओटीपी",
            "सुरक्षित",
        ),
    },
    {
        "category": "exaggerated_claims",
        "label_key": "risk_claims_label",
        "why_key": "risk_claims_why",
        "signal_key": "signal_claims",
        "terms": (
            "best",
            "#1",
            "number one",
            "guaranteed",
            "guarantee",
            "100%",
            "zero risk",
            "never",
            "always",
            "instant",
            "miracle",
            "cure",
            "सबसे अच्छा",
            "गारंटी",
            "हमेशा",
            "तुरंत परिणाम",
        ),
    },
)


def get_persona_templates(persona_count: int = 10) -> list[dict[str, Any]]:
    """Return an inspectable, deterministic subset of the persona lenses."""

    if not isinstance(persona_count, int) or isinstance(persona_count, bool):
        raise ValueError("persona_count must be an integer")
    if not 4 <= persona_count <= len(PERSONA_TEMPLATES):
        raise ValueError("persona_count must be between 4 and 10")
    return copy.deepcopy(list(PERSONA_TEMPLATES[:persona_count]))


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_string(
    container: Mapping[str, Any],
    field: str,
    path: str,
    fields: dict[str, str],
) -> str | None:
    if field not in container:
        fields[path] = "is required"
        return None
    value = container[field]
    if not isinstance(value, str):
        fields[path] = "must be a string"
        return None
    if not value.strip():
        fields[path] = "must not be empty"
        return None
    max_length = MAX_LENGTHS.get(path)
    if max_length and len(value) > max_length:
        fields[path] = f"must be at most {max_length} characters"
        return None
    return value.strip()


def _validate_string_list(
    container: Mapping[str, Any],
    field: str,
    path: str,
    fields: dict[str, str],
    *,
    max_items: int,
) -> list[str] | None:
    if field not in container:
        fields[path] = "is required"
        return None
    value = container[field]
    if not isinstance(value, list):
        fields[path] = "must be an array of strings"
        return None
    if len(value) > max_items:
        fields[path] = f"must contain at most {max_items} items"
        return None
    normalized: list[str] = []
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if not isinstance(item, str):
            fields[item_path] = "must be a string"
            continue
        if not item.strip():
            fields[item_path] = "must not be empty"
            continue
        max_length = MAX_LENGTHS[path + "[]"]
        if len(item) > max_length:
            fields[item_path] = f"must be at most {max_length} characters"
            continue
        normalized.append(item.strip())
    return normalized


def validate_payload(payload: Any) -> dict[str, Any]:
    """Validate and normalize an API payload without raising raw type errors."""

    fields: dict[str, str] = {}
    if not isinstance(payload, dict):
        raise MiroIndValidationError({"payload": "must be a JSON object"})

    normalized: dict[str, Any] = {}
    sections = ("brand", "asset", "audience", "config")
    for section in sections:
        value = payload.get(section)
        if not isinstance(value, dict):
            fields[section] = "is required and must be a JSON object"
        else:
            normalized[section] = value

    brand = normalized.get("brand")
    if brand is not None:
        normalized_brand: dict[str, Any] = {}
        for field in (
            "name",
            "positioning",
            "tone",
            "audience_relationship",
        ):
            value = _validate_string(brand, field, f"brand.{field}", fields)
            if value is not None:
                normalized_brand[field] = value
        red_lines = _validate_string_list(
            brand,
            "red_lines",
            "brand.red_lines",
            fields,
            max_items=20,
        )
        preferred_vocabulary = _validate_string_list(
            brand,
            "preferred_vocabulary",
            "brand.preferred_vocabulary",
            fields,
            max_items=30,
        )
        if red_lines is not None:
            normalized_brand["red_lines"] = red_lines
        if preferred_vocabulary is not None:
            normalized_brand["preferred_vocabulary"] = preferred_vocabulary
        normalized["brand"] = normalized_brand

    asset = normalized.get("asset")
    if asset is not None:
        normalized_asset: dict[str, Any] = {}
        asset_type = asset.get("type")
        if asset_type != "text":
            fields["asset.type"] = "must be 'text'"
        else:
            normalized_asset["type"] = asset_type
        for field in ("title", "content"):
            value = _validate_string(asset, field, f"asset.{field}", fields)
            if value is not None:
                normalized_asset[field] = value
        language = asset.get("language")
        if language not in {"en", "hi"}:
            fields["asset.language"] = "must be one of: en, hi"
        else:
            normalized_asset["language"] = language
        normalized["asset"] = normalized_asset

    audience = normalized.get("audience")
    if audience is not None:
        normalized_audience: dict[str, Any] = {}
        for field in (
            "region",
            "language",
            "age_band",
            "occupation",
            "city_tier",
            "income_band",
        ):
            value = _validate_string(audience, field, f"audience.{field}", fields)
            if value is not None:
                normalized_audience[field] = value
        normalized["audience"] = normalized_audience

    config = normalized.get("config")
    if config is not None:
        normalized_config: dict[str, Any] = {}
        report_language = config.get("report_language")
        if report_language not in {"en", "hi"}:
            fields["config.report_language"] = "must be one of: en, hi"
        else:
            normalized_config["report_language"] = report_language
        interaction_format = config.get("interaction_format")
        if interaction_format != "short_post":
            fields["config.interaction_format"] = "must be 'short_post'"
        else:
            normalized_config["interaction_format"] = interaction_format
        persona_count = config.get("persona_count")
        if (
            not isinstance(persona_count, int)
            or isinstance(persona_count, bool)
            or not 4 <= persona_count <= 10
        ):
            fields["config.persona_count"] = "must be an integer between 4 and 10"
        else:
            normalized_config["persona_count"] = persona_count
        budget = config.get("budget")
        if not isinstance(budget, int) or isinstance(budget, bool) or budget < 1:
            fields["config.budget"] = "must be an integer greater than or equal to 1"
        else:
            normalized_config["budget"] = budget
        normalized["config"] = normalized_config

    if fields:
        raise MiroIndValidationError(fields)
    return normalized


def _contains_term(text: str, term: str) -> bool:
    folded_text = text.casefold()
    folded_term = term.casefold()
    if not folded_term.strip():
        return False
    if all(character.isascii() and (character.isalnum() or character.isspace()) for character in term):
        return re.search(r"(?<![a-z0-9])" + re.escape(folded_term.strip()) + r"(?![a-z0-9])", folded_text) is not None
    return folded_term in folded_text


def _signals(text: str, terms: tuple[str, ...]) -> list[str]:
    return [term for term in terms if _contains_term(text, term)]


def _excerpt(text: str, signal: str | None = None, limit: int = 180) -> str:
    if len(text) <= limit:
        return text
    if signal:
        position = text.casefold().find(signal.casefold())
        if position >= 0:
            start = max(0, position - 65)
            return text[start : start + limit].strip()
    return text[:limit].rstrip() + "…"


def _language_key(language: str) -> str:
    folded = language.casefold().strip()
    if folded in {"hi", "hindi", "हिंदी", "हिन्दी"}:
        return "hi"
    if folded in {"en", "english"}:
        return "en"
    return folded


def _t(locale: str, key: str, **values: Any) -> str:
    return TRANSLATIONS[locale][key].format(**values)


def _labels(language: str) -> dict[str, str]:
    keys = (
        "scenario",
        "audience_summary",
        "overall_image_impact_direction",
        "positive_reactions",
        "negative_reactions",
        "mixed_reactions",
        "risk_points",
        "misunderstandings",
        "persona_reactions",
        "disagreements",
        "recommendations",
        "rewrite_options",
        "assumptions",
        "uncertainty",
        "limitations",
        "usage_metadata",
    )
    return {key: _t(language, key) for key in keys}


def _impact_label(language: str, impact: str) -> str:
    return _t(language, impact if impact in {"positive", "negative", "mixed", "neutral"} else "neutral")


def _risk_points(
    *,
    language: str,
    asset_text: str,
    audience: Mapping[str, str],
    asset_language: str,
) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for rule in RISK_RULES:
        signals = _signals(asset_text, rule["terms"])
        if not signals:
            continue
        severity = "high" if len(signals) >= 2 else "medium"
        points.append(
            {
                "category": rule["category"],
                "label": _t(language, rule["label_key"]),
                "signal_key": rule["signal_key"],
                "severity": severity,
                "signals": signals,
                "evidence": _excerpt(asset_text, signals[0]),
                "why_it_matters": _t(language, rule["why_key"]),
            }
        )

    audience_language = _language_key(audience["language"])
    if audience_language in {"en", "hi"} and audience_language != asset_language:
        points.append(
            {
                "category": "regional_language_fit",
                "label": _t(language, "risk_language_label"),
                "severity": "medium",
                "signals": [f"asset={asset_language}", f"audience={audience['language']}"],
                "evidence": f"asset language {asset_language}; audience language {audience['language']}",
                "why_it_matters": _t(language, "risk_language_why"),
            }
        )
    return points


def _unique(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _build_report(payload: Mapping[str, Any]) -> dict[str, Any]:
    brand = payload["brand"]
    asset = payload["asset"]
    audience = payload["audience"]
    config = payload["config"]
    language = config["report_language"]
    asset_text = f"{asset['title']}\n{asset['content']}"
    folded_text = asset_text.casefold()
    risk_points = _risk_points(
        language=language,
        asset_text=asset_text,
        audience=audience,
        asset_language=asset["language"],
    )
    risk_categories = {point["category"] for point in risk_points}
    preferred_matches = [
        word for word in brand["preferred_vocabulary"] if _contains_term(asset_text, word)
    ]
    red_line_matches = [
        line for line in brand["red_lines"] if _contains_term(asset_text, line)
    ]
    benefit_signals = _signals(
        asset_text,
        (
            "simple",
            "easy",
            "help",
            "save",
            "learn",
            "trusted",
            "clear",
            "सरल",
            "आसान",
            "मदद",
            "बचत",
            "भरोसा",
        ),
    )
    positive_score = len(preferred_matches) + len(benefit_signals)
    negative_score = sum(2 if point["severity"] == "high" else 1 for point in risk_points)
    negative_score += len(red_line_matches) * 2
    if not asset["content"].strip():
        negative_score += 2
    if positive_score == 0 and negative_score == 0:
        impact = "neutral"
    elif positive_score >= negative_score + 2:
        impact = "positive"
    elif negative_score >= positive_score + 2:
        impact = "negative"
    else:
        impact = "mixed"

    personas = get_persona_templates(config["persona_count"])
    persona_reactions: list[dict[str, Any]] = []
    positive_reactions: list[str] = []
    negative_reactions: list[str] = []
    mixed_reactions: list[str] = []
    all_priorities = set()

    for persona in personas:
        priorities = set(persona["priorities"])
        all_priorities.update(priorities)
        checks = [
            _t(language, f"check_{priority}")
            for priority in persona["priorities"]
            if f"check_{priority}" in TRANSLATIONS[language]
        ]
        check = " and ".join(checks) if checks else _t(language, "check_clarity")
        concerns: list[str] = []
        if "value" in priorities and "pricing_urgency" in risk_categories:
            concerns.append(_t(language, "concern_context"))
        if ("trust" in priorities or "evidence" in priorities) and (
            {"trust_privacy", "exaggerated_claims"} & risk_categories
        ):
            concerns.append(_t(language, "concern_proof"))
        if "language" in priorities and "regional_language_fit" in risk_categories:
            concerns.append(_t(language, "concern_language"))
        if "local_fit" in priorities and audience["region"]:
            concerns.append(audience["region"])
        if red_line_matches:
            concerns.append("brand red line")
        concerns = _unique(concerns)

        if concerns and (positive_score > 0 or not risk_points):
            persona_impact = "mixed"
        elif concerns:
            persona_impact = "negative"
        else:
            persona_impact = "positive" if positive_score > 0 or not risk_points else "mixed"
        positive_word = (
            _t(language, "positive_benefit")
            if positive_score > 0
            else _t(language, "positive_action")
        )
        reaction = _t(
            language,
            "persona_reaction",
            positive=positive_word,
            check=check,
        )
        if persona_impact == "positive":
            positive_reactions.append(reaction)
        elif persona_impact == "negative":
            negative_reactions.append(reaction)
        else:
            mixed_reactions.append(reaction)
        persona_reactions.append(
            {
                "persona_id": persona["id"],
                "label": persona["label_hi"] if language == "hi" else persona["label"],
                "research_lens": (
                    persona["research_lens_hi"]
                    if language == "hi"
                    else persona["research_lens"]
                ),
                "reaction": reaction,
                "impact": persona_impact,
                "impact_label": _impact_label(language, persona_impact),
                "positive_signals": _unique(preferred_matches + benefit_signals),
                "concerns": concerns,
                "confidence": "medium",
            }
        )

    if not positive_reactions and impact in {"positive", "neutral"}:
        positive_reactions.append(_t(language, "positive_default"))
    if not negative_reactions and risk_points:
        signal = _t(language, risk_points[0]["signal_key"] if "signal_key" in risk_points[0] else "signal_none")
        negative_reactions.append(_t(language, "negative_risk", signal=signal))
    if not mixed_reactions and impact == "mixed":
        mixed_reactions.append(_t(language, "mixed_default"))
    positive_reactions = _unique(positive_reactions)
    negative_reactions = _unique(negative_reactions)
    mixed_reactions = _unique(mixed_reactions)

    misunderstandings: list[str] = []
    if len(asset["content"]) < 45:
        misunderstandings.append(_t(language, "negative_default"))
    if "regional_language_fit" in risk_categories:
        misunderstandings.append(_t(language, "concern_language"))
    if "pricing_urgency" in risk_categories:
        misunderstandings.append(_t(language, "concern_context"))
    if not misunderstandings:
        misunderstandings.append(_t(language, "uncertainty_1"))
    misunderstandings = _unique(misunderstandings)

    recommendations = [_t(language, "recommendation_clarity")]
    if "pricing_urgency" in risk_categories:
        recommendations.append(_t(language, "recommendation_terms"))
    if {"trust_privacy", "exaggerated_claims"} & risk_categories:
        recommendations.append(_t(language, "recommendation_proof"))
    if "regional_language_fit" in risk_categories:
        recommendations.append(_t(language, "recommendation_language"))
    if len(recommendations) < 3:
        recommendations.append(_t(language, "recommendation_proof"))
    recommendations = _unique(recommendations)

    rewrite_options = [
        {
            "option": "clarity_first",
            "label": _t(language, "rewrite_clarity"),
            "text": _t(
                language,
                "rewrite_clarity_text",
                brand=brand["name"],
                positioning=brand["positioning"],
                content=asset["content"],
            ),
            "rationale": _t(language, "rewrite_clarity_reason"),
        },
        {
            "option": "trust_first",
            "label": _t(language, "rewrite_trust"),
            "text": _t(
                language,
                "rewrite_trust_text",
                brand=brand["name"],
                content=asset["content"],
            ),
            "rationale": _t(language, "rewrite_trust_reason"),
        },
    ]

    if risk_points or len(persona_reactions) > 1:
        disagreements = [_t(language, "disagreement_text")]
    else:
        disagreements = [_t(language, "mixed_default")]

    scenario_summary = _t(
        language,
        "scenario_summary",
        brand=brand["name"],
        tone=brand["tone"],
        relationship=brand["audience_relationship"],
    )
    audience_summary = _t(
        language,
        "audience_summary_text",
        region=audience["region"],
        language=audience["language"],
        age=audience["age_band"],
        occupation=audience["occupation"],
        city=audience["city_tier"],
        income=audience["income_band"],
    )
    if red_line_matches:
        recommendations.append(
            _t(language, "recommendation_proof")
            if _t(language, "recommendation_proof") not in recommendations
            else _t(language, "recommendation_terms")
        )
        recommendations = _unique(recommendations)

    return {
        "title": _t(language, "report_title"),
        "labels": _labels(language),
        "scenario": {
            "summary": scenario_summary,
            "brand_name": brand["name"],
            "positioning": brand["positioning"],
            "asset_title": asset["title"],
            "asset_type": asset["type"],
            "asset_language": asset["language"],
            "content_excerpt": _excerpt(asset["content"]),
            "interaction_format": config["interaction_format"],
        },
        "audience_summary": {
            "summary": audience_summary,
            **audience,
            "persona_count": config["persona_count"],
        },
        "overall_image_impact_direction": impact,
        "overall_image_impact_direction_label": _impact_label(language, impact),
        "positive_reactions": positive_reactions,
        "negative_reactions": negative_reactions,
        "mixed_reactions": mixed_reactions,
        "risk_points": risk_points,
        "misunderstandings": misunderstandings,
        "persona_reactions": persona_reactions,
        "disagreements": disagreements,
        "recommendations": recommendations,
        "rewrite_options": rewrite_options,
        "assumptions": [
            _t(language, "assumption_1"),
            _t(language, "assumption_2"),
        ],
        "uncertainty": [
            _t(language, "uncertainty_1"),
            _t(language, "uncertainty_2"),
        ],
        "limitations": [
            _t(language, "limitation_1"),
            _t(language, "limitation_2"),
        ],
        "usage_metadata": {
            "engine": "miroind-deterministic-v1",
            "method": "rules_and_templates",
            "offline": True,
            "network_calls": False,
            "llm_used": False,
            "report_language": language,
            "asset_language": asset["language"],
            "persona_count": config["persona_count"],
            "budget": config["budget"],
            "risk_categories_reviewed": [
                "pricing_urgency",
                "trust_privacy",
                "exaggerated_claims",
                "regional_language_fit",
            ],
            "preferred_vocabulary_matches": preferred_matches,
            "red_line_matches": red_line_matches,
            "research_lenses_used": sorted(all_priorities),
            "translation_quality_note": _t(language, "quality_note"),
        },
    }


class MiroIndService:
    """Validate, analyze, persist, and read deterministic MiroInd runs."""

    RUNS_DIR = Path(Config.MIROIND_RUNS_DIR)

    def __init__(self, runs_dir: str | os.PathLike[str] | None = None):
        self.runs_dir = Path(runs_dir) if runs_dir is not None else Path(self.RUNS_DIR)

    def run(self, payload: Any) -> dict[str, Any]:
        normalized = validate_payload(payload)
        run_id = f"miroind_{uuid.uuid4().hex[:24]}"
        report = _build_report(normalized)
        record = {
            "run_id": run_id,
            "status": "completed",
            "report": report,
        }
        self._persist(record)
        return record

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        if not isinstance(run_id, str) or RUN_ID_PATTERN.fullmatch(run_id) is None:
            return None
        path = self.runs_dir / f"{run_id}.json"
        try:
            with path.open("r", encoding="utf-8") as handle:
                record = json.load(handle)
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None
        if not isinstance(record, dict) or record.get("run_id") != run_id:
            return None
        if record.get("status") != "completed" or not isinstance(record.get("report"), dict):
            return None
        return record

    def _persist(self, record: dict[str, Any]) -> None:
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        destination = self.runs_dir / f"{record['run_id']}.json"
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{record['run_id']}.",
            suffix=".tmp",
            dir=str(self.runs_dir),
        )
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
                json.dump(record, handle, ensure_ascii=False, sort_keys=True, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, destination)
        except Exception:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise


__all__ = [
    "MiroIndService",
    "MiroIndValidationError",
    "PERSONA_TEMPLATES",
    "ValidationError",
    "get_persona_templates",
    "validate_payload",
]
