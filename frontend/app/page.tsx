"use client";

import {
  ArrowUp, Heart, ArrowRight, ArrowUpRight, Camera, ChevronDown, Clock3, Fingerprint,
  FolderOpen, Menu, Radar, ScanLine, Search, ShieldCheck, Trophy, UserRound, X,
} from "lucide-react";
import {useCallback, useEffect, useState} from "react";
import {Investigation} from "../components/investigation";
import {Scanner} from "../components/scanner";
import {EntryChoice, WelcomeVoice, rememberVoice} from "../components/voice-settings";
import {ranks, portraitStyle, avatarStyle} from "../lib/ranks";
import {Leaderboard} from "../components/leaderboard";
import {Profile} from "../components/profile";
import {api, Game, Home, Scene} from "../lib/api";

type View = "home" | "scanner" | "profile" | "leaderboard" | "game";
const filters = ["All cases", "Beginner", "Intermediate", "Professional", "Special Challenge"];

function CaseCard({scene, index, start, busy}: {scene: Scene; index: number; start: () => void; busy: boolean}) {
  return <article className="case-card">
    <div className={`case-image art-${scene.id}`}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={`/art/${scene.id}.webp`} alt="" loading="lazy"/>
      <span className={`tag level-${scene.difficulty.split(" ")[0].toLowerCase()}`}>{scene.difficulty}</span>
      <span className="file-id">RV / {String(index + 1).padStart(2,"0")}</span>
    </div>
    <div className="case-body"><div><h3>{scene.title}</h3><p>{scene.location}</p>{scene.id === "midnight" && <span className="change-badge">NEW · Spot the change</span>}</div>
      <div className="card-foot"><span><Clock3 size={15}/> {scene.duration}</span><button className="icon-button" aria-label={`Open ${scene.title}`} onClick={start} disabled={busy}><ArrowUpRight size={19}/></button></div>
    </div>
  </article>;
}

