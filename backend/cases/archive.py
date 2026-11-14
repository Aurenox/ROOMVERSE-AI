"""Persistent cross-player duplicate index for fictional virtual-case content."""
import hashlib
import json
from django.db import IntegrityError, transaction
from django.db.models import Q

from .models import ArchiveFingerprint, RoundArchive
from .stories import question_key, QuestionPoolExhausted


class DuplicateRound(Exception):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def section(case):
    from .content import CASES
    return f"{case['id']}:{case['difficulty']}" if case.get('id') in CASES else None


def fingerprints(case):
    evidence = digest(case.get('exhibits',[]))
    result = {('story',digest([question_key(case.get('story_title','')),question_key(case['intro'])]))}
    for q in case['puzzles']:
        # Changing option order or punctuation does not create a new question.
        result.add(('question',digest(question_key(q['question']))))
        # Same reasoning target with identical evidence is a duplicate even if rewritten.
        result.add(('target',digest([question_key(q.get('source_question',q['question'])),question_key(q['answer']),evidence])))
    return result


def archive_history(scene_id):
    # A bounded prompt/selection window; the indexed check below covers ALL stored entries.
    return list(reversed(list(RoundArchive.objects.filter(section__startswith=f'{scene_id}:').order_by('-created').values_list('payload',flat=True)[:100])))


def merge_history(*groups):
    seen=set()
    result=[]
    for group in groups:
        for case in group:
            key=digest(case)
            if key not in seen:
                seen.add(key);result.append(case)
    return result


def duplicate(case):
    scope=section(case)
    if not scope:return False
    query=Q()
    for kind,value in fingerprints(case):
        query |= Q(kind=kind,digest=value)
    return ArchiveFingerprint.objects.filter(query,section=scope).exists()


def preserve(case, backfill=False):
    scope=section(case)
    if not scope:return  # Scanner content stays in its owner's Game archive.
    try:
        with transaction.atomic():
            if not backfill and duplicate(case):raise DuplicateRound
            record,created=RoundArchive.objects.get_or_create(digest=digest(case),defaults={'section':scope,'payload':case})
            if not created and not backfill:raise DuplicateRound
            entries=[ArchiveFingerprint(archive=record,section=scope,kind=kind,digest=value) for kind,value in fingerprints(case)]
            if backfill:
                for entry in entries:
                    ArchiveFingerprint.objects.get_or_create(section=scope,kind=entry.kind,digest=entry.digest,defaults={'archive':record})
            else:
                ArchiveFingerprint.objects.bulk_create(entries)
    except IntegrityError as exc:
        raise DuplicateRound from exc


def distinct_round(case, history):
    """Regenerate local fallback if a candidate overlaps the permanent archive."""
    if not duplicate(case):return case
    from .content import fresh_virtual_case
    attempts=list(history)
    for _ in range(12):
        attempts.append(case)
        case=fresh_virtual_case(case['id'],history=attempts)
        case.update(source='Puzzle engine fallback',generation='engine')
        if not duplicate(case):return case
    raise QuestionPoolExhausted
