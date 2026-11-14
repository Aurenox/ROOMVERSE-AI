import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .ai import detect, sanitize
from .round_ai import generate_round, eligible
from .archive import archive_history, merge_history, distinct_round, preserve, DuplicateRound
from .content import CASES, DIFFICULTIES, THEMES, catalog, scanner_case, fresh_virtual_case
from .engine import HINT_LIMIT, badges, recalculate, serialize, stage
from .models import Game, Profile, Scan
from .rankings import leaderboard_rows, LEAGUES
from .stories import QuestionPoolExhausted
from .privacy import PhotoPrivacyError, contains_private_text

User = get_user_model()


def endpoint(methods):
    def decorate(view):
        def validate_body(request, *args, **kwargs):
            if request.method == "POST" and not isinstance(request.data, dict):
                return problem("Send an object with the request fields.")
            return view(request, *args, **kwargs)

        wrapped = api_view(methods)(validate_body)
        wrapped.csrf_exempt = False
        return never_cache(csrf_protect(wrapped))
    return decorate


def ownership(request):
    if request.user.is_authenticated:
        return {"player": request.user}
    if "guest" not in request.session:
        request.session["guest"] = secrets.token_hex(24)
    return {"guest": request.session["guest"], "player": None}


def claim_guest(guest, player):
    if guest:
        for model in (Game, Scan):
            model.objects.filter(guest=guest, player=None).update(player=player, guest="")


def problem(message, status=400):
    return Response({"detail": message}, status=status)


@endpoint(["GET"])
@ensure_csrf_cookie
def index(request):
    owner = ownership(request)
    games = Game.objects.filter(**owner)
    profile = None
    if request.user.is_authenticated:
        record, _ = Profile.objects.get_or_create(player=request.user)
        profile = {"username": request.user.username, "avatar": record.avatar, "public_score": record.public_score, "gender": record.gender, "voice_style": record.voice_style, "voice_rate": record.voice_rate}
    completed = games.filter(completed__isnull=False)
    xp = sum(completed.values_list("score", flat=True))
    return Response({
        "scenes": catalog(), "themes": list(THEMES), "difficulty": DIFFICULTIES[:3],
        "ai_configured": bool(settings.GEMINI_API_KEY), "profile": profile, "xp": xp,
        "level": 1 + xp // 1000, "badges": badges(games),
        "history": [
            {"id": str(game.pk), "title": game.case["title"], "phase": stage(game), "score": game.score}
            for game in games.order_by("-created")[:30]
        ],
        "scans": [{"id": str(scan.pk), "created": scan.created} for scan in Scan.objects.filter(**owner).order_by("-created")[:30]],
    })


@endpoint(["POST"])
def start(request):
    case = CASES.get(str(request.data.get("scene", "")))
    if not case:
        return problem("Choose a listed virtual scene.")
    owner = ownership(request)
    history = list(Game.objects.filter(**owner).order_by("created").values_list("case", flat=True))
    diversity = merge_history(archive_history(case["id"]),history)
    prior = next((old for old in reversed(diversity) if old.get("id") == case["id"]),None)
    try:
        case = fresh_virtual_case(case["id"], prior, diversity)
    except QuestionPoolExhausted:
        return problem("You have reached the available question limit for this case. Choose another scene for fresh clues.",409)
    case = generate_round(case,diversity)
    try:
        case = distinct_round(case,diversity)
    except QuestionPoolExhausted:
        return problem("The archive could not find a fresh round. Choose another scene.",409)
    with transaction.atomic():
        if request.user.is_authenticated:
            User.objects.select_for_update().get(pk=request.user.pk)
        current = list(Game.objects.filter(**owner).order_by("created").values_list("case",flat=True))
        if len(current) != len(history):
            # A simultaneous attempt consumed evidence while Gemini was responding.
            # Never hold a database write lock during a provider request.
            try:
                case = fresh_virtual_case(case["id"], next((old for old in reversed(current) if old.get("id") == case["id"]),None), current)
                case.update(source="Puzzle engine fallback",generation="engine")
            except QuestionPoolExhausted:
                return problem("Choose another scene for fresh clues.",409)
        try:
            case = distinct_round(case,merge_history(archive_history(case["id"]),current))
        except QuestionPoolExhausted:
            return problem("Choose another scene for fresh archived clues.",409)
        if not eligible(case,current):
            return problem("This round overlaps your recent questions. Please start a fresh round.",409)
        try:
            preserve(case)
        except DuplicateRound:
            return problem("Another round just used this content. Please try again for a fresh round.",409)
        game = Game.objects.create(**owner, case=case,
                                   deadline=timezone.now() + timedelta(seconds=settings.OBSERVATION_SECONDS))
    return Response(serialize(game), status=201)


@endpoint(["GET"])
def game_detail(request, pk):
    return Response(serialize(get_object_or_404(Game, pk=pk, **ownership(request))))


