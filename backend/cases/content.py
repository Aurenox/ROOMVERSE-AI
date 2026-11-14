from hashlib import sha256
from secrets import token_hex
from random import Random
from itertools import permutations
from .mysteries import strengthen
from .stories import exposures, question_key, QuestionPoolExhausted

THEMES = {
    "Detective": ("The Missing Ledger", "Recover the missing ledger"),
    "Horror": ("The Midnight Echo", "Break the echo before it returns"),
    "Science Fiction": ("Signal from Tomorrow", "Recover the future signal"),
    "Treasure Hunt": ("The Last Cache", "Locate the missing cache"),
    "Spy Mission": ("Operation Nightfall", "Identify the compromised drop"),
    "Reality Glitch": ("The Room That Repeated", "Close the repeating loop"),
}
DIFFICULTIES = ("Beginner", "Intermediate", "Professional", "Special Challenge")


def puzzle(question, options, answer, hints, explanation, evidence=None):
    return dict(question=question, options=options, answer=answer, hints=hints, explanation=explanation, evidence=evidence)


CASES = {
    "midnight": {
        "id": "midnight",
        "title": "The Midnight Office",
        "location": "Private investigator’s office",
        "difficulty": "Beginner",
        "intro": "A ledger vanished from a locked office. At midnight, the investigator left five exhibits on the desk. Study them before the archive seals.",
        "objective": "Identify who took the ledger and where they hid it.",
        "completion": "The exhibits point straight to the courier and the station locker. The ledger is back in evidence.",
        "source": "Virtual case", "duration": "3–5 min",
        "exhibits": [
            ["Wall clock", "Stopped at 11:40."],
            ["Door register", "Archivist signed out at 11:35. Courier entered at 11:38. Caretaker entered at 11:45."],
            ["Brass key", "Tag: station locker 27."],
            ["Desk note", "The ledger left three minutes before the clock stopped. Allow two minutes of clock drift in either direction."],
            ["Courier slip", "Hold the next delivery in the locker identified by the brass key."],
        ],
        "puzzles": [
            puzzle("What time did the wall clock stop?", ["11:35", "11:38", "11:40", "11:45"], "11:40",
                   ["Remember the stopped clock.", "The minute hand was past the half hour.", "Separate the clock reading from the sign-in times."], "The clock exhibit recorded 11:40."),
            puzzle("Which object identified a storage location?", ["Door register", "Brass key", "Wall clock", "Desk note"], "Brass key",
                   ["Look for a portable exhibit.", "It carried a small tag.", "Think of the item you would use to open a lock."], "The brass key was tagged with station locker 27."),
            puzzle("Ignoring clock drift, when did the ledger leave?", ["11:37", "11:38", "11:40", "11:43"], "11:37",
                   ["Combine the desk note and clock.", "The note describes an earlier time.", "Subtract the interval on the note from the stopped time."], "11:40 minus three minutes is 11:37."),
            puzzle("Whose entry fits within the clock’s two-minute drift?", ["Archivist", "Courier", "Caretaker", "Nobody"], "Courier",
                   ["Build a time window around your estimate.", "Compare the register's entry times only.", "The window ends before 11:40."], "The estimated window was 11:35–11:39. The archivist signed out. The courier entered at 11:38."),
            puzzle("Where should you recover the ledger?", ["Office safe", "Archive shelf", "Station locker 27", "Mail room"], "Station locker 27",
                   ["Connect the outgoing delivery to a tagged object.", "The slip tells you where the next delivery is held.", "Use the key’s tag to resolve the location."], "The courier slip directs the delivery to the locker on the brass key’s tag."),
        ],
    },
}

