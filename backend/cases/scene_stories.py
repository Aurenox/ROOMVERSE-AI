"""Scene-specific fictional settings, anchored to the shipped image manifest."""
SETTINGS = {
    "midnight": ("Midnight Office", ["desk area","evidence-board corner","chair alcove","office doorway"], ["the night investigator's shift", "a confidential file review", "the office closing check"]),
    "greenhouse": ("Glasshouse", ["pond walkway","flower aisle","glass-roof entrance","potting corner"], ["a botanical inspection", "the evening watering round", "a rare-seed exhibition"]),
    "library": ("Quiet Archive", ["globe corner","reading table","rear-window aisle","bookshelf passage"], ["an archive restoration review", "the last reading session", "a private collection audit"]),
    "observatory": ("Mountain Observatory", ["telescope platform","chalkboard corner","dome entrance","instrument bench"], ["a meteor observation shift", "a telescope calibration", "the final research briefing"]),
    "station": ("Platform Zero", ["train-side platform","bench area","tunnel approach","roofed platform entrance"], ["the last departure inspection", "a closed-platform survey", "the railway archive review"]),
    "hotel": ("Grand Lobby", ["sofa area","flower-table corner","trolley bay","chandelier hall"], ["a late guest arrival", "a reception shift change", "a private lobby event"]),
    "vault": ("Violet Vault", ["wheel-door threshold","violet corridor","deposit bay","security desk"], ["a vault maintenance window", "an overnight deposit audit", "a security handover"]),
    "submarine": ("Deep-Sea Station", ["viewing-window bay","jellyfish tank aisle","microscope bench","research entrance"], ["a deep-sea sampling shift", "an aquarium research audit", "a pressure-system inspection"]),
    "museum": ("Restoration Gallery", ["portrait easel","sculpture corner","lamp-lit workbench","gallery entrance"], ["a portrait restoration session", "a collection insurance review", "the exhibition closing round"]),
    "loop": ("Temporal Laboratory", ["hourglass chamber","clock-face platform","left control bank","right control bank"], ["a chamber timing experiment", "a control-system audit", "the laboratory shutdown sequence"]),
}


def scene_story(case, history, rng, story_id, title, opening):
    setting = SETTINGS.get(case.get("id"))
    if not setting:
        return title, opening, None
    place, zones, occasions = setting
    prior = [old for old in history if old.get("id") == case["id"] and old.get("story_id") == story_id]
    counts = {occasion:sum(old.get("story_occasion") == occasion for old in prior) for occasion in occasions}
    lowest = min(counts.values())
    occasion = rng.choice([value for value in occasions if counts[value] == lowest])
    case["story_occasion"] = occasion
    facts = case.get("scene_facts", [])
    anchor = rng.choice(facts) if facts else place
    case["scene_anchor"] = anchor
    return (f"{place}: {title} — {occasion.capitalize()}",
            f"During {occasion} at {place}, a new investigation begins. {opening} "
            f"Start with the actual room photograph: {anchor} "
            "The visitor movements, portable evidence, and named investigation zones below are fictional case records; do not infer them from the photograph.",
            list(zones))