@endpoint(["POST"])
def answer(request, pk):
    owner = ownership(request)
    position = request.data.get("position")
    submitted = request.data.get("answer")
    if type(position) is not int or not isinstance(submitted, str):
        return problem("Choose an answer for the current question.")
    with transaction.atomic():
        query = Game.objects.filter(pk=pk, **owner)
        game = get_object_or_404(query.select_for_update())
        if stage(game) != "quiz" or position != len(game.attempts):
            return problem("This question is no longer active. Refresh your case.", 409)
        puzzle = game.case["puzzles"][position]
        if submitted not in puzzle["options"]:
            return problem("Choose one of the supplied options.")
        attempt = {"submitted": submitted, "correct": submitted == puzzle["answer"]}
        game.attempts = [*game.attempts, attempt]
        if len(game.attempts) == len(game.case["puzzles"]):
            game.completed = timezone.now()
        recalculate(game)
        if not query.filter(attempts=game.attempts[:-1], hints=game.hints, completed__isnull=True).update(
            attempts=game.attempts, completed=game.completed, score=game.score,
        ):
            return problem("The case changed. Refresh before continuing.", 409)
        return Response({"game": serialize(game), "correct": attempt["correct"]})


@endpoint(["POST"])
def nova(request, pk):
    owner = ownership(request)
    kind = request.data.get("kind")
    message = request.data.get("message", "")
    if kind not in ("hint", "assist", "rules", "objective", "progress") or not isinstance(message, str) or len(message) > 500:
        return problem("Choose a Nova action and keep messages under 500 characters.")
    with transaction.atomic():
        query = Game.objects.filter(pk=pk, **owner)
        game = get_object_or_404(query.select_for_update())
        position = len(game.attempts)
        if kind == "rules":
            reply = "Solve five questions for up to 1,000 points. Each case includes three optional hints, at 25 points each."
        elif kind == "objective":
            reply = game.case["objective"]
        elif kind == "progress":
            reply = f"You’ve answered {position} of five questions. Your current score is {game.score}."
        else:
            if stage(game) != "quiz" or request.data.get("position") != position:
                return problem("Open the active question before requesting a hint.", 409)
            if len(game.hints) >= HINT_LIMIT:
                return problem("You have used all three hints in this case.", 409)
            level = sum(hint["position"] == position for hint in game.hints)
            reply = game.case["puzzles"][position]["hints"][level]
            if kind == "assist":
                reply = "Let’s focus on this part of the evidence. " + reply
            previous = game.hints
            game.hints = [*previous, {"position": position, "text": reply}]
            recalculate(game)
            if not query.filter(hints=previous, attempts=game.attempts, completed__isnull=True).update(hints=game.hints, score=game.score):
                return problem("The case changed. Refresh before continuing.", 409)
        return Response({"game": serialize(game), "message": reply})


@endpoint(["POST"])
def scan_create(request):
    if request.data.get("consent") != "yes":
        return problem("Confirm permission to process the photograph first.")
    try:
        image = sanitize(request.FILES.get("photo"))
    except ValueError as exc:
        return problem(str(exc))
    try:
        objects = detect(image)
    except PhotoPrivacyError as exc:
        return problem(str(exc),422)
    scan = Scan.objects.create(**ownership(request), detections=objects or [], source="Gemini" if objects is not None else "Manual")
    return Response({"id": str(scan.pk), "source": scan.source, "objects": scan.detections, "privacy_status": "checked" if objects is not None else "unavailable"}, status=201)


@endpoint(["POST", "DELETE"])
def scan_detail(request, pk):
    owner = ownership(request)
    scan = get_object_or_404(Scan, pk=pk, **owner)
    if request.method == "DELETE":
        scan.delete()
        return Response(status=204)
    raw = request.data.get("objects")
    theme = request.data.get("theme")
    difficulty = request.data.get("difficulty")
    if not isinstance(theme, str) or theme not in THEMES or difficulty not in DIFFICULTIES[:3]:
        return problem("Choose a valid theme and difficulty.")
    if not isinstance(raw, list) or not 1 <= len(raw) <= 10:
        return problem("Confirm one to ten distinct objects.")
    if any(not isinstance(item, str) or not 1 <= len(item.strip()) <= 45 or any(ord(c) < 32 for c in item) for item in raw):
        return problem("Each object needs a name between 1 and 45 characters.")
    objects = [item.strip() for item in raw]
    if any(contains_private_text(item) for item in objects):
        return problem("Use generic object names only. Remove phone numbers, email addresses, URLs, and sensitive document details.")
    if len({item.casefold() for item in objects}) != len(objects):
        return problem("Give each confirmed object a distinct name.")
    section = {"objects": sorted(objects), "theme": theme, "difficulty": difficulty}
    history = list(Game.objects.filter(**owner).order_by("created").values_list("case",flat=True))
    try:
        case = scanner_case(objects,theme,difficulty,history=history)
    except QuestionPoolExhausted:
        return problem("Choose different objects for fresh practice questions.",409)
    case = generate_round(case,history)
    with transaction.atomic():
        if request.user.is_authenticated:
            User.objects.select_for_update().get(pk=request.user.pk)
        get_object_or_404(Scan,pk=pk,**owner)
        current = list(Game.objects.filter(**owner).order_by("created").values_list("case",flat=True))
        if len(current) != len(history):
            try:
                case = scanner_case(objects,theme,difficulty,history=current)
                case.update(source="Puzzle engine fallback",generation="engine")
            except QuestionPoolExhausted:
                return problem("Choose different objects for fresh practice questions.",409)
        if not eligible(case,current):
            return problem("This round overlaps your recent questions. Please start a fresh round.",409)
        case.update(section=section)
        game = Game.objects.create(**owner, case=case)
    return Response(serialize(game), status=201)


