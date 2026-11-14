from datetime import timedelta
from io import BytesIO
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from PIL import Image

from .ai import Detections, create_story, generate, sanitize
from .content import CASES
from .models import Game, Scan


@override_settings(GEMINI_API_KEY="")
class GameTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.client.get("/api/")

    def post(self, path, data):
        return self.client.post(path, data, content_type="application/json",
                                HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value)

    def upload(self, consent="yes", photo=None):
        buffer = BytesIO()
        Image.new("RGB", (50, 50)).save(buffer, "PNG")
        return self.client.post("/api/scans/", {
            "photo": photo or SimpleUploadedFile("room.png", buffer.getvalue(), "image/png"),
            "consent": consent,
        }, HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value)

    def test_full_virtual_case(self):
        self.assertEqual(len(self.client.get("/api/").json()["scenes"]), 10)
        game = self.post("/api/start/", {"scene": "midnight"}).json()
        path = f"/api/games/{game['game_id']}/"
        self.assertEqual(game["phase"], "observe")
        self.assertIn("exhibits", game)
        self.assertNotIn("question", game)
        self.assertEqual(self.post(path + "answer/", {"position": 0, "answer": "11:40"}).status_code, 409)
        self.assertEqual(Client().get(path).status_code, 404)
        Game.objects.filter(pk=game["game_id"]).update(deadline=timezone.now()-timedelta(seconds=1))
        active = self.client.get(path).json()
        self.assertNotIn("exhibits", active)
        self.assertNotIn("answer", active["question"])
        self.assertEqual(self.post(path+"nova/", {"kind":"rules"}).json()["game"]["hints_remaining"], 3)
        for index, kind in enumerate(["hint", "assist", "hint"]):
            response = self.post(path+"nova/", {"kind":kind, "position":0, "message":"Help me."})
            self.assertEqual(response.json()["game"]["hints_remaining"], 2-index)
        self.assertEqual(self.post(path+"nova/", {"kind":"hint", "position":0}).status_code, 409)
        for index, puzzle in enumerate(Game.objects.get(pk=game["game_id"]).case["puzzles"]):
            response = self.post(path+"answer/", {"position":index, "answer":puzzle["answer"], "score":9000})
            self.assertEqual(response.status_code, 200)
        result = self.client.get(path).json()
        self.assertEqual((result["phase"], result["score"], result["correct"]), ("complete", 925, 5))
        self.assertEqual(len(result["review"]), 5)
        self.assertIn("exhibits", result)
        self.assertEqual(self.post(path+"answer/", {"position":4, "answer":"Station locker 27"}).status_code, 409)
        self.assertIn("Perfect Observer", self.client.get("/api/").json()["badges"])

    def test_fallback_scan_owner_and_deletion(self):
        self.assertEqual(self.upload("no").status_code, 400)
        self.assertEqual(self.upload(photo=SimpleUploadedFile("bad.png", b"bad", "image/png")).status_code, 400)
        response = self.upload()
        self.assertEqual(response.status_code, 201)
        scan = response.json()
        self.assertEqual(scan["source"], "Manual")
        path = f"/api/scans/{scan['id']}/"
        self.assertEqual(Client().post(path, {}, content_type="application/json").status_code, 404)
        game = self.post(path, {"objects":["lamp","key"], "theme":"Spy Mission", "difficulty":"Beginner"}).json()
        self.assertEqual(game["source"], "Puzzle engine fallback")
        game_path = f"/api/games/{game['game_id']}/"
        self.assertIn("lamp", str(game["question"]["evidence"]))
        puzzle = Game.objects.get(pk=game["game_id"]).case["puzzles"]
        for index, question in enumerate(puzzle):
            response = self.post(game_path+"answer/", {"position":index, "answer":question["answer"]})
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(game_path).json()["score"], 1000)
        result = self.client.delete(path, HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value)
        self.assertEqual(result.status_code, 204)
        self.assertFalse(Scan.objects.exists())
        self.assertEqual(self.client.get(game_path).json()["phase"], "complete")

    def test_account_claim_reset_and_delete(self):
        game = self.post("/api/start/", {"scene":"midnight"}).json()
        path = f"/api/games/{game['game_id']}/"
        self.assertEqual(self.client.post("/api/start/", {"scene":"midnight"}).status_code, 403)
        user = {"username":"det-nova","password":"River-44-Telescope%","email":"nova@example.test"}
        self.assertEqual(self.post("/api/account/register/",user).status_code, 201)
        self.assertNotEqual(get_user_model().objects.get().password, user["password"])
        self.assertEqual(self.client.get(path).status_code, 200)
        self.assertEqual(self.post("/api/account/logout/",{}).status_code, 200)
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.post("/api/account/reset/", {"username":user["username"]}).status_code, 200)
        token = mail.outbox[0].body.split("?reset=")[1]
        password = "Clock-104-Archive%"
        self.assertEqual(self.post("/api/account/confirm/", {"token":token, "password":password}).status_code, 200)
        self.assertEqual(self.post("/api/account/login/", {"username":user["username"], "password":password}).status_code, 200)
        self.assertEqual(self.post("/api/account/delete/", {"password":password}).status_code, 200)
        self.assertFalse(Game.objects.exists())

    @patch("cases.api.generate_round")
    @patch("cases.api.detect")
    def test_scan_to_generated_game(self, detection, story):
        detection.return_value = [{"id":"object_001","name":"lamp","description":"A lamp","confidence_label":"high","usable_for_puzzle":True}]
        story.side_effect = lambda case,history: dict(case,title="Ghost Relay",source="Gemini generated")
        scan = self.upload().json()
        self.assertEqual(scan["source"], "Gemini")
        self.assertEqual(scan["objects"][0]["name"], "lamp")
        self.assertIsInstance(detection.call_args.args[0], bytes)
        game = self.post(f"/api/scans/{scan['id']}/", {"objects":["lamp","key"],"theme":"Horror","difficulty":"Intermediate"}).json()
        self.assertEqual((game["title"],game["source"]), ("Ghost Relay","Gemini generated"))