# Each file supplies a unique case narrative and five exhibits. Timing and clues
# stay entirely in the server-side manifest, separate from gallery metadata.
CASE_FILES = [
    ("greenhouse", "The Glasshouse Signal", "Botanical greenhouse", "A seed vault lost a rare specimen.", "isolate the matching greenhouse tray", "Brass mister", "Blue tray", "Copper gauge", "Ivy hook", "Seed seal", 2, 5),
    ("library", "The Quiet Archive", "After-hours library", "A folio disappeared during closing rounds.", "identify the folio’s transfer station", "Red folio", "Book cart", "Reading lamp", "Oak stamp", "Return bell", 3, 6),
    ("observatory", "Signal at Perihelion", "Mountain observatory", "An incoming signal vanished from the research log.", "identify the source of the missing recording", "Lens cap", "Signal dial", "Star chart", "Radio coil", "Tripod clip", 1, 7),
    ("station", "Platform Zero", "Abandoned rail station", "A parcel was logged on a platform that officially closed years ago.", "trace the parcel to its hand-off", "Ticket punch", "Rail lantern", "Platform sign", "Fare box", "Timetable pin", 4, 8),
    ("hotel", "Room Without a Number", "Art deco hotel", "A guest checked out before their room existed on the register.", "trace the unregistered checkout", "Desk bell", "Room fob", "Service tray", "Lobby mirror", "Guest ledger", 2, 9),
    ("vault", "The Violet Vault", "Bank sublevel", "A transfer signal appeared without a matching deposit.", "find the device behind the transfer", "Steel seal", "Deposit tray", "Vault wheel", "Ledger clasp", "Alarm plate", 5, 11),
    ("submarine", "Pressure Drop", "Deep-sea research station", "The emergency sample route was changed during a pressure alarm.", "reconstruct the diverted sample route", "Dive slate", "Pressure valve", "Airlock crank", "Hose clip", "Depth gauge", 4, 12),
    ("museum", "A Frame Too Far", "Restoration gallery", "The morning inventory found a frame with a false provenance stamp.", "locate the altered exhibit", "Canvas frame", "Paint palette", "Brass plaque", "Glass plinth", "Restoration brush", 6, 14),
    ("loop", "The Thirteenth Hour", "Temporal research lab", "A sealed room replayed the same hand-off with one item missing.", "break the repeating hand-off", "Quartz timer", "Pulse key", "Relay switch", "Loop reel", "Ion clamp", 7, 16),
]


def build_dossier(title, intro, objective, objects, offset, start, seed, complex_case=False, preserve_order=False):
    rng = Random(seed)
    labels = list(objects[:5])
    marker = 1
    used = {item.casefold() for item in labels}
    while len(labels) < 5:
        label = f"Fictional archive marker {marker}"
        marker += 1
        if label.casefold() not in used:
            labels.append(label)
            used.add(label.casefold())
    if not preserve_order:
        rng.shuffle(labels)
    exhibits = [[label, f"Fictional archive entry • Station {start + i * offset}"] for i, label in enumerate(labels)]
    first, second, third, fourth, fifth = labels
    if complex_case:
        final_prompt = f"Find the exhibit one interval above the midpoint between stations {start + offset} and {start + 3 * offset}."
        final_answer = fourth
    else:
        final_prompt = f"The dispatch was moved forward two intervals from station {start + offset}. Which exhibit was at the hand-off?"
        final_answer = fourth
    questions = [
        (f"Which exhibit was recorded at station {start}?", first, ["Start with the smallest station number.", "Find the first station in the ledger.", "Compare the numeric suffixes."], f"{first} was logged at station {start}."),
        ("Which exhibit was logged immediately after the first station?", second, ["Order the station numbers.", "Find the second station.", "Only one entry sits between the first and third."], f"The second station was {start + offset}."),
        (f"What was the interval between consecutive stations?", str(offset), ["Compare two neighboring stations.", "Use subtraction.", "Check the same difference with a second pair."], f"{start + offset} minus {start} is {offset}."),
        (f"Which exhibit was midway between the lowest and highest stations?", third, ["Look at the endpoints.", "Average the two endpoint numbers.", "There are two exhibits on either side."], f"The midpoint was station {start + 2 * offset}."),
        (final_prompt, final_answer, ["Trace the hand-off using the station numbers.", "Use the interval you calculated.", "Locate the resulting station in the evidence."], f"The hand-off points to {final_answer}."),
    ]
    puzzles = []
    for index, (prompt, answer, hints, explanation) in enumerate(questions):
        choices = [str(n) for n in (offset, offset + 1, offset + 3, offset * 2 + 2)] if index == 2 else [answer, *rng.sample([label for label in labels if label != answer], 3)]
        rng.shuffle(choices)
        puzzles.append(puzzle(prompt, choices, answer, hints, explanation))
    return dict(title=title, intro=intro, objective=objective, exhibits=exhibits, puzzles=puzzles,
                completion=f"Case closed. The evidence placed the hand-off at {final_answer}.")


