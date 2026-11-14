# API contract

Requests use same-origin Django session cookies. Begin with GET /api/ to receive the session and CSRF cookie. Include X-CSRFToken for POST and DELETE. Use application/json unless uploading multipart data.

| Method and path | Input and result |
| --- | --- |
| GET /api/ | Case catalog, AI configuration, themes, profile, badges, scans, and game history |
| POST /api/start/ | scene ID, returns new virtual game in observation |
| GET /api/games/{id}/ | Owned game. Observation returns exhibits, quiz returns only the active question, completion returns review |
| POST /api/games/{id}/answer/ | Zero-based position and exact selected option as answer, returns updated game and correctness |
| POST /api/games/{id}/nova/ | kind, optionally position and message. rules, objective, and progress are free. hint and assist consume allowance and require position |
| POST /api/scans/ | Multipart photo and consent=yes, returns ID, source label, and detections |
| POST /api/scans/{id}/ | objects as an array of one to ten distinct names, theme, difficulty. Returns a playable case |
| DELETE /api/scans/{id}/ | Removes the owned detection record |
| GET /api/leaderboard/ | Up to 25 opted-in players ranked by highest validated score |
| POST /api/account/register/ | username, email, password |
| POST /api/account/login/ | username, password |
| POST /api/account/logout/ | Empty JSON object |
| POST /api/account/reset/ | username. The response stays the same for unknown usernames |
| POST /api/account/confirm/ | token and new password |
| POST /api/account/profile/ | avatar (radar, fingerprint, or key) and public_score (boolean) |
| POST /api/account/delete/ | Current password |

400 signals invalid input, 401 invalid login, 403 denied requests or CSRF failure, 404 an unknown or inaccessible resource, 409 a stale or incompatible game action, and 429 throttling. Most errors return a detail field. React displays supplied text as text.



Completed game responses include detective_name, detective_title, and leaderboard_rank. The rank is null for guests and players who keep their score private. Titles use the player's best completed score, and public ranks are recalculated when the result is fetched. Leaderboard rows include name, score, rank, and title. Equal scores receive equal ranks.


Profile gender accepts `male`, `female`, or `others` on registration and profile update. Omitted registration gender defaults to `others`; omitted profile-update gender preserves the current selection. Home profile data includes `gender`. Completed games include `character` and `rank_score` (career best for accounts, current score for guests). Leaderboard rows include `character`, alongside cumulative score, title, and competition rank. Gender-based characters become public only with leaderboard opt-in.


`POST /api/account/voice/` requires login and accepts `voice_style` (`style:luna` or `style:orion`) and numeric `voice_rate` (0.75, 0.9, 1, 1.15). Home profile data returns both fields. `GET /api/leaderboard/` now requires login (403 for guests); only opted-in users are listed.


`GET /api/leaderboard/?difficulty=Beginner` selects a league (Beginner default; Intermediate, Professional, and Special Challenge also accepted). Rows include `attempts` (completed cases), `total_time_ms`, `completed_at` (latest included completion), `best_score`, and `difficulty`. Scanner cases are excluded from all league queries. The result identity returns `practice_only` and `leaderboard_difficulty`; practice results always have a null leaderboard rank. Virtual `rank_score` now represents the player's best completed score in that difficulty alone.


Case responses include optional `story_title`. Story selection and normalized question-wording exposure limits (maximum two issuances per owner) use all saved virtual and scanner cases. `story_id`, question answer claims, and solution models remain server-side.

Leaderboard score is the sum of all completed virtual-case scores in that difficulty. Rank compares descending total, ascending completed-case count, then ascending total duration. Exact ties share competition rank; latest included completion time orders tied rows earliest first, with player ID as a stable final fallback. Detective title and result `rank_score` continue to use best single-case performance.

### Gemini-first rounds
Virtual and scanner start endpoints now attempt Gemini structured generation of stories, questions, options, hints, answers and explanations against verified scene evidence and solution references. The prior scanner-only opening/order path is no longer used. Source is `Gemini generated` or `Puzzle engine fallback`. Failed validation or unavailable generation selects engine questions. Complete rounds remain saved in Game.case for resume/review; new starts attempt Gemini again. Answers and explanations remain private until review. Calls run outside database write transactions; player history is checked again before saving, and the observation timer starts after generation. Validation checks answer values and structure, not every semantic implication in generated prose.