@override_settings(GEMINI_API_KEY="testing-key", GEMINI_REQUESTS_PER_MINUTE=10)
class AITests(TestCase):
    def mock_client(self, client, text):
        response = MagicMock()
        response.text = text
        call = client.return_value.__enter__.return_value.models.generate_content
        call.return_value = response
        return call

    @patch("cases.ai.genai.Client")
    def test_malformed_quota_and_timeouts(self, client):
        call = self.mock_client(client, "{malformed")
        self.assertIsNone(generate("test", Detections))
        call.side_effect = TimeoutError()
        self.assertIsNone(generate("test", Detections))
        with self.settings(GEMINI_REQUESTS_PER_MINUTE=2):
            self.assertIsNone(generate("test", Detections))
        self.assertEqual(call.call_count, 2)

    @patch("cases.ai.genai.Client")
    def test_validate_references_and_cache(self, client):
        call = self.mock_client(client, '{"title":"Signal","intro":"A missing signal arrived during a fictional inquiry.","order":[0,9]}')
        self.assertEqual(create_story("one", ["lamp","key"], "Horror", "Beginner"), (None, "Prepared mystery"))
        call.return_value.text = '{"title":"Signal","intro":"A missing signal arrived during a fictional inquiry.","order":[1,0]}'
        first, source = create_story("one", ["lamp","key"], "Horror", "Beginner")
        self.assertEqual(source, "Gemini generated")
        self.assertEqual(first["order"], ["key","lamp"])
        self.assertEqual(create_story("one", ["lamp","key"], "Horror", "Beginner"), (first, "Cached Gemini"))
        self.assertEqual(call.call_count, 2)

    def test_metadata_removed(self):
        buffer = BytesIO()
        image = Image.new("RGB", (100,100))
        exif = image.getexif()
        exif[270] = "Private description"
        image.save(buffer, "JPEG", exif=exif)
        clean = sanitize(SimpleUploadedFile("image.jpg", buffer.getvalue(), "image/jpeg"))
        with Image.open(BytesIO(clean)) as sanitized:
            self.assertFalse(sanitized.getexif())



