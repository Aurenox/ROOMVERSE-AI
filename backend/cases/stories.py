"""Rotating story missions and an owner-history question exposure limit."""
from collections import Counter
import re

class QuestionPoolExhausted(Exception):
    """No eligible prompt could be generated within the bounded search."""


STORIES = {
    "relay": ("The Broken Custody Chain", "Two recorded handovers connect three visitors. Reconstruct the final holder.", "Follow both handovers to their final destination.", "relay"),
    "audit": ("The False Clearance", "An inspection pass belongs to a visitor, but its destination was copied from someone else.", "Check the pass against the independent evidence.", "audit"),
    "recovery": ("The Last Safe Location", "A recovery team must locate an item using the first and final arrivals rather than a delivery label.", "Reconstruct the recovery route from the arrival sequence.", "recovery"),
    "vanished": ("The Vanished Keepsake", "A keepsake vanished between the opening and closing checks. Reconstruct its last confirmed journey.", "Trace the missing item and its last carrier.", "missing"),
    "labels": ("The Switched Exhibit Labels", "Two exhibit labels were swapped before the display opened. Restore the true owners using the confirmed records.", "Untangle swapped labels and restore the correct pairings.", "labels"),
    "message": ("The Intercepted Message", "A sealed message followed the visitors through the building. One delivery note points to the wrong room.", "Reconstruct the message route and check the delivery note.", "route"),
    "blackout": ("The Blackout Alibi", "The lights failed between two recorded arrivals. A visitor's account does not match the independently confirmed evidence.", "Establish the arrival sequence and test the alibis.", "blackout"),
    "planted": ("The Planted Clue", "An item was presented as proof against the wrong visitor. Separate the accusation from the confirmed chain of custody.", "Identify the true carrier and reject the planted accusation.", "accusation"),
    "parcel": ("The Misdelivered Parcel", "A parcel was redirected while four visitors passed through the building. Follow the real recipient instead of trusting its address label.", "Find the intended recipient and the correct delivery room.", "delivery"),
}


def question_key(text):
    return " ".join(re.findall(r"\w+",text.casefold()))


def question_origins(case, question):
    origins = {question_key(question['question']), question_key(question.get('source_question',question['question']))}
    # Recover image targets for older Gemini rounds written before provenance was saved.
    if question.get('generation_target','').startswith('image-') and not question.get('source_question') and not question.get('photo_captions'):
        from .content import VISUAL_CLUES, EXTRA_VISUAL_CLUES
        for prompt,options,answer in [*VISUAL_CLUES.get(case.get('id'),[]),*EXTRA_VISUAL_CLUES.get(case.get('id'),[])]:
            if question.get('answer') == answer and set(question.get('options',[])) == set(options):
                origins.add(question_key(prompt))
    return origins


def exposures(history):
    counts = Counter()
    for case in history:
        for question in case.get('puzzles',[]):
            counts.update(question_origins(case,question))
    return counts


def choose_story(history,rng):
    counts = Counter(case.get("story_id") for case in history)
    last = history[-1].get("story_id") if history else None
    available = [key for key in STORIES if key != last]
    lowest = min(counts[key] for key in available)
    return rng.choice([key for key in available if counts[key] == lowest])