@endpoint(["GET"])
def leaderboard(request):
    if not request.user.is_authenticated:
        raise PermissionDenied("Sign in to view the leaderboard.")
    difficulty = request.query_params.get("difficulty", "Beginner")
    if difficulty not in LEAGUES:
        return problem("Choose a listed leaderboard difficulty.")
    return Response([{key:value for key,value in row.items() if key != "player_id"} for row in leaderboard_rows(difficulty)])


@endpoint(["POST"])
def account(request, action):
    data = request.data
    username, password = data.get("username", ""), data.get("password", "")
    if not isinstance(username, str) or not isinstance(password, str) or len(username) > 150 or len(password) > 128:
        return problem("Check your username and password.")
    if action == "logout":
        logout(request)
        return Response({"ok": True})
    if action == "register":
        gender = data.get("gender", "others")
        if gender not in ("male", "female", "others"):
            return problem("Choose Male, Female, or Others.")
        avatar = data.get("avatar", "radar")
        if avatar not in ("radar", "fingerprint", "key"):
            return problem("Choose a listed detective avatar.")
        email = data.get("email", "")
        if not isinstance(email, str) or not email.strip() or len(email) > 254:
            return problem("Enter a valid email address.")
        user = User(username=username, email=email.strip())
        try:
            user.full_clean(exclude=["password"])
            validate_password(password, user)
            with transaction.atomic():
                user.set_password(password)
                user.save()
                Profile.objects.create(player=user, gender=gender, avatar=avatar)
        except ValidationError as exc:
            return problem(" ".join(exc.messages))
        except IntegrityError:
            return problem("This account could not be registered.", 409)
        claim_guest(request.session.get("guest"), user)
        login(request, user)
        return Response({"ok": True}, status=201)
    if action == "login":
        user = authenticate(request, username=username, password=password)
        if not user:
            return problem("Username or password is incorrect.", 401)
        claim_guest(request.session.get("guest"), user)
        login(request, user)
        return Response({"ok": True})
    if action == "reset":
        if username:
            user = User.objects.filter(username=username, is_active=True).first()
            if user and user.email:
                token = default_token_generator.make_token(user)
                user.email_user("Reset your Roomverse password",
                                f"Open {settings.PUBLIC_ORIGIN}/?reset={user.pk}.{token}", fail_silently=True)
        return Response({"ok": True})
    if action == "confirm":
        value = data.get("token")
        if not isinstance(value, str) or "." not in value or len(value) > 120:
            return problem("The reset link is invalid or expired.")
        pk, token = value.split(".", 1)
        user = User.objects.filter(pk=int(pk), is_active=True).first() if len(pk) <= 18 and pk.isascii() and pk.isdigit() else None
        if not user or not default_token_generator.check_token(user, token):
            return problem("The reset link is invalid or expired.")
        try:
            validate_password(password, user)
        except ValidationError as exc:
            return problem(" ".join(exc.messages))
        user.set_password(password)
        user.save(update_fields=["password"])
        return Response({"ok": True})
    if not request.user.is_authenticated:
        raise PermissionDenied("Sign in to manage your profile.")
    if action == "voice":
        style, rate = data.get("voice_style"), data.get("voice_rate")
        if style not in ("style:luna", "style:orion") or type(rate) not in (int, float) or rate not in (0.75, 0.9, 1, 1.15):
            return problem("Choose a listed voice and reading speed.")
        record, _ = Profile.objects.get_or_create(player=request.user)
        record.voice_style, record.voice_rate = style, rate
        record.save(update_fields=["voice_style", "voice_rate"])
        return Response({"ok": True})
    if action == "profile":
        avatar, public = data.get("avatar"), data.get("public_score")
        if avatar not in ("radar", "fingerprint", "key") or type(public) is not bool:
            return problem("Choose an avatar and leaderboard visibility.")
        record, _ = Profile.objects.get_or_create(player=request.user)
        gender = data.get("gender", record.gender)
        if gender not in ("male", "female", "others"):
            return problem("Choose Male, Female, or Others.")
        record.avatar, record.public_score, record.gender = avatar, public, gender
        record.save(update_fields=["avatar", "public_score", "gender"])
        return Response({"ok": True})
    if action == "delete":
        if not request.user.check_password(password):
            return problem("Enter your current password to delete the account.")
        request.user.delete()
        logout(request)
        return Response({"ok": True})
    return problem("Unknown account action.", 404)