@override_settings(GEMINI_API_KEY="")
class VariationTests(GameTests):
    def test_new_attempt_changes_notes_and_visual_questions(self):
        first = self.post("/api/start/", {"scene":"midnight"}).json()
        second = self.post("/api/start/", {"scene":"midnight"}).json()
        old = Game.objects.get(pk=first["game_id"])
        new = Game.objects.get(pk=second["game_id"])
        self.assertNotEqual(old.case["exhibits"], new.case["exhibits"])
        self.assertFalse({p["question"] for p in old.case["puzzles"][:2]} &
                         {p["question"] for p in new.case["puzzles"][:2]})
        self.assertEqual(self.client.get(f"/api/games/{old.pk}/").json()["exhibits"], first["exhibits"])
        for case in (old.case, new.case):
            self.assertEqual(len(case["puzzles"]), 5)
            for item in case["puzzles"]:
                self.assertIn(item["answer"], item["options"])

    @patch("cases.api.generate_round")
    def test_saved_section_fallback_preserves_original_questions(self, story):
        scan = self.upload().json()
        body = {"objects":["lamp","key"], "theme":"Horror", "difficulty":"Beginner"}
        story.side_effect = lambda case,history: dict(case,title="Saved opening",source="Gemini generated")
        first = self.post(f"/api/scans/{scan['id']}/", body).json()
        old_case = Game.objects.get(pk=first["game_id"]).case
        story.side_effect = lambda case,history: dict(case,source="Puzzle engine fallback")
        second = self.post(f"/api/scans/{scan['id']}/", body).json()
        self.assertEqual(second["source"], "Puzzle engine fallback")
        self.assertEqual(old_case["title"], "Saved opening")
        self.assertNotEqual(old_case["exhibits"], Game.objects.get(pk=second["game_id"]).case["exhibits"])
        self.assertEqual(old_case, Game.objects.get(pk=first["game_id"]).case)


class RankingTests(TestCase):
    def test_ties_titles_and_private_rank(self):
        from .models import Profile
        from .rankings import leaderboard_rows, result_identity
        players = [get_user_model().objects.create_user(username=name) for name in ("alpha", "bravo", "charlie")]
        games = []
        for player, score in zip(players, [1000, 1000, 600]):
            Profile.objects.create(player=player, public_score=True)
            games.append(Game.objects.create(player=player, case=CASES["midnight"], score=score, completed=timezone.now()))
        rows = leaderboard_rows()
        self.assertEqual([row["rank"] for row in rows], [1, 1, 3])
        self.assertEqual(rows[2]["title"], "Field Investigator")
        self.assertEqual(result_identity(games[2])["leaderboard_rank"], 3)
        repeat = Game.objects.create(player=players[0], case=CASES["midnight"], score=200, completed=timezone.now())
        self.assertEqual(result_identity(repeat)["detective_title"], "Professional Detective")
        self.assertEqual(result_identity(repeat)["leaderboard_rank"], 1)
        Profile.objects.filter(player=players[2]).update(public_score=False)
        self.assertIsNone(result_identity(games[2])["leaderboard_rank"])
        guest = Game.objects.create(guest="example", case=CASES["midnight"], score=800, completed=timezone.now())
        self.assertIsNone(result_identity(guest)["leaderboard_rank"])
        self.assertEqual(result_identity(guest)["detective_title"], "Senior Detective")


class GenderRankTests(TestCase):
    def test_score_boundaries_and_character_identity(self):
        from .models import Profile
        from .rankings import detective_title, leaderboard_rows, result_identity
        for score, title in [(0,"Unlisted"),(1,"Unlisted"),(200,"Unlisted"),(201,"Clue Hunter"),(400,"Clue Hunter"),(401,"Field Investigator"),(600,"Field Investigator"),(601,"Senior Detective"),(800,"Senior Detective"),(801,"Professional Detective"),(1000,"Professional Detective")]:
            self.assertEqual(detective_title(score),title)
        for gender in ("male","female","others"):
            player = get_user_model().objects.create_user(username=gender)
            Profile.objects.create(player=player, gender=gender, avatar="key", public_score=True)
            game = Game.objects.create(player=player,case=CASES["midnight"],score=801,completed=timezone.now())
            self.assertEqual(result_identity(game)["character"],gender)
        self.assertEqual({row["character"] for row in leaderboard_rows()},{"male","female","others"})
        self.assertTrue(all(row["avatar"] == "key" for row in leaderboard_rows()))

    def test_registration_and_profile_gender_validation(self):
        payload = {"username":"newdetective","email":"detective@example.com","password":"A-unique-long-passphrase-742!","gender":"invalid"}
        self.assertEqual(self.client.post("/api/account/register/",payload,content_type="application/json").status_code,400)
        payload["gender"] = "female"
        payload["avatar"] = "fingerprint"
        self.assertEqual(self.client.post("/api/account/register/",payload,content_type="application/json").status_code,201)
        self.assertEqual(self.client.get("/api/").json()["profile"]["gender"],"female")
        self.assertEqual(self.client.get("/api/").json()["profile"]["avatar"],"fingerprint")
        update = {"avatar":"radar","public_score":True,"gender":"male"}
        self.assertEqual(self.client.post("/api/account/profile/",update,content_type="application/json").status_code,200)
        update["gender"] = "invalid"
        self.assertEqual(self.client.post("/api/account/profile/",update,content_type="application/json").status_code,400)
        self.assertEqual(self.client.get("/api/").json()["profile"]["gender"],"male")