export default function Roomverse() {
  const [home,setHome] = useState<Home>();
  const [view,setView] = useState<View>("home");
  const [game,setGame] = useState<Game>();
  const [filter,setFilter] = useState(filters[0]);
  const [all,setAll] = useState(false);
  const [menu,setMenu] = useState(false);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const [entry,setEntry] = useState(false);
  const [authRevision,setAuthRevision] = useState(0);
  const [authMode,setAuthMode] = useState("login");
  const [welcome,setWelcome] = useState(false);
  const [reset,setReset] = useState("");

  const refresh = useCallback(async () => {
    try {const next = await api<Home>(); setHome(next); if (next.profile) rememberVoice(next.profile.voice_style,next.profile.voice_rate); return next;}
    catch (error) {setError((error as Error).message);}
  }, []);

  const navigate = useCallback((next: View, section?: string) => {
    setView(next); setMenu(false); setError("");
    if (next !== "game") sessionStorage.removeItem("roomverse-open-game");
    if (next !== "home") window.scrollTo(0,0);
    else requestAnimationFrame(() => section ? document.getElementById(section)?.scrollIntoView({behavior:"instant"}) : window.scrollTo(0,0));
  }, []);

  const updateGame = useCallback((next: Game) => {
    setGame(next);
    if (next.phase === "complete") void refresh();
  }, [refresh]);

  const openGame = useCallback((next: Game) => {
    updateGame(next);
    sessionStorage.setItem("roomverse-open-game",next.game_id);
    navigate("game");
  }, [navigate, updateGame]);

  useEffect(() => {
    let active = true;
    async function restore() {
      const next = await refresh();
      if (!active) return;
      const token = new URLSearchParams(window.location.search).get("reset");
      if (token) {
        setReset(token); navigate("profile"); return;
      }
      if (next && !next.profile && !sessionStorage.getItem("roomverse-entry")) {setEntry(true); return;}
      const saved = sessionStorage.getItem("roomverse-open-game");
      if (saved) {
        try {
          const current = await api<Game>(`games/${saved}/`);
          if (active) openGame(current);
        } catch {sessionStorage.removeItem("roomverse-open-game");}
      }
    }
    void restore();
    return () => {active = false;};
  }, [navigate, openGame, refresh]);

  function openAuth(mode: string) {setEntry(false);setAuthMode(mode);setAuthRevision(value => value + 1);navigate("profile");}

  async function play(scene?: string, id?: string) {
    setBusy(true);
    setError("");
    try {
      const next = id ? await api<Game>(`games/${id}/`) : await api<Game>("start/","POST",{scene});
      openGame(next);
      void refresh();
    } catch (error) {setError((error as Error).message);}
    finally {setBusy(false);}
  }

  const matching = home?.scenes.filter(scene => filter === filters[0] || scene.difficulty === filter) || [];
  const scenes = all || filter !== filters[0] ? matching : matching.slice(0,3);
  const resume = home?.history.find(item => item.phase !== "complete");

  if (!home && !error) return <main className="entry-loading" role="status"><Radar size={36}/><h1>Opening the case archive…</h1><p>Preparing your guest and sign-in options.</p></main>;

  return <>
    <a className="skip" href="#main">Skip to content</a>
    <header className="site-header">
      <div className="nav wrap">
        <button className="brand" onClick={() => navigate("home")} aria-label="Roomverse AI home"><span className="brand-mark"><Radar size={23}/></span><span>ROOMVERSE<span className="brand-ai"> AI</span></span></button>
        <nav aria-label="Main navigation" className={menu ? "nav-links expanded" : "nav-links"}>
          <button className={view === "home" || view === "game" ? "active" : ""} onClick={() => navigate("home","cases")}>Case Files</button>
          <button className={view === "scanner" ? "active" : ""} onClick={() => navigate("scanner")}>Room Scanner</button>
          <button className={view === "leaderboard" ? "active" : ""} onClick={() => navigate("leaderboard")}>Leaderboard</button>
        </nav>
        <div className="nav-right">{!home?.profile && <><button className="text-button auth-button" onClick={() => openAuth("login")}>Login</button><button className="text-button auth-button" onClick={() => openAuth("register")}>Sign up</button></>}<button className="button outline profile-link" aria-label="Detective profile" onClick={() => navigate("profile")}><>{home?.profile ? <span className="nav-avatar" style={avatarStyle(home.profile.avatar,home.profile.gender)}/> : <UserRound size={16}/>}</><span>{home?.profile?.username || "Detective Profile"}</span></button>
          <button className="icon-button menu-toggle" aria-label={menu ? "Close menu" : "Open menu"} aria-expanded={menu} onClick={() => setMenu(!menu)}>{menu ? <X/> : <Menu/>}</button></div>
      </div>
    </header>
    <main id="main">
      {busy && <div className="wrap notice" role="status">Preparing your investigation with Gemini. A puzzle-engine round is ready if generation is unavailable.</div>}
      {error && <div className="wrap global-error" role="alert"><p className="error">{error}</p>{!home && <button className="button outline" onClick={refresh}>Retry connection</button>}</div>}
      {view === "home" && <>
        <section className="hero wrap" aria-labelledby="hero-title">
          <div className="hero-image" aria-hidden="true"/>
          <div className="hero-copy">
            <div className="eyebrow hero-eyebrow"><span className="live-dot"/> THE INVESTIGATION BEGINS</div>
            <h1 id="hero-title">Your reality<br/>is hiding<br/><em>something.</em></h1>
            <p>Every object has a story. Every room hides a mystery. Step inside and see what everyone else missed.</p>
            <div className="actions hero-actions">
              <button className="button primary" onClick={() => navigate("home","cases")}><Fingerprint size={19}/> Start investigation <ArrowRight size={17}/></button>
              <button className="button outline" onClick={() => navigate("scanner")}><ScanLine size={19}/> Scan my room</button>
            </div>
          </div>
          <div className="hero-caption"><span/><span>LOCATION</span><strong>THE MIDNIGHT OFFICE</strong></div>
        </section>
        <section className="wrap catalog" id="cases" aria-labelledby="catalog-title">
          <div className="section-top"><div>
            <span className="eyebrow"><FolderOpen size={16}/> VIRTUAL MYSTERY WORLDS</span><h2 id="catalog-title">Open a case file.</h2>
            <p className="muted">Pick a scene. Gemini writes fresh scene-linked stories and questions from the photograph facts and case records. If Gemini is unavailable or its answers fail validation, our puzzle engine keeps your round playable.</p><p className="replay-note">A question can appear at most twice in your saved history. Some Midnight Office rounds ask you to find one missing object in a changed image.</p>
          </div>{resume && <button className="button outline" disabled={busy} onClick={() => play(undefined,resume.id)}>Continue adventure <ArrowRight size={17}/></button>}</div>
          <div className="difficulty-guide"><p><strong>Beginner</strong> Spot visual details, find missing items, and check simple witness records.</p><p><strong>Intermediate</strong> Link people, objects, and rooms; expose contradictions and reconstruct events.</p><p><strong>Professional</strong> Very hard: solve indirect clues, eliminate false leads, and reconstruct a unique chain of events.</p></div>
          <div className="filters" aria-label="Filter cases by difficulty">{filters.map(item => <button aria-pressed={filter === item} key={item} onClick={() => setFilter(item)}>{item}</button>)}</div>
          {!home && !error && <p role="status">Connecting to the case archive…</p>}
          <div className="case-grid">{scenes.map(scene => <CaseCard key={scene.id} scene={scene} index={home!.scenes.indexOf(scene)} start={() => play(scene.id)} busy={busy}/>)}</div>
          {home && filter === filters[0] && <button className="button outline archive-button" onClick={() => setAll(!all)}>{all ? "Show featured files" : "View all case files"} <ChevronDown size={16}/></button>}
        </section>
        <section className="wrap catalog" aria-labelledby="ranks-title"><span className="eyebrow"><Trophy size={17}/> YOUR DETECTIVE JOURNEY</span><h2 id="ranks-title">Every clue builds your rank.</h2>
          <p className="lede">Earn up to 1,000 points per case. Your best virtual-case score sets your title separately in each difficulty. Scanner sessions are personal practice.</p>
          <div className="rank-gallery home-ranks">{ranks.map((rank,index) => <div className="rank-tile" key={rank.title} style={{borderColor:rank.color}}><span className="rank-art" aria-hidden="true" style={portraitStyle(index*200+1,home?.profile?.gender)}/><strong style={{color:rank.color}}>{rank.title}</strong><span>{index === 0 ? "1–200 (also 0)" : rank.range} points</span></div>)}</div>
          <div className="panel leaderboard-intro"><h3>Join the agency leaderboard</h3><p>Sign in to view live rankings, share results, and download your detective card. Enable public scores in your profile to join the leaderboard. Beginner, Intermediate, and Professional have separate leagues. Rankings refresh every five seconds. Every completed virtual case adds to your difficulty total. Equal totals favor fewer completed cases, then shorter total duration. Exact ties share rank; the earlier final completion is displayed first. Scanner sessions never count. Each hint costs 25 points.</p><button className="button outline" onClick={() => navigate("leaderboard")}>{home?.profile ? "Open leaderboard" : "Sign in to join"}</button></div>
        </section>
        <section className="wrap catalog" aria-labelledby="benefits-title"><span className="eyebrow">PRACTICE WITH PURPOSE</span><h2 id="benefits-title">Train how you notice and reason.</h2><div className="instruction-grid"><div><Search/><h3>Notice visual details</h3><p>Practice observing objects, colors, and positions, then recalling what you saw.</p></div><div><Fingerprint/><h3>Connect evidence</h3><p>Combine image clues with notes. Work from simple recall to multi-step deductions at your own pace.</p></div><div><Camera/><h3>Use your real world</h3><p>Scanner practice turns familiar surroundings into exercises. Review explanations, learn from mistakes, and retry without leaderboard pressure.</p></div></div><p className="muted">Designed for observation, recall, and reasoning practice. Improvement varies; scores are game results, not a measure of intelligence or memory capacity.</p></section>
        <section className="wrap how" id="how" aria-labelledby="how-title">
          <div className="scanner-callout"><div><span className="eyebrow"><Camera size={17}/> REAL-WORLD SCANNER</span><h2>Make your room the crime scene.</h2><p className="muted">Turn objects from your photo into a personalized mystery. You choose which objects go into the case.</p></div><button className="button primary" onClick={() => navigate("scanner")}>Open room scanner <ArrowRight size={17}/></button></div>
          <h2 id="how-title">How it works</h2>
          <div className="instruction-grid">
            <div><Camera/><h3>Choose a scene</h3><p>Open a virtual case or take a photo of your surroundings.</p></div>
            <div><Search/><h3>Study the evidence</h3><p>Observe a timed scene or confirm the objects for your own case.</p></div>
            <div><ShieldCheck/><h3>Close the case</h3><p>Solve five linked questions and review the clues with Nova.</p></div>
          </div>
        </section>
      </>}
      {view === "scanner" && (home ? <Scanner home={home} play={next => {openGame(next); void refresh();}}/> : <p className="wrap" role="status">Connecting to the scanner…</p>)}
      {view === "leaderboard" && home && <Leaderboard home={home} signIn={()=>openAuth("login")} profile={()=>navigate("profile")} play={()=>navigate("home","cases")}/>}
      {view === "profile" && home && <Profile key={`${authMode}-${authRevision}`} initialMode={authMode} authenticated={() => {sessionStorage.setItem("roomverse-entry","member");navigate("home");setWelcome(true);}} home={home} refresh={async () => {await refresh();}} resume={id => play(undefined,id)} reset={reset} clearReset={() => {setReset(""); history.replaceState(null,"",location.pathname);}}/>}
      {view === "game" && game && <Investigation signedIn={Boolean(home?.profile)} signIn={() => openAuth("login")} key={game.game_id} game={game} change={updateGame} back={() => navigate("home","cases")} replay={() => game.id === "scanner" ? navigate("scanner") : play(game.id)}/>}
    </main>
    {entry && <EntryChoice guest={() => {sessionStorage.setItem("roomverse-entry","guest");setEntry(false);navigate("home");setWelcome(true);}} signIn={() => openAuth("login")} signUp={() => openAuth("register")}/>}
    {welcome && home && <WelcomeVoice profile={home.profile} onDone={async () => {await refresh();setWelcome(false);navigate("home");}}/>}
    <footer className="footer"><div className="wrap footer-inner"><div className="footer-credit"><strong>© ROOMVERSE AI @2026</strong><span>Built by Saurav B <Heart size={16} aria-label="with love"/></span></div><button className="back-to-top" aria-label="Back to top" onClick={() => window.scrollTo({top:0,behavior:window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth"})}><ArrowUp size={22}/></button></div></footer>
  </>;
}