def build_questions(model,history,rng,story_id,full,count):
    people,objects,rooms = model["people"],model["objects"],model["rooms"]
    obj,room = model["solution"]
    missing,liar = model["missing"],model["liar"]
    carrier = obj.index(missing)
    a,b = rng.sample(range(4),2)
    extra = []
    if story_id == "relay":
        c = next(i for i in range(4) if i not in (a,b))
        extra.append(["Two-stage custody record",f"A sealed evidence pouch passed from {people[a]} to the carrier of {objects[obj[b]]}, then to the visitor to the {rooms[room[c]]}. No later handover occurred."])
    elif story_id == "audit":
        extra.append(["Disputed inspection pass",f"The pass names the carrier of {objects[obj[a]]}, but gives the {rooms[room[b]]} as their destination. The independent clues, not the pass, establish where they went."])
    elif story_id == "recovery":
        extra.append(["Recovery instruction", "Find the item held by the final arrival, then send the recovery team to the room visited by the first arrival. These are two different visitors."])
    elif story_id == "labels":
        extra.append(["Swapped labels",f"The label on {objects[obj[a]]} names {people[b]}; the label on {objects[obj[b]]} names {people[a]}. Both labels are wrong. Confirmed records identify the real carriers."])
    elif story_id == "message":
        extra.append(["Sealed message route",f"The message passed from {people[a]} to the visitor carrying {objects[obj[b]]}. A delivery note incorrectly names the {rooms[room[a]]} as the recipient's room."])
    elif story_id == "blackout":
        a = rng.randrange(3)
        extra.append(["Power failure",f"The lights went out immediately after {people[a]} arrived and returned immediately before {people[a+1]} arrived. Neither arrival occurred during the blackout."])
    elif story_id == "planted":
        extra.append(["Unverified accusation",f"A loose card accuses {people[b]} of carrying {objects[obj[a]]}. Trust the confirmed records, not this card."])
    elif story_id == "parcel":
        extra.append(["Parcel instructions",f"Deliver to the visitor carrying {objects[obj[a]]}. The address label says {rooms[room[b]]}, but that label is incorrect."])
    bank = []
    def add(prompt,category,index,kind,hints,explanation=full):
        choices = {"person":people,"object":objects,"room":rooms}[category]
        bank.append(dict(question=prompt,answer=choices[index],options=rng.sample(choices,len(choices)),evidence=None,
                         hints=hints,explanation=explanation,kind=kind,answer_claim=[category,index]))
    recall = ["Use the confirmed records, not the unverified claim.","Match each visitor to one item and one room.","Eliminate pairings that contradict a confirmed clue."]
    timeline = ["Recall the camera arrival order.","Find the named visitor or item in that order.","Then use the confirmed pairings to complete the next step."]
    for i in range(4):
        add(f"Who carried {objects[i]} in the confirmed record?","person",obj.index(i),"matching",recall)
        add(f"Which room did the carrier of {objects[i]} visit?","room",room[obj.index(i)],"matching",recall)
        add(f"Which item did {people[i]} take into their recorded room?","object",obj[i],"matching",recall)
        add(f"Which item was carried by the visitor to the {rooms[i]}?","object",obj[room.index(i)],"matching",recall)
    for i in range(3):
        add(f"Which item arrived immediately after {objects[obj[i]]}?","object",obj[i+1],"timeline",timeline)
        add(f"Which room did the visitor immediately after {people[i]} visit?","room",room[i+1],"timeline",timeline)
        add(f"Who arrived immediately before the visitor to the {rooms[room[i+1]]}?","person",i,"timeline",timeline)
    # Mission questions change the deduction, not only the surrounding story text.
    if story_id == "vanished":
        add("Which single item disappeared between the opening and closing inventories?","object",missing,"missing",["Compare both inventories.","Cross out items present in both.","Only one opening item is absent at closing."],f"{objects[missing]} is absent from the closing inventory.")
        add(f"Who last carried the missing {objects[missing]} according to the confirmed records?","person",carrier,"missing",recall)
        add(f"Which room should be searched first for the missing {objects[missing]}?","room",room[carrier],"missing",recall)
    elif story_id == "labels":
        add(f"The label on {objects[obj[a]]} names {people[b]}. Whose name should replace it?","person",a,"labels",recall)
        add(f"Which item should actually carry {people[b]}'s label?","object",obj[b],"labels",recall)
        add(f"Where did the true carrier of the wrongly labeled {objects[obj[a]]} go?","room",room[a],"labels",recall)
    elif story_id == "message":
        add(f"Who received the sealed message from {people[a]}?","person",b,"route",recall)
        add(f"The delivery note names the {rooms[room[a]]}. Which room did the message recipient actually visit?","room",room[b],"route",recall)
        add(f"Which item identifies the visitor who received {people[a]}'s message?","object",obj[b],"route",recall)
    elif story_id == "blackout":
        add(f"Which item was carried by the visitor arriving immediately before the blackout after {people[a]}'s arrival?","object",obj[a],"blackout",timeline)
        add(f"Which room did the first visitor arriving after that blackout visit?","room",room[a+1],"blackout",timeline)
    elif story_id == "planted":
        add(f"The loose card blames {people[b]} for carrying {objects[obj[a]]}. Who really carried it?","person",a,"accusation",recall)
        add(f"Which item actually belongs in the confirmed record for the accused {people[b]}?","object",obj[b],"accusation",recall)
        add(f"Which room was visited by the real carrier of the item falsely linked to {people[b]}?","room",room[a],"accusation",recall)
    elif story_id == "relay":
        add(f"After both handovers starting with {people[a]}, who finally held the sealed pouch?","person",c,"relay",recall)
        add(f"Which item identifies the middle holder in the pouch route starting with {people[a]}?","object",obj[b],"relay",recall)
        add(f"Where did the final pouch holder after {people[b]} go?","room",room[c],"relay",recall)
    elif story_id == "audit":
        add(f"Who is the actual holder of the inspection pass linked to {objects[obj[a]]}?","person",a,"audit",recall)
        add(f"Which destination should replace {rooms[room[b]]} on the pass linked to {objects[obj[a]]}?","room",room[a],"audit",recall)
    elif story_id == "recovery":
        add(f"Under the recovery instruction, which item must be collected from final arrival {people[3]}?","object",obj[3],"recovery",timeline)
        add(f"Which room is the recovery team's destination, determined by first arrival {people[0]}?","room",room[0],"recovery",timeline)
    else:
        add(f"The parcel is for the carrier of {objects[obj[a]]}. Who should receive it?","person",a,"delivery",recall)
        add(f"The parcel label says {rooms[room[b]]}. Which room is the correct destination?","room",room[a],"delivery",recall)
        add(f"Which item identifies the intended recipient of the parcel labeled {rooms[room[b]]}?","object",obj[a],"delivery",recall)
    add(f"Among {', '.join(sorted(people))}, whose claimed room contradicts the confirmed records?","person",liar,"contradiction",recall,model["contradiction_explanation"])
    counts = exposures(history)
    bank = list({question_key(q["question"]):q for q in bank if counts[question_key(q["question"])] < 2}.values())
    recent = {key for old in history[-1:] for q in old.get("puzzles",[]) for key in question_origins(old,q)}
    bank = [q for q in bank if question_key(q["question"]) not in recent]
    preferred = [q for q in bank if q["kind"] == STORIES[story_id][3]]
    if not preferred or len(bank) < count:
        return None,extra
    selected = [rng.choice(preferred)]
    remaining = [q for q in bank if q not in selected]
    rng.shuffle(remaining)
    # Mix deduction types before filling the remaining slots.
    for q in remaining:
        if len(selected) == count:
            break
        if q["kind"] not in {item["kind"] for item in selected}:
            selected.append(q)
    selected += rng.sample([q for q in bank if q not in selected],count-len(selected))
    return selected,extra