class DifficultyAndVoiceTests(TestCase):
    def test_difficulty_deductions_have_unique_solutions(self):
        from itertools import permutations, product
        from .content import fresh_virtual_case, scanner_case
        from .mysteries import satisfies
        for repeat in range(12):
            for case in (fresh_virtual_case("midnight"),fresh_virtual_case("observatory"),fresh_virtual_case("vault"),scanner_case(["lamp","key"],"Detective","Professional")):
                self.assertEqual(len(case["puzzles"]),5)
                for question in case["puzzles"]:
                    self.assertEqual(len(question["options"]),len(set(question["options"])))
                    self.assertIn(question["answer"],question["options"])
                    self.assertNotIn("interval",question["question"])
                    self.assertNotIn("station number",question["question"])
                model = case["logic_model"]
                if case["difficulty"] == "Professional":
                    self.assertTrue(all(clue[1] != "eq" for clue in model["clues"]))
                if case["difficulty"] == "Intermediate":
                    self.assertLessEqual(sum(clue[1] == "eq" for clue in model["clues"]),2)
                solutions = [assignment for assignment in product(permutations(range(4)),repeat=2) if all(satisfies(assignment,clue) for clue in model["clues"])]
                self.assertEqual(solutions,[model["solution"]])
                self.assertIn(case["story_id"],__import__("cases.stories",fromlist=["STORIES"]).STORIES)
                for question in case["puzzles"]:
                    if question.get("answer_claim"):
                        category,index = question["answer_claim"]
                        self.assertEqual(question["answer"],model[{"person":"people","object":"objects","room":"rooms"}[category]][index])
            professional = fresh_virtual_case("vault")
            prior = {q["question"] for q in professional["puzzles"][:2]}
            next_case = fresh_virtual_case("vault",professional)
            self.assertFalse(prior & {q["question"] for q in next_case["puzzles"][:2]})
            self.assertNotEqual(professional["exhibits"],next_case["exhibits"])

    def test_voice_preferences_and_leaderboard_require_login(self):
        from .models import Profile
        self.assertEqual(self.client.get("/api/leaderboard/").status_code,403)
        self.assertEqual(self.client.post("/api/account/voice/",{"voice_style":"style:orion","voice_rate":1},content_type="application/json").status_code,403)
        user = get_user_model().objects.create_user(username="voice-test")
        Profile.objects.create(player=user)
        self.client.force_login(user)
        self.assertEqual(self.client.get("/api/leaderboard/").status_code,200)
        for style, rate in [("bad",1),("style:luna",True),("style:luna",9)]:
            self.assertEqual(self.client.post("/api/account/voice/",{"voice_style":style,"voice_rate":rate},content_type="application/json").status_code,400)
        self.assertEqual(self.client.post("/api/account/voice/",{"voice_style":"style:orion","voice_rate":0.75},content_type="application/json").status_code,200)
        profile = self.client.get("/api/").json()["profile"]
        self.assertEqual((profile["voice_style"],profile["voice_rate"]),("style:orion",0.75))


