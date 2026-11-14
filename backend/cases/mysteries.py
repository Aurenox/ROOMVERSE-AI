"""Narrative puzzles with a uniquely solvable evidence model."""
from itertools import permutations, product
from random import Random
from secrets import token_hex
from .scene_stories import scene_story
from .dossier_formats import vary_dossier
from .stories import STORIES, choose_story, build_questions, QuestionPoolExhausted


def position(entity, assignment):
    kind, value = entity
    return value if kind == 'person' else assignment[0 if kind == 'object' else 1].index(value)


def satisfies(assignment, clue):
    left, relation, right = clue
    a, b = position(left, assignment), position(right, assignment)
    return a == b if relation == 'eq' else a != b if relation == 'ne' else a < b


def strengthen(case, history=None, attempt=0):
    if attempt >= 32:
        raise QuestionPoolExhausted
    history = history or []
    rng = Random(token_hex(16))
    story_id = choose_story(history,rng)
    story_title,opening,objective,_ = STORIES[story_id]
    story_title,opening,scene_rooms = scene_story(case,history,rng,story_id,story_title,opening)
    people = rng.sample(['Alex','Mira','Jules','Rowan','Sam','Isha','Noor','Theo'],4)
    if attempt:
        people = [f"{name} {rng.choice(['Vale','Reed','Park','Chen','Shah','Stone','Lake','Fox'])}" for name in people]
    labels = list(case.get('selected_objects') or [row[0] for row in case['exhibits']])
    case["selected_objects"] = labels
    objects = labels[:4]
    marker = 1
    while len(objects) < 4:
        label = f'Fictional evidence envelope {marker}'
        marker += 1
        if label not in objects:
            objects.append(label)
    rooms = rng.sample(scene_rooms or ['reading room','side office','courtyard','storage room','workshop','reception'],4)
    solution = (tuple(rng.sample(range(4),4)),tuple(rng.sample(range(4),4)))
    level = case['difficulty']
    entities = [(kind,i) for kind in ('person','object','room') for i in range(4)]
    def name(entity):
        kind,i = entity
        return people[i] if kind == 'person' else f'the visitor carrying {objects[i]}' if kind == 'object' else f'the visitor to the {rooms[i]}'
    def describe(clue):
        left,relation,right = clue
        connector = {'eq':'was the same person as','ne':'was not','before':'arrived earlier than'}[relation]
        return f'{name(left)} {connector} {name(right)}.'
    clues = []
    if level == 'Beginner':
        for i in range(4):
            clues += [(('person',i),'eq',('object',solution[0][i])),(('person',i),'eq',('room',solution[1][i]))]
    else:
        candidates = list(product(permutations(range(4)),repeat=2))
        # Intermediate gets two anchors; all remaining links require deduction.
        if level == 'Intermediate':
            i,j = rng.sample(range(4),2)
            clues = [(('person',i),'eq',('object',solution[0][i])),
                     (('object',solution[0][j]),'eq',('room',solution[1][j]))]
            candidates = [item for item in candidates if all(satisfies(item,c) for c in clues)]
        # Professional has no direct identity giveaways: infer the entire grid.
        possible = [(a,rel,b) for a in entities for b in entities if a[0] != b[0] for rel in ('ne','before') if satisfies(solution,(a,rel,b))]
        rng.shuffle(possible)
        for clue in possible:
            remaining = [item for item in candidates if satisfies(item,clue)]
            if len(remaining) < len(candidates):
                clues.append(clue)
                candidates = remaining
            if len(candidates) == 1:
                break
        all_assignments = list(product(permutations(range(4)),repeat=2))
        for clue in list(clues):
            reduced = [c for c in clues if c != clue]
            if sum(all(satisfies(item,c) for c in reduced) for item in all_assignments) == 1:
                clues.remove(clue)
    rng.shuffle(clues)
    missing,liar = rng.randrange(4),rng.randrange(4)
    carrier = solution[0].index(missing)
    claims = list(solution[1])
    claims[liar] = rng.choice([i for i in range(4) if i != claims[liar]])
    exhibits = [
        ['Fictional case rules','Story clues are separate from the room illustration. Four visitors each carried one different item and visited one different room. Confirmed clues are reliable; exactly one witness statement is false.'],
        ['Camera arrival order',' → '.join(people)+'. No simultaneous arrivals.'],
        ['Opening inventory','; '.join(objects)],
        ['Closing inventory','; '.join(item for i,item in enumerate(objects) if i != missing)],
        ['Rooms in this case','; '.join(rooms)],
    ]
    if case.get('id') == 'scanner':
        exhibits.append(['Your confirmed objects', '; '.join(labels) + '. The four-item story inventory above is fictional; any extra objects stay outside this puzzle.'])
    if level == 'Beginner':
        exhibits += [[f'Confirmed record: {people[i]}',f'Carried {objects[solution[0][i]]}; visited the {rooms[solution[1][i]]}.'] for i in range(4)]
    else:
        exhibits += [[f'Confirmed clue {i+1}',describe(clue)] for i,clue in enumerate(clues)]
    exhibits += [[f'Witness statement: {people[i]}',f'I visited the {rooms[claims[i]]}.'] for i in range(4)]
    full = '; '.join(f'{people[i]} carried {objects[solution[0][i]]} and visited the {rooms[solution[1][i]]}' for i in range(4))+'.'
    model = dict(people=people,objects=objects,rooms=rooms,clues=clues,solution=solution,missing=missing,liar=liar,
                 contradiction_explanation=f"{people[liar]} claimed the {rooms[claims[liar]]}, but visited the {rooms[solution[1][liar]]}. {full}")
    notes,mission_evidence = build_questions(model,history,rng,story_id,full,5 if case.get('id') == 'scanner' else 3)
    if notes is None:
        return strengthen(case,history,attempt+1)
    exhibits += mission_evidence
    case['puzzles'] = notes if case.get('id') == 'scanner' else [*case['puzzles'][:2],*notes]
    case['exhibits'] = exhibits
    case['story_id'],case['story_title'] = story_id,story_title
    case['objective'] = objective
    atmosphere = case['intro'].split(' Use the fictional')[0] + ' ' if case.get('id') == 'scanner' else ''
    case['intro'] = atmosphere + opening + ' Study the illustration and the separate fictional case notes.'
    case['intro'] += {'Beginner':' Direct records help you learn the investigation.','Intermediate':' Start with two confirmed links, then combine exclusions and arrival-order clues.','Professional':' No direct identity clues: reconstruct all object and room assignments from exclusions and arrival order, then test the witness accounts.','Special Challenge':' Solve a unique logic mystery from indirect clues; every connection matters.'}[level]
    case['completion'] = f'{story_title}: case closed. {full}'
    case['logic_model'] = model
    if not vary_dossier(case,history,rng):
        return strengthen(case,history,attempt+1)
    return case
