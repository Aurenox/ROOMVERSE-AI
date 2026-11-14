from django.utils import timezone
from .rankings import result_identity

HINT_LIMIT = 3
POINTS = 200
HINT_COST = 25
COUNT = 5


def stage(game):
    if game.completed:
        return "complete"
    if game.deadline and game.deadline > timezone.now():
        return "observe"
    return "quiz"


def serialize(game):
    case = game.case
    phase = stage(game)
    data = {key: case[key] for key in ("title", "id", "difficulty", "intro", "objective", "source")}
    data.update(
        game_id=str(game.pk), phase=phase, position=len(game.attempts),
        score=game.score, hints_remaining=HINT_LIMIT - len(game.hints),
        deadline=game.deadline, server_time=timezone.now(),
    )
    data["story_title"] = case.get("story_title", "")
    data["has_change_round"] = bool(case.get("change_variant"))
    if phase in {"observe", "complete"}:
        data["exhibits"] = case["exhibits"]
    if phase == "quiz":
        question = case["puzzles"][len(game.attempts)]
        data["question"] = {key: question[key] for key in ("question", "options", "evidence")}
        if question.get("changed_image"):
            data["question"]["changed_image"] = question["changed_image"]
        data["hints"] = [hint["text"] for hint in game.hints if hint["position"] == len(game.attempts)]
    if phase == "complete":
        data.update(result_identity(game))
        correct = sum(attempt["correct"] for attempt in game.attempts)
        data.update(
            completion=case["completion"], hints_used=len(game.hints), correct=correct,
            elapsed=max(0, int((game.completed - game.created).total_seconds())),
            review=[
                dict(attempt, question=puzzle["question"], answer=puzzle["answer"], explanation=puzzle["explanation"], changed_image=puzzle.get("changed_image"))
                for attempt, puzzle in zip(game.attempts, case["puzzles"], strict=True)
            ],
        )
    return data


def recalculate(game):
    game.score = max(0, POINTS * sum(attempt["correct"] for attempt in game.attempts) - HINT_COST * len(game.hints))


def badges(games):
    completed = list(games.filter(completed__isnull=False))
    awards = []
    checks = [
        ("First Investigation", bool(completed)),
        ("Perfect Observer", any(all(a["correct"] for a in g.attempts) for g in completed)),
        ("No-Hint Detective", any(g.score and not g.hints for g in completed)),
        ("Mystery Solver", any(g.score >= 600 for g in completed)),
        ("Speed Investigator", any(g.score >= 600 and (g.completed - g.created).total_seconds() < 180 for g in completed)),
        ("Master Detective", sum(g.score >= 600 for g in completed) >= 5),
        ("Reality Explorer", any(g.case["id"] == "scanner" for g in completed)),
    ]
    for label, awarded in checks:
        if awarded:
            awards.append(label)
    return awards