class LeagueTests(TestCase):
    def test_difficulty_attempt_time_ties_and_scanner_exclusion(self):
        from datetime import timedelta
        from .models import Profile
        from .rankings import leaderboard_rows, result_identity
        now = timezone.now()
        players = {}
        def run(name, level="Beginner", score=800, seconds=100, scene="midnight", complete=True):
            if name not in players:
                players[name] = get_user_model().objects.create_user(username=name)
                Profile.objects.create(player=players[name],public_score=True)
            game = Game.objects.create(player=players[name],case={**CASES["midnight"],"id":scene,"difficulty":level},score=score)
            Game.objects.filter(pk=game.pk).update(created=now-timedelta(seconds=seconds),completed=now if complete else None)
            game.refresh_from_db()
            return game
        slow = run("slow",seconds=120)
        fast = run("fast",seconds=90)
        run("equal",seconds=90)
        retry = run("retry",score=1000,seconds=40)
        run("retry",score=200,seconds=30)
        pro = run("fast",level="Professional",score=600,scene="vault")
        scanner = run("slow",score=1000,scene="scanner",seconds=1)
        run("slow",score=1000,scene="scanner",seconds=1)
        rows = leaderboard_rows("Beginner")
        self.assertEqual([(r["name"],r["rank"]) for r in rows],[("retry",1),("fast",2),("equal",2),("slow",4)])
        self.assertEqual(rows[-1]["attempts"],1)
        self.assertEqual(rows[-1]["total_time_ms"],120000)
        self.assertEqual(result_identity(slow)["rank_score"],800)
        self.assertIsNone(result_identity(scanner)["leaderboard_rank"])
        self.assertTrue(result_identity(scanner)["practice_only"])
        self.assertEqual(result_identity(pro)["leaderboard_rank"],1)
        self.assertEqual(result_identity(pro)["rank_score"],600)
        self.assertEqual(len(leaderboard_rows("Professional")),1)
        run("fast",complete=False)
        self.assertEqual(next(r["rank"] for r in leaderboard_rows() if r["name"]=="fast"),2)
        self.client.force_login(players["fast"])
        self.assertEqual(self.client.get("/api/leaderboard/?difficulty=Professional").json()[0]["score"],600)
        self.assertEqual(self.client.get("/api/leaderboard/?difficulty=scanner").status_code,400)

    def test_best_run_does_not_break_equal_total_times(self):
        from datetime import timedelta
        from .models import Profile
        from .rankings import leaderboard_rows
        now = timezone.now()
        for name, times in [("a",[80,120]),("b",[90,110])]:
            player = get_user_model().objects.create_user(username=name)
            Profile.objects.create(player=player,public_score=True)
            for seconds in times:
                game = Game.objects.create(player=player,case=CASES["midnight"],score=1000)
                Game.objects.filter(pk=game.pk).update(created=now-timedelta(seconds=seconds),completed=now)
        self.assertEqual([r["rank"] for r in leaderboard_rows()],[1,1])


class ChangeRoundTests(TestCase):
    def test_change_round_alternates_and_only_reveals_current_image(self):
        from datetime import timedelta
        from .content import fresh_virtual_case
        from .engine import serialize
        first = fresh_virtual_case("midnight")
        second = fresh_virtual_case("midnight",first)
        self.assertNotEqual(first["change_variant"],second["change_variant"])
        self.assertEqual(len(first["puzzles"]),5)
        game = Game.objects.create(guest="change-test",case=first,deadline=timezone.now()+timedelta(seconds=60))
        observing = serialize(game)
        self.assertTrue(observing["has_change_round"])
        self.assertNotIn("changed_image",str(observing))
        game.deadline = timezone.now()-timedelta(seconds=1)
        self.assertNotIn("changed_image",serialize(game)["question"])
        game.attempts = [{"submitted":first["puzzles"][0]["answer"],"correct":True}]
        current = serialize(game)["question"]
        self.assertEqual(current["changed_image"],first["puzzles"][1]["changed_image"])
        self.assertNotIn("answer",current)
        self.assertIn(first["puzzles"][1]["answer"],current["options"])
        game.attempts = [{"submitted":p["answer"],"correct":True} for p in first["puzzles"]]
        game.completed = timezone.now()
        self.assertEqual(serialize(game)["review"][1]["changed_image"],current["changed_image"])
        self.assertFalse(serialize(Game.objects.create(guest="old",case=CASES["midnight"]))["has_change_round"])


