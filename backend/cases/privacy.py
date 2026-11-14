"""Conservative text checks; these are not a complete PII detector."""
import re


class PhotoPrivacyError(ValueError):
    pass


def contains_private_text(text):
    if re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}",text,re.I):
        return True
    if re.search(r"(?:https?://|www\.)\S+",text,re.I):
        return True
    for value in re.findall(r"\+?\d[\d\s().-]{5,}\d",text):
        if len(re.sub(r"\D","",value)) >= 7:
            return True
    return bool(re.search(r"\b(?:passport|password|selfie|identity card|id card|driver'?s? licen[cs]e|credit card|debit card|bank statement|medical record|social security|email address|phone number)\b",text,re.I))
