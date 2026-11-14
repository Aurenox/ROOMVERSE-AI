"""Different evidence systems, each with computed solutions rather than renamed witnesses."""
from collections import Counter
from .stories import exposures, question_key
from .scene_stories import SETTINGS

FORMATS = ('inventory_audit','event_reconstruction','access_routes','witness_logic')


def choose_format(history,rng):
    counts=Counter(old.get('dossier_format','witness_logic') for old in history)
    last=history[-1].get('dossier_format','witness_logic') if history else 'witness_logic'
    options=[key for key in FORMATS if key != last]
    lowest=min(counts[key] for key in options)
    return rng.choice([key for key in options if counts[key]==lowest])


def vary_dossier(case,history,rng):
    family=choose_format(history,rng)
    case['dossier_format']=family
    if family=='witness_logic':return True
    model=case['logic_model']
    objects=model['objects']; zones=model['rooms']
    advanced=case['difficulty'] in ('Professional','Special Challenge')
    intermediate=case['difficulty']=='Intermediate'
    notes=[]; questions=[]
    def add(prompt,answer,options,explanation):
        values=list(dict.fromkeys([str(answer),*map(str,options)]))[:4]
        rng.shuffle(values)
        questions.append(dict(question=prompt,answer=str(answer),options=values,evidence=None,
            hints=['Recall the rules for this dossier.','Combine the relevant records before choosing an option.',explanation],
            explanation=explanation,kind=family))
    def numeric(prompt,answer,explanation):
        add(prompt,answer,[answer+1,answer+3,max(0,answer-2),answer+7],explanation)
    context=SETTINGS.get(case['id'],[case.get('location') or 'your confirmed object collection'])[0]
    if family=='inventory_audit':
        title='The Reconciliation Error'
        objective='Audit the evidence packets and identify the unexplained shortage.'
        opening='A packet audit disagrees with the authorized transfer ledger. Reconcile quantities; there are no witness statements in this investigation.'
        opening_counts=rng.sample(range(18,65),4)
        received=[rng.randint(2,9) for _ in objects];sent=[rng.randint(2,8) for _ in objects]
        returned=[rng.randint(1,5) if advanced or intermediate else 0 for _ in objects]
        held=[rng.randint(1,4) if advanced else 0 for _ in objects]
        expected=[opening_counts[i]+received[i]-sent[i]+returned[i]-held[i] for i in range(4)]
        culprit=rng.randrange(4);shortage=rng.randint(2,7);observed=expected[:];observed[culprit]-=shortage
        notes=[['Audit rule','These are fictional evidence packets labeled after scene objects, not quantities visible in the image. Expected shelf count = opening + received - sent + returned - held off-shelf. Exactly one shelf count is wrong.']]
        for i,label in enumerate(objects):
            notes.append([f'{label} packet ledger',f'Opening {opening_counts[i]}; received {received[i]}; sent {sent[i]}; returned {returned[i]}; held off-shelf {held[i]}; counted on shelf {observed[i]}.'])
        add(f'Which packet label has an unexplained shortage in this audit with {sum(opening_counts)} opening packets?',objects[culprit],objects,f'{objects[culprit]} should have {expected[culprit]} on the shelf, but has {observed[culprit]}.')
        numeric(f'For {objects[culprit]}, what shelf count follows from opening {opening_counts[culprit]} and all authorized movements?',expected[culprit],f'Compute {opening_counts[culprit]} + {received[culprit]} - {sent[culprit]} + {returned[culprit]} - {held[culprit]} = {expected[culprit]}.')
        numeric(f'How many packets are unaccounted for under {objects[culprit]} after reconciling its counted shelf of {observed[culprit]}?',shortage,f'{expected[culprit]} expected minus {observed[culprit]} counted leaves {shortage}.')
        numeric(f'With {sum(opening_counts)} opening packets, what is the expected total shelf count after every ledger movement?',sum(expected),f'Add the four expected shelf counts: {" + ".join(map(str,expected))} = {sum(expected)}.')
        numeric(f'After excluding the disputed {objects[culprit]} shelf, how many packets were actually counted elsewhere?',sum(observed)-observed[culprit],f'Sum the other three recorded shelf counts to obtain {sum(observed)-observed[culprit]}.')
        reference=f'{objects[culprit]} / {sum(opening_counts)} packets'
        proof=dict(kind=family,opening=opening_counts,received=received,sent=sent,returned=returned,held=held,observed=observed,expected=expected,culprit=culprit,shortage=shortage)
    elif family=='event_reconstruction':
        title='The Misaligned Event Log'
        objective='Reconstruct four inspection events and correct the recording clock.'
        opening='The scene inspection recorder lost its absolute timestamps. Relative event gaps survived. Recover the timeline from those fragments instead of tracking visitors.'
        order=rng.sample(objects,4);base=rng.randint(8*60,20*60)
        gaps=[rng.randint(3,14) for _ in range(3)];drift=rng.randint(2,9) if advanced or intermediate else 0
        times=[base]
        for gap in gaps:times.append(times[-1]+gap)
        def clock(value):return f'{value//60:02d}:{value%60:02d}'
        notes=[['Recorder calibration',f'The recorder runs {drift} minutes fast. Subtract that error to obtain actual time. All events happened on the same day. These are fictional inspection logs, not text visible in the image.'],
               ['Surviving timestamp',f'The {order[0]} inspection is recorded at {clock(base+drift)}.']]
        fragments=[]
        for i,gap in enumerate(gaps):
            fragments.append([f'Event fragment {i+1}',f'{order[i]} was inspected {gap} minutes before {order[i+1]}.' if advanced else f'{order[i+1]} was inspected {gap} minutes after {order[i]}.'])
        if advanced:rng.shuffle(fragments)
        notes+=fragments
        add(f'At what actual time did the final {order[3]} inspection occur after the {clock(base+drift)} recorder entry?',clock(times[3]),[clock(times[3]+1),clock(times[3]-2),clock(times[3]+4)],f'Correct the first timestamp, then add all gaps: {clock(base)} + {sum(gaps)} minutes = {clock(times[3])}.')
        numeric(f'How many actual minutes separate the {order[0]} and {order[2]} inspections in the log anchored at {clock(base+drift)}?',sum(gaps[:2]),f'Combine the first two gaps: {gaps[0]} + {gaps[1]} = {sum(gaps[:2])}.')
        add(f'Which object was inspected immediately before {order[3]} in the {clock(base+drift)} log?',order[2],order,f'The final surviving fragment places {order[2]} before {order[3]}.')
        add(f'What was the actual time of the {order[0]} inspection recorded at {clock(base+drift)}?',clock(base),[clock(base+1),clock(base+3),clock(base-2)],f'Subtract the {drift}-minute recorder error: {clock(base+drift)} becomes {clock(base)}.')
        numeric(f'How long did the whole four-event inspection sequence beginning at actual {clock(base)} last?',sum(gaps),f'Add the three gaps: {" + ".join(map(str,gaps))} = {sum(gaps)} minutes.')
        reference=f'{order[0]} / {clock(base+drift)}'
        proof=dict(kind=family,base=base,gaps=gaps,drift=drift,times=times,order=order)
    else:
        title='The Locked Recovery Route'
        objective='Find the one authorized recovery route and diagnose the rejected gate.'
        opening='An automated access system offers four recovery routes. Only one can be completed using the issued credentials. Read the access policy and route cards; no suspect interviews are needed.'
        symbols=rng.sample(['sun','moon','wave','leaf','star','flame','snow','spiral'],4)
        held=set(symbols[:2]);missing=symbols[2]
        gates=rng.sample([f"{item} marker" for item in objects] if case["id"]=="scanner" else zones,4);closed=gates[3]
        routes=rng.sample(['Amber','Cobalt','Jade','Quartz','Ruby','Silver','Indigo','Pearl'],4)
        paths=[gates[:3]]+[rng.sample([closed,*rng.sample(gates[:3],2)],3) for _ in range(3)]
        notes=[['Issued credentials',f'Badge symbols: {symbols[0]} and {symbols[1]}. All named gates are fictional checkpoints in this case.'],
               ['Access policy','Every gate in a route must authorize passage. A blocked gate invalidates the entire route. No credential is consumed by passing a gate.']]
        for i,gate in enumerate(gates):
            rule=f'requires {symbols[0]} AND {missing}' if i==3 else (f'requires {symbols[0]} AND NOT {symbols[3]}' if advanced and i==1 else f'requires {symbols[i%2]}')
            notes.append([f'Gate: {gate}',rule])
        route_notes=[[f'{name} route',' → '.join(path)] for name,path in zip(routes,paths)];rng.shuffle(route_notes);notes+=route_notes
        add(f'Which recovery route accepts the {symbols[0]} / {symbols[1]} badge at every checkpoint?',routes[0],routes,f'Only {routes[0]} avoids the {closed}, which needs the missing {missing} credential.')
        add(f'Which checkpoint blocks the {routes[1]} route for the issued {symbols[0]} / {symbols[1]} badge?',closed,gates,f'The {closed} requires both {symbols[0]} and {missing}; the issued badge lacks {missing}.')
        add(f'Which extra credential would authorize the blocked {closed} on route {routes[1]}?',missing,symbols,f'The badge already has {symbols[0]}; adding {missing} satisfies the remaining requirement.')
        add(f'On the only authorized route for the {symbols[0]} / {symbols[1]} badge, which checkpoint is second?',gates[1],gates,f'The authorized {routes[0]} route is {" → ".join(paths[0])}; {gates[1]} is second.')
        add(f'Where does the authorized {routes[0]} recovery route finish after its first two checkpoints?',gates[2],gates,f'The third and final checkpoint on {routes[0]} is {gates[2]}.')
        reference=f'{routes[0]} / {symbols[0]} and {symbols[1]}'
        proof=dict(kind=family,held=sorted(held),missing=missing,closed=closed,routes=dict(zip(routes,paths)),authorized=routes[0])
    counts=exposures(history)
    available=[q for q in questions if counts[question_key(q['question'])]<2]
    count=5 if case['id']=='scanner' else 3
    if len(available)<count:return False
    # Preserve the central investigation question and vary the remaining deductions.
    selected=[available[0],*rng.sample(available[1:],count-1)]
    new_title=f'{context}: {title} — {reference}'
    if any(old.get('story_title') == new_title for old in history):return False
    case['puzzles']=selected if case['id']=='scanner' else [*case['puzzles'][:2],*selected]
    case['exhibits']=notes
    case['evidence_model']=proof
    case['story_title']=new_title
    case['intro']=f'At {context}, {opening} This case concerns {reference}. Study the scene image separately from these fictional records. ' + case.get('scene_anchor','')
    case['objective']=objective
    case['completion']=f'{title}: case closed. The review shows how each answer follows from the records.'
    return True