class ReplayDiversityTests(TestCase):
    def test_full_history_consumes_fixed_changes_and_caption_pairs_do_not_repeat(self):
        from .content import fresh_virtual_case, VISUAL_CLUES, EXTRA_VISUAL_CLUES
        history = []
        variants = []
        direct = []
        caption_sets = set()
        raw = {item[0] for item in [*VISUAL_CLUES["midnight"],*EXTRA_VISUAL_CLUES["midnight"]]}
        for _ in range(18):
            case = fresh_virtual_case("midnight",history[-1] if history else None,history)
            if case.get("change_variant"):
                variants.append(case["change_variant"])
            for question in case["puzzles"][:2]:
                if question["question"] in raw:
                    direct.append(question["question"])
                if question.get("photo_captions"):
                    key = tuple(sorted(tuple(pair) for pair in question["photo_captions"]))
                    self.assertNotIn(key,caption_sets)
                    caption_sets.add(key)
                    self.assertIn(question["answer"],question["options"])
                    self.assertTrue(any(question["answer"] in value for _,value in case["exhibits"]))
            history.append(case)
        self.assertEqual(set(variants),{"lamp","globe"})
        self.assertEqual(len(variants),2)
        self.assertTrue(all(variants.count(variant) == 1 for variant in set(variants)))
        self.assertTrue(all(direct.count(prompt) <= 1 for prompt in set(direct)))
        self.assertGreater(len(caption_sets),15)
        self.assertNotIn("change_variant",history[-1])

    def test_start_uses_all_owned_history_and_keeps_other_players_separate(self):
        from django.test import Client
        first = self.client.post("/api/start/",{"scene":"midnight"},content_type="application/json")
        self.assertEqual(first.status_code,201)
        for _ in range(5):
            self.assertEqual(self.client.post("/api/start/",{"scene":"midnight"},content_type="application/json").status_code,201)
        cases = list(Game.objects.order_by("created").values_list("case",flat=True))
        self.assertEqual(sum(bool(case.get("change_variant")) for case in cases),2)
        other = Client().post("/api/start/",{"scene":"midnight"},content_type="application/json")
        self.assertEqual(other.status_code,201)
        self.assertFalse(other.json()["has_change_round"])
        self.assertEqual(Client().get(f"/api/games/{other.json()['game_id']}/").status_code,404)


class StoryRotationTests(TestCase):
    def test_stories_rotate_and_all_question_wordings_are_capped_at_two(self):
        from .content import fresh_virtual_case, scanner_case
        from .stories import exposures, STORIES
        history = []
        for index in range(42):
            if index % 3 == 2:
                case = scanner_case(["lamp","key","book","vase"],"Detective","Intermediate",history=history)
            else:
                scene = "midnight" if index % 3 == 0 else "observatory"
                prior = next((old for old in reversed(history) if old["id"] == scene),None)
                case = fresh_virtual_case(scene,prior,history)
            if history:
                self.assertNotEqual(case["story_id"],history[-1]["story_id"])
            self.assertEqual(len(case["puzzles"]),5)
            self.assertLessEqual(sum(bool(q.get("changed_image")) for q in case["puzzles"]),1)
            history.append(case)
            self.assertLessEqual(max(exposures(history).values()),2)
        self.assertEqual({case["story_id"] for case in history[:len(STORIES)]},set(STORIES))
        self.assertEqual(len({str(case["logic_model"]) for case in history}),len(history))


class QuestionLimitFailureTests(TestCase):
    @patch("cases.api.fresh_virtual_case")
    def test_exhausted_pool_does_not_issue_a_repeat_or_create_an_attempt(self,create):
        from .stories import QuestionPoolExhausted
        create.side_effect = QuestionPoolExhausted
        response = self.client.post("/api/start/",{"scene":"midnight"},content_type="application/json")
        self.assertEqual(response.status_code,409)
        self.assertEqual(Game.objects.count(),0)


