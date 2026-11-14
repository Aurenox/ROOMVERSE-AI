from django.db.models import Max

from .models import Game, Profile


def detective_title(score):
    for threshold, title in (
        (801, "Professional Detective"),
        (601, "Senior Detective"),
        (401, "Field Investigator"),
        (201, "Clue Hunter"),
        (0, "Unlisted"),
    ):
        if score >= threshold:
            return title


LEAGUES = ("Beginner", "Intermediate", "Professional", "Special Challenge")


def competitive_games(difficulty):
    from .content import CASES
    return Game.objects.filter(case__id__in=list(CASES), case__difficulty=difficulty)


def leaderboard_rows(difficulty="Beginner", limit=25):
    players = {}
    games = competitive_games(difficulty).filter(player__profile__public_score=True, completed__isnull=False).select_related("player__profile")
    for game in games.iterator():
        row = players.setdefault(game.player_id, {"player_id":game.player_id, "name":game.player.username,
            "character":game.player.profile.gender, "avatar":game.player.profile.avatar,
            "attempts":0, "total_time_ms":0, "score":0, "best_score":0, "completed_at":game.completed})
        row["attempts"] += 1
        row["score"] += game.score
        row["best_score"] = max(row["best_score"],game.score)
        row["total_time_ms"] += max(0, round((game.completed - game.created).total_seconds() * 1000))
        # When this player finished the latest case contributing to this total.
        row["completed_at"] = max(row["completed_at"],game.completed)
    def key(row):
        return (-row["score"], row["attempts"], row["total_time_ms"])
    # Completion time orders equal-ranked rows; it never changes their shared rank.
    ordered = sorted(players.values(), key=lambda row:(*key(row),row["completed_at"],row["player_id"]))

    previous = None
    rank = 0
    for position,row in enumerate(ordered,1):
        if key(row) != previous:
            rank = position
        previous = key(row)
        row.update(rank=rank, title=detective_title(row["best_score"]), difficulty=difficulty)
    return ordered if limit is None else ordered[:limit]


def result_identity(game):
    practice = game.case.get("id") == "scanner"
    difficulty = game.case["difficulty"]
    identity = {"detective_name":"Guest Detective", "detective_title":detective_title(game.score),
        "leaderboard_rank":None, "rank_score":game.score, "character":"others",
        "leaderboard_difficulty":None if practice else difficulty, "practice_only":practice}
    if game.player_id:
        identity["detective_name"] = game.player.username
        if not practice:
            best = competitive_games(difficulty).filter(player_id=game.player_id, completed__isnull=False).aggregate(best=Max("score"))["best"]
            identity["rank_score"] = best if best is not None else game.score
            identity["detective_title"] = detective_title(identity["rank_score"])
        profile = Profile.objects.filter(player_id=game.player_id).first()
        identity["character"] = profile.gender if profile else "others"
        if not practice and profile and profile.public_score:
            entry = next((row for row in leaderboard_rows(difficulty,limit=None) if row["player_id"] == game.player_id),None)
            if entry:
                identity["leaderboard_rank"] = entry["rank"]
    return identity
