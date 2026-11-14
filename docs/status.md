# Implementation status

| Area | Status |
| --- | --- |
| Virtual worlds | Ten illustrated cases across four difficulty categories. The Midnight Office has bespoke evidence and logic. The other nine use distinct settings and clues with a shared station puzzle family. |
| Puzzle engine | Timed observation, five multiple-choice questions, persistent attempts, server-side scores, and post-game review. Artwork is public gallery art. The server gates the playable exhibit data. |
| Scanner and Gemini | Multipart photo intake, validated Gemini integration, editable detections, configurable themes, per-player story cache, and template fallback. SDK responses are covered with mocks. A live API key is required to verify production model behavior. |
| Nova | Prepared progressive hints and contextual rules, objectives, and progress. Puzzle messages use the active puzzle's scripted hint. Voice playback uses the browser. |
| Accounts and privacy | Django registration, login, logout, password recovery flow, account deletion, avatars, experience, opt-in leaderboard, and scan deletion. Real email transport requires SMTP configuration. Photographs are discarded after processing. |
| Pending from the broader brief | More distinct virtual puzzle sets, additional answer formats, AI-generated freeform puzzles and Nova conversation, optional object re-verification, physical-device and full cross-browser testing, hosted deployment, and a recorded demo. The UI uses custom Tailwind/CSS components in place of shadcn/ui and React Bits. |

Local verification now covers twenty Django tests, plus desktop and emulated-mobile Playwright flows. Next.js production build, ESLint, TypeScript, and Django migration checks passed.



Recent gameplay updates add a fixed hint bar and automatic hint reading with a mute control. Voice settings use one compact row. Luna is a brighter pitch style of an installed female voice. Voice availability and audio quality depend on the device.

New virtual attempts create new station notes and select two visual questions that differ from the previous attempt. The four verified visual questions per scene eventually rotate. Scanner attempts also get fresh ledger values. The Game records retain every full question set, correct answer, explanation, hint, and exhibit for review. Scanner sections are indexed within the saved case payload by confirmed objects, theme, and difficulty. If Gemini generation fails, a matching owner-scoped saved opening can be reused with a fresh deterministic puzzle set.


The scene viewer uses original artwork files with 1�5� zoom, pointer dragging, two-finger pinch, keyboard panning, reset, and an expanded view. Zoom is limited by each original image's pixel detail. The nine contact-sheet scenes retain their original tile resolution.

Completed games render a 1200�760 PNG card with a rank-specific female, male, or neutral detective, the player's title, score, accuracy, correct answers, hints, elapsed time, and public leaderboard position. Sharing uses the device's native file share when supported and otherwise downloads the card. The card excludes room photographs and puzzle answers. Registered players retain a title based on their best completed virtual score within the current difficulty. Scanner results use the current practice score only. Guests get a title from the current case. Titles progress at 201, 401, 601, and 801 points. The five tiers are Unlisted, Clue Hunter, Field Investigator, Senior Detective, and Professional Detective. Public leaderboards are split by difficulty and use score, attempts, total completion time, and best-run time; exact ties share position. Private players and guests are shown as unlisted.


Gender (Male, Female, Others) is available during registration and in account settings. Existing accounts default to Others until changed. All five rank previews, leaderboard portraits, and exported cards use that selection. Luna retains its brighter female style; Orion adds a brighter male style. Both use installed browser voices with a device-voice fallback. Questions and their lettered options read automatically once per new question when voice is enabled, with a manual replay button.


Intermediate now adds two-step station arithmetic, route tracing, and strict midpoint comparisons. Professional and Special Challenge add randomized codes and weights, weighted modular checksums, conditional circular routes, and exclusion/ranking deductions. Virtual professional questions also require mapping verified visual observations to memorized codebooks. Scanner puzzles use the same advanced deductions with their evidence ledger available. Existing saved games remain unchanged; start a new attempt to receive the upgrades.

Voice style and rate are saved to the account. Successful signup and login open a five-second welcome state on Home, then a modal with Luna/Orion, Clear/Slow/Normal/Fast, preview, and Set. Profile settings and in-case voice controls update the saved preference. Leaderboard reads require authentication at the API; guests do not see its listing or share/download controls. Guests may still play and review a result card. Home explains the five score bands and the opt-in, cumulative-score leaderboard with five-second refresh.


Competitive rankings are now separate for Beginner, Intermediate, Professional, and Special Challenge. Only catalog virtual cases count. Ordering: highest summed score, fewest completed cases, then lowest summed elapsed time across completed cases. Exact metric ties share a rank; the player who finished their latest included case earlier appears first within the tie. Unfinished cases do not count. Time is measured server-side in milliseconds from case creation to completion, including observation. Scanner practice is excluded from rank titles for virtual leagues, positions, attempts, and timing; scanner cards are explicitly labeled personal practice.

First-time visitors see a loading state followed by Guest / Sign in / Sign up. Guest mode explains the browser-session cookie and server-side progress, then opens voice setup after five seconds on Home. Guest voice preferences save locally; account preferences save to the profile. Home now explains observation/recall/reasoning practice and the personal-use scanner, and the top navigation has distinct Login and Sign up buttons.