class PhotoPrivacyTests(TestCase):
    @patch("cases.ai.generate")
    def test_sensitive_photo_is_blocked_without_returning_private_values(self,generate):
        from .ai import Detections, detect
        from .privacy import PhotoPrivacyError
        generate.return_value = Detections(sensitive_content=True,privacy_flags=["contact_details"],objects=[])
        with self.assertRaises(PhotoPrivacyError):
            detect(b"photo")

    @patch("cases.ai.generate")
    def test_response_text_filter_and_uncertain_objects(self,generate):
        from .ai import Detections, Detection, detect
        from .privacy import PhotoPrivacyError
        generate.return_value = Detections(sensitive_content=False,privacy_flags=[],objects=[Detection(name="paper",description="Contact alex@example.com",confidence_label="high",usable_for_puzzle=True)])
        with self.assertRaises(PhotoPrivacyError):
            detect(b"photo")
        generate.return_value = Detections(sensitive_content=False,privacy_flags=[],objects=[Detection(name="lamp",description="A desk lamp",confidence_label="high",usable_for_puzzle=True),Detection(name="book",description="Possibly a book",confidence_label="low",usable_for_puzzle=True)])
        self.assertEqual([item["name"] for item in detect(b"photo")],["lamp"])

    @patch("cases.api.detect")
    def test_rejected_upload_creates_no_scan(self,detect):
        from .privacy import PhotoPrivacyError
        from .models import Scan
        detect.side_effect = PhotoPrivacyError("Cover private details and try again.")
        image = BytesIO()
        Image.new("RGB",(10,10)).save(image,"PNG")
        response = self.client.post("/api/scans/",{"photo":SimpleUploadedFile("test.png",image.getvalue(),"image/png"),"consent":"yes"})
        self.assertEqual(response.status_code,422)
        self.assertEqual(Scan.objects.count(),0)

    def test_contact_information_in_object_names_is_rejected_before_gemini(self):
        from .models import Scan
        from .privacy import contains_private_text
        self.client.get("/api/")
        scan = Scan.objects.create(guest=self.client.session["guest"],detections=[],source="Manual")
        for value in ["alex@example.com","+1 (202) 555-0123","www.example.com/private","my passport"]:
            self.assertTrue(contains_private_text(value))
            with patch("cases.api.generate_round") as generate:
                response = self.client.post(f"/api/scans/{scan.pk}/",{"objects":[value],"theme":"Detective","difficulty":"Beginner"},content_type="application/json")
                self.assertEqual(response.status_code,400)
                generate.assert_not_called()
        self.assertFalse(contains_private_text("mobile phone"))

    @patch("cases.ai.generate")
    def test_story_with_contact_details_is_not_cached(self,generate):
        from .ai import Story, create_story
        from .models import AICache
        generate.return_value = Story(title="A missing note",intro="A fictional clue says to email alex@example.com for details.",order=[0])
        self.assertEqual(create_story("privacy",["book"],"Detective","Beginner"),(None,"Prepared mystery"))
        self.assertEqual(AICache.objects.count(),0)


class CumulativeRankingTests(TestCase):
    def test_totals_cases_duration_and_completion_order(self):
        from datetime import timedelta
        from .models import Profile
        from .rankings import leaderboard_rows
        now = timezone.now()
        def player(name, scores, seconds, finish):
            user = get_user_model().objects.create_user(username=name)
            Profile.objects.create(player=user, public_score=True)
            for index,score in enumerate(scores):
                end=now+timedelta(seconds=finish+index*200)
                game=Game.objects.create(player=user,case=CASES['midnight'],score=score)
                Game.objects.filter(pk=game.pk).update(created=end-timedelta(seconds=seconds),completed=end)
            return user
        player('two_cases',[1000,1000],100,0)
        player('four_cases',[500,500,500,500],10,0)
        player('slow',[500],80,0)
        player('aaa_later',[500],60,100)
        player('zzz_earlier',[500],60,0)
        rows=leaderboard_rows()
        self.assertEqual([(r['name'],r['score'],r['attempts'],r['rank']) for r in rows],[
            ('two_cases',2000,2,1),('four_cases',2000,4,2),
            ('zzz_earlier',500,1,3),('aaa_later',500,1,3),('slow',500,1,5)])
        self.assertEqual(leaderboard_rows(),rows)  # Reading does not add points again.


class SceneStoryTests(TestCase):
    def test_scene_grounding_and_opening_variety(self):
        from .content import fresh_virtual_case, VISUAL_CLUES, EXTRA_VISUAL_CLUES
        from .scene_stories import SETTINGS
        for scene, (place,zones,occasions) in SETTINGS.items():
            case=fresh_virtual_case(scene)
            self.assertIn(place,case['story_title'])
            self.assertEqual(set(case['logic_model']['rooms']),set(zones))
            self.assertIn(case['scene_anchor'],case['intro'])
            self.assertIn(case['scene_anchor'],[f'{q} {answer}.' for q,options,answer in [*VISUAL_CLUES[scene],*EXTRA_VISUAL_CLUES[scene]]])
        history=[]
        for _ in range(18):
            case=fresh_virtual_case('observatory',history=history)
            self.assertNotIn(case['story_title'],[old['story_title'] for old in history])
            history.append(case)