for index, (slug, title, location, event, objective, *data) in enumerate(CASE_FILES, 1):
    *labels, interval, station = data
    case = build_dossier(title, event + " Memorize the station ledger before the archive seals.",
                         objective.capitalize() + ".", labels, interval, station, slug, index >= 6)
    CASES[slug] = dict(case, id=slug, location=location, difficulty=DIFFICULTIES[index // 3],
                      source="Virtual case", duration="3–5 min")


def scanner_case(objects, theme, difficulty, story=None, source="Prepared mystery", history=None):
    title, objective = THEMES[theme]
    seed = sha256(("|".join(objects) + theme + difficulty + token_hex(16)).encode()).hexdigest()
    offset = 2 + int(seed[0], 16) % 5
    start = 4 + int(seed[1], 16) % 13
    intro = (f"Your selected objects are part of a fictional missing-item mystery. "
             f"Follow witness statements and arrival records to {objective.lower()}.")
    if story:
        title, intro = story["title"], story["intro"] + " Use the fictional witness dossier to solve the case."
        objects = story["order"]
    case = build_dossier(title, intro, objective + ".", objects, offset, start,
                         seed, difficulty in DIFFICULTIES[2:], preserve_order=story is not None)
    case.update(id="scanner", difficulty=difficulty, selected_objects=list(objects))
    strengthen(case,history)
    # The model's selected exhibit order determines the station map, whilst the
    # game's deterministic construction always supplies a checkable solution.
    for question in case["puzzles"]:
        question["evidence"] = case["exhibits"]
    return dict(case, id="scanner", source=source, difficulty=difficulty, duration="3–5 min")


def catalog():
    fields = ("id", "title", "location", "difficulty", "duration")
    return [{field: case[field] for field in fields} for case in CASES.values()]



# Visual details verified against the shipped scene artwork.
VISUAL_CLUES = {
    "midnight": [("What sits directly behind the desk?", ["Leather chair", "Wooden bench", "Red sofa", "Metal stool"], "Leather chair"),
                 ("Where is the lit desk lamp?", ["Right side", "Left side", "Under the desk", "On the ceiling"], "Right side")],
    "greenhouse": [("What covers the greenhouse roof?", ["Glass panes", "Wood boards", "Stone slabs", "Fabric"], "Glass panes"),
                   ("What color are the flowers at the front left?", ["Purple", "Orange", "White", "Blue"], "Purple")],
    "library": [("What color are the reading lamp shades?", ["Green", "Red", "Blue", "White"], "Green"),
                ("What stands to the left of the reading table?", ["Globe", "Telescope", "Piano", "Bicycle"], "Globe")],
    "observatory": [("Which instrument dominates the room?", ["Telescope", "Microscope", "Camera", "Radio"], "Telescope"),
                    ("What appears beyond the dome opening?", ["Mountains", "Ocean", "City towers", "Forest"], "Mountains")],
    "station": [("Where is the train?", ["Left of the platform", "Right of the platform", "Above the platform", "At the ticket desk"], "Left of the platform"),
                ("Which item is beside the wall on the right?", ["Bench", "Piano", "Fountain", "Desk"], "Bench")],
    "hotel": [("What hangs above the lobby?", ["Chandelier", "Clock", "Ceiling fan", "Globe"], "Chandelier"),
              ("What color are the sofas?", ["Red", "Green", "Blue", "White"], "Red")],
    "vault": [("What shape is the open vault door?", ["Circular", "Square", "Triangular", "Hexagonal"], "Circular"),
              ("Which color lights the corridor?", ["Violet", "Green", "Orange", "White"], "Violet")],
    "submarine": [("What lies beyond the large round window?", ["Underwater landscape", "Mountains", "City street", "Desert"], "Underwater landscape"),
                  ("What floats in the glowing tanks on the left?", ["Jellyfish", "Leaves", "Balloons", "Crystals"], "Jellyfish")],
    "museum": [("What is depicted in the central painting?", ["Woman", "Ship", "Mountain", "Horse"], "Woman"),
               ("What supports the central painting?", ["Easel", "Glass cabinet", "Wall hook", "Bookshelf"], "Easel")],
    "loop": [("What occupies the central glass chamber?", ["Hourglass", "Globe", "Clock face", "Telescope"], "Hourglass"),
             ("Where are the control screens?", ["Along the sides", "On the ceiling", "Under the floor", "Inside the hourglass"], "Along the sides")],
}
for scene_id, details in VISUAL_CLUES.items():
    visual = [
        puzzle(question, options, answer,
               ["Recall the room image.", "Picture the object and its position.", "Compare the choices with the scene you observed."],
               f"The scene shows {answer.lower()}.")
        for question, options, answer in details
    ]
    CASES[scene_id]["puzzles"][:2] = visual
    CASES[scene_id]["intro"] += " Study the image as well as the notes. Two questions test visual details and three test the written evidence."



EXTRA_VISUAL_CLUES = {
    "midnight": [("What is visible on the right wall?", ["Evidence board", "Bookshelf", "Mirror", "Calendar"], "Evidence board"),
                 ("What is on the desk in front of the chair?", ["Papers", "Fruit bowl", "Chessboard", "Telephone"], "Papers")],
    "greenhouse": [("Where is the round pond?", ["Front right", "Front left", "On the roof", "Behind a bookshelf"], "Front right"),
                   ("What is reflected on the path?", ["Warm lights", "Road signs", "Televisions", "Snow"], "Warm lights")],
    "library": [("What shape is the large rear window?", ["Arched", "Circular", "Triangular", "Square"], "Arched"),
                ("What surrounds the reading room?", ["Bookshelves", "Fish tanks", "Train tracks", "Paintings only"], "Bookshelves")],
    "observatory": [("Which object stands left of the telescope?", ["Chalkboard", "Bench", "Globe", "Piano"], "Chalkboard"),
                    ("What shape is the telescope platform?", ["Circular", "Triangular", "Rectangular", "Hexagonal"], "Circular")],
    "station": [("What covers the platform roof?", ["Arched structure", "Flat glass", "Fabric awning", "Open sky"], "Arched structure"),
                ("What do the tracks lead toward?", ["Dark tunnel", "Sea", "Library", "Garden"], "Dark tunnel")],
    "hotel": [("What is on the central table?", ["Flowers", "Globe", "Clock", "Books"], "Flowers"),
              ("Which item stands at the right of the lobby?", ["Luggage trolley", "Piano", "Bicycle", "Desk chair"], "Luggage trolley")],
    "vault": [("Where is the open vault door?", ["Left", "Right", "Ceiling", "Far end"], "Left"),
              ("What is on the vault door face?", ["Wheel handle", "Window", "Painting", "Clock"], "Wheel handle")],
    "submarine": [("What sits on the right of the workbench?", ["Microscope", "Globe", "Lamp shade", "Books"], "Microscope"),
                  ("What shape is the large viewing window?", ["Circular", "Triangular", "Square", "Hexagonal"], "Circular")],
    "museum": [("What is left of the central portrait?", ["Sculpted bust", "Globe", "Clock", "Tree"], "Sculpted bust"),
               ("Which tool lights the restoration table?", ["Desk lamp", "Chandelier", "Candle", "Flashlight"], "Desk lamp")],
    "loop": [("What stands behind the central chamber?", ["Large clock face", "Bookshelf", "Tree", "Painting"], "Large clock face"),
             ("What color is the central chamber's glow?", ["Amber", "Violet", "Green", "Red"], "Amber")],
}

def fresh_virtual_case(scene_id, previous=None, history=None):
    """Build new evidence while retaining the verified scene illustration."""
    history = list(history) if history is not None else ([previous] if previous else [])
    original = CASES[scene_id]
    rng = Random(token_hex(16))
    labels = [entry[0] for entry in original["exhibits"]]
    start = rng.randint(10, 99)
    interval = rng.randint(2, 19)
    case = build_dossier(original["title"],
                         "A new dispatch has arrived. Study the room image and this case's fictional evidence ledger.",
                         "Trace the missing dispatch through the evidence stations.",
                         labels, interval, start, token_hex(16),
                         original["difficulty"] in DIFFICULTIES[2:])
    case.update({key: original[key] for key in ("id", "location", "difficulty", "source", "duration")})
    details = [*VISUAL_CLUES[scene_id], *EXTRA_VISUAL_CLUES[scene_id]]
    counts = exposures(history)
    previous_questions = {item["question"].split(" Give its number")[0] for old in history for item in old.get("puzzles", [])}
    recent_questions = {item["question"] for item in (previous or {}).get("puzzles", [])}
    available = [item for item in details if counts[question_key(item[0])] < 1 and item[0] not in recent_questions]
    chosen = rng.sample(available, min(2,len(available)))
    chosen += rng.sample([item for item in details if item not in chosen],2-len(chosen))
    pool = []
    for question, options, answer in chosen:
        options = list(options)
        rng.shuffle(options)
        pool.append(puzzle(question, options, answer,
                           ["Recall the room image.", "Picture the object and its position.", "Compare the options with what you observed."],
                           f"The scene shows {answer.lower()}."))
    notes = case["puzzles"]
    # Vary the locations players must infer, not only option order.
    labels = [row[0] for row in case["exhibits"]]
    target = rng.randrange(1, 5)
    options = [labels[target], *rng.sample([label for label in labels if label != labels[target]], 3)]
    rng.shuffle(options)
    notes[3] = puzzle(
        f"Which exhibit is {target} interval(s) after station {start}?",
        options, labels[target],
        ["Recall the station ledger.", "Use the gap between neighboring stations.", "Count forward from the lowest station."],
        f"{start} + {target} × {interval} = {start + target * interval}, the station for {labels[target]}.")
    case["puzzles"] = [*pool, *notes[2:]]
    if previous and case["exhibits"] == previous.get("exhibits"):
        return fresh_virtual_case(scene_id, previous, history)
    case["scene_facts"] = [f"{q} {answer}." for q,options,answer in details]
    case = strengthen(case,history)
    # Once a fixed picture fact is used, bind it to a freshly assigned witness caption.
    # Recalling last time's option no longer answers the new question.
    used_captions = {tuple(sorted(tuple(pair) for pair in item.get("photo_captions", []))) for old in history for item in old.get("puzzles", []) if item.get("photo_captions")}
    for index, question in enumerate(case["puzzles"][:2]):
        if counts[question_key(question["question"])] < 1:
            continue
        people = [f"{tag}-{rng.randint(10,99)}" for tag in rng.sample(["Amber","Cobalt","Jade","Silver","Ruby","Pearl","Quartz","Indigo"],4)]
        original_answer = question["answer"]
        captions = list(question["options"])
        mappings = [tuple(zip(people,values)) for values in permutations(captions)]
        fresh_mappings = [mapping for mapping in mappings if tuple(sorted(mapping)) not in used_captions]
        retries = 0
        while not fresh_mappings:
            retries += 1
            if retries > 100:
                raise QuestionPoolExhausted
            # A new, clearly separate photo-review team avoids recycling an exhausted caption set.
            people = [f"Reviewer {name} {rng.choice(['Vale', 'Reed', 'Park', 'Chen', 'Shah', 'Stone', 'Lake', 'Fox'])}" for name in rng.sample(["Ada","Kai","Leah","Omar","Zoe","Finn","Nia","Ravi"],4)]
            fresh_mappings = [tuple(zip(people,values)) for values in permutations(captions) if tuple(sorted(zip(people,values))) not in used_captions]
        mapping = rng.choice(fresh_mappings)
        correct = next(person for person,caption in mapping if caption == original_answer)
        case["exhibits"].append([f"Image reference {index+1}", question["question"] + " " + "; ".join(f"{person}: {caption}" for person,caption in mapping)])
        prompt = f"{question['question']} Which scene-reference tag matches the image: {', '.join(sorted(people))}?"
        retries = 0
        while counts[question_key(prompt)] >= 2:
            retries += 1
            if retries > 100:
                raise QuestionPoolExhausted
            people = [f"Reviewer {name} {rng.choice(['Vale','Reed','Park','Chen','Shah','Stone','Lake','Fox'])}" for name in rng.sample(["Ada","Kai","Leah","Omar","Zoe","Finn","Nia","Ravi"],4)]
            mapping = tuple(zip(people,captions))
            correct = next(person for person,caption in mapping if caption == original_answer)
            prompt = f"{question['question']} Which scene-reference tag matches the image: {', '.join(sorted(people))}?"
        case["exhibits"][-1] = [f"Image reference {index+1}", question["question"] + " " + "; ".join(f"{person}: {caption}" for person,caption in mapping)]
        linked = puzzle(prompt,people[:],correct,
            ["Recall the image detail, then this attempt's scene-reference tags.", "Only one reference description matches the pictured detail.", "Choose the tag attached to that matching description."],
            f"The pictured detail was {original_answer}. In this attempt, {correct} labels that description.")
        linked.update(kind="photo-link",photo_captions=list(mapping))
        rng.shuffle(linked["options"])
        case["puzzles"][index] = linked
    change_counts = {variant:sum(old.get("change_variant") == variant for old in history) for variant in ("lamp","globe")}
    unused_changes = [variant for variant in ("lamp","globe") if change_counts[variant] < 1]
    if scene_id == "midnight" and not unused_changes:
        case["intro"] += " You have completed the current changed-image set. Use the new scene-reference tags to connect the image to this investigation."
    if scene_id == "midnight" and unused_changes:
        least_seen = min(change_counts[variant] for variant in unused_changes)
        unused_changes = [variant for variant in unused_changes if change_counts[variant] == least_seen]
        variant = rng.choice([variant for variant in unused_changes if variant != (previous or {}).get("change_variant")] or unused_changes)
        if variant == "lamp":
            changed = puzzle("What changed in the desk area compared with the original room?",
                ["The brass desk lamp is missing", "The mug is missing", "The drinking glass is missing", "The magnifying glass is missing"],
                "The brass desk lamp is missing",
                ["Recall the objects on the right side of the desk.", "Compare the tall objects with the smaller desk items.", "A brass object that provided light was removed."],
                "The original had a brass desk lamp on the right. The changed image has no desk lamp; the other listed objects remain.")
        else:
            changed = puzzle("What changed on the cabinet behind the chair compared with the original room?",
                ["The globe is missing", "The plant is missing", "The camera is missing", "The books are missing"],
                "The globe is missing",
                ["Recall the cabinet behind the chair.", "Look to the left of the plant.", "A round object on a stand was removed."],
                "The original had a globe to the left of the plant on the rear cabinet. The changed image has no globe; the other listed objects remain.")
        rng.shuffle(changed["options"])
        changed["changed_image"] = "/art/midnight-change-a.png" if variant == "lamp" else "/art/midnight-change-b.png"
        changed["kind"] = "spot-the-change"
        case["puzzles"][1] = changed
        case["change_variant"] = variant
        case["intro"] += " Remember the objects: one visual round will show a changed version of this room."
    return case