Latest puzzle redesign replaces station arithmetic and numeric ciphers in all newly generated virtual/scanner cases with fictional missing-item investigations. Each dossier has four visitors, objects, rooms, an arrival order, confirmed evidence, and one false witness statement. Beginner uses direct records; Intermediate links objects to rooms and uses elimination; Professional/Special Challenge use indirect constraints reduced to a unique solution. Virtual cases retain two verified image questions plus three narrative deductions. Scanner cases use five dossier questions and keep confirmed photo objects visible. The server retains the solution model privately; it is not serialized into active quiz responses. Existing saved manifests remain unchanged.

Login and signup share the same navigation treatment, entry-choice button styling, and account-panel/form styles.


The Midnight Office now includes a spot-the-change round in new attempts. Players study the original, answer one visual recall question, then inspect a changed image. Two verified missing-object variants alternate across consecutive attempts. The changed image is supplied only for that active question and in completed review, with zoom/pan and an original/changed comparison. Cases still have five questions and the same scoring; older saved cases are unchanged.


Replay diversity now checks all owner-scoped scene attempts, including started attempts. Each fixed change image is issued once; direct visual prompts are also consumed once. When a scene exhausts those fixed prompts, new attempts link image facts to shuffled witness-caption assignments added to the observation dossier. Previously used caption mappings are excluded, with a fresh named review team if a mapping set is exhausted. This prevents the fixed answer loop; the underlying artwork is still a finite set. New case creation is transactional. Account history follows the user across devices; clearing guest cookies loses the association with prior attempts.


Story rotation now spans all owner-scoped virtual and scanner attempts. Six balanced missions rotate without immediate repetition: vanished keepsake, swapped labels, intercepted message, blackout alibi, planted accusation, and misdelivered parcel. Each adds mission-specific evidence and questions to the uniquely solvable person/object/room dossier. A normalized question-wording counter excludes prompts after two issuances, including legacy saved attempts. Fixed image-change variants may each appear at most twice, one per case. The current story title is shown in the case heading. New casts and caption-review teams supply fresh grounded questions when a prompt pool is exhausted; saved cases are unchanged.

### Scene-linked stories and image controls
New virtual rounds rotate nine investigation mechanisms across three scene-specific occasions per mechanism. Openings cite a verified visual fact from the shipped image manifest; fictional investigation zones and events are explicitly distinguished from visible facts. Scene title/occasion selection favors unused combinations, and question exposure remains capped at two per saved player history. The illustrations and template pool remain finite; this is not unlimited generated artwork or unlimited story mechanisms. Existing saved cases retain their original contents.

Scrollbar tracks are hidden while document scrolling, keyboard navigation, and image panning remain available. Expanded scenes expose a visible Close action, Escape dismissal, focus containment/restoration, and background scroll locking.

### Gemini-first rounds
Virtual and scanner start endpoints now attempt Gemini structured generation of stories, questions, options, hints, answers and explanations against verified scene evidence and solution references. The prior scanner-only opening/order path is no longer used. Source is `Gemini generated` or `Puzzle engine fallback`. Failed validation or unavailable generation selects engine questions. Complete rounds remain saved in Game.case for resume/review; new starts attempt Gemini again. Answers and explanations remain private until review. Calls run outside database write transactions; player history is checked again before saving, and the observation timer starts after generation. Validation checks answer values and structure, not every semantic implication in generated prose.

### Reworded-question repetition guard
Gemini questions now retain their original reasoning target in server-side source_question metadata. Exposure checks count both displayed wording and the original target, so paraphrasing cannot reset the two-use cap. Generation excludes exhausted targets and targets from the most recent round. Older Gemini image questions are matched to known image facts through their answer/options where possible. Direct image facts and fixed missing-object variants now appear once per saved player history; later visual rounds use fresh caption evidence. This tracks known targets, not arbitrary semantic similarity, and the artwork and reasoning families are still finite.

### Persistent shared virtual-case archive
RoundArchive stores full virtual-case stories, evidence, questions, answers, hints and explanations without player identifiers. ArchiveFingerprint indexes normalized question text, story title/opening pairs, and source-target/answer/evidence combinations by scene and difficulty. Every new virtual round is checked against all fingerprints, then atomically reserved with unique database constraints before its game is saved. Recently archived cases also guide generation. Duplicate Gemini content falls back to a fresh local candidate; exhausted regeneration returns an explicit fresh-scene message instead of issuing a known duplicate. Shared archive records survive game/account deletion. Scanner content remains only in owner-scoped Game records. Existing virtual rounds can be imported idempotently with `python manage.py backfill_round_archive`. These checks reject exact normalized matches and known-target duplicates, not all possible semantic paraphrases.

### Different dossier systems
Evidence now rotates between packet reconciliation, clock/event reconstruction, credential-gated route selection, and the existing witness logic format. Consecutive rounds do not reuse the same format; legacy cases count as witness logic. Non-witness formats replace the old visitor/inventory/statement sections completely, with separate computed solution models and Gemini target banks that cannot introduce visitor-routing questions. Packet audits scale to returns/off-shelf holds, event logs add clock correction and reordered fragments, and access rules add credential conjunction/exclusion. Scene-reference tags replace repeated caption-author framing for exhausted image facts. Original saved games remain immutable.
