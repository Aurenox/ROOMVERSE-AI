"use client";

import {AnimatePresence, motion, useReducedMotion} from "motion/react";
import {ArrowRight, Check, Clock3, Crosshair, Fingerprint, Lightbulb, Send, Volume2, VolumeX, X} from "lucide-react";
import {useCallback, useEffect, useRef, useState} from "react";
import {readingVoice} from "../lib/speech";
import {SceneViewer} from "./scene-viewer";
import {ResultCard} from "./result-card";
import {api, Exhibit, Game} from "../lib/api";

export function Evidence({items}: {items: Exhibit[]}) {
  return <ul className="evidence">{items.map(([label,value]) => <li key={label}><strong>{label}</strong><span>{value}</span></li>)}</ul>;
}

export function Investigation({game, change, back, replay, signedIn, signIn}: {
  signedIn: boolean; signIn: () => void; game: Game; change: (game: Game) => void; back: () => void; replay: () => void;
}) {
  const [choice,setChoice] = useState("");
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const [feedback,setFeedback] = useState<boolean>();
  const [message,setMessage] = useState("");
  const [reply,setReply] = useState("");
  const [voice,setVoice] = useState(true);
  const [rate,setRate] = useState(0.9);
  const speechRequest = useRef(0);
  const stopSpeech = useCallback(() => {speechRequest.current++;window.speechSynthesis?.cancel();}, []);
  const [voiceId,setVoiceId] = useState("style:luna");
  const [speechError,setSpeechError] = useState("");
  const [speechSupported,setSpeechSupported] = useState(true);
  useEffect(() => {
    const sync = () => {
      setSpeechSupported("speechSynthesis" in window);
      if (!("speechSynthesis" in window)) return;

      const saved = localStorage.getItem("roomverse-voice") || "";
      setVoiceId(saved === "style:orion" ? saved : "style:luna");
      const savedRate = Number(localStorage.getItem("roomverse-rate") || "0.9");
      setRate([0.75,0.9,1,1.15].includes(savedRate) ? savedRate : 0.9);
    };
    const initial = window.setTimeout(sync, 0);
    const retry = window.setTimeout(sync, 1500);
    window.speechSynthesis?.addEventListener("voiceschanged", sync);
    window.addEventListener("focus", sync);
    return () => {
      window.clearTimeout(initial);
      window.clearTimeout(retry);
      window.speechSynthesis?.removeEventListener("voiceschanged", sync);
      window.removeEventListener("focus", sync);
    };
  }, []);
  const [review,setReview] = useState(false);
  const [seconds,setSeconds] = useState(0);
  const reduced = useReducedMotion();

  useEffect(() => {
    if (game.phase !== "observe" || !game.deadline) return;
    const duration = Date.parse(game.deadline) - Date.parse(game.server_time);
    const began = performance.now();
    let fetching = false;
    let disposed = false;
    const tick = async () => {
      const left = Math.max(0, Math.ceil((duration - (performance.now() - began)) / 1000));
      setSeconds(left);
      if (!left && !fetching) {
        fetching = true;
        try {
          const current = await api<Game>(`games/${game.game_id}/`);
          if (!disposed) change(current);
        } catch {
          if (!disposed) setError("Connection lost. Reconnecting to the case server…");
        } finally {fetching = false;}
      }
    };
    void tick();
    const timer = window.setInterval(tick, 750);
    return () => {disposed = true; window.clearInterval(timer);};
  }, [game.deadline, game.game_id, game.phase, game.server_time, change]);

  useEffect(() => () => stopSpeech(), [stopSpeech]);

  async function task(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {await action();} catch (error) {setError((error as Error).message);}
    finally {setBusy(false);}
  }

  const speak = useCallback(async (text: string, preview = false) => {
    if ((!voice && !preview) || !("speechSynthesis" in window)) return;
    setSpeechError("");
    const utterance = new SpeechSynthesisUtterance(text);
    const request=++speechRequest.current;
    const selected=await readingVoice(voiceId);
    if(request!==speechRequest.current)return;
    if(!selected){setSpeechError("The selected voice is not available yet on this device. Try Preview again or choose another voice.");return;}
    utterance.pitch = voiceId === "style:luna" ? 1.15 : 1.12;
    utterance.voice=selected;utterance.lang=selected.lang;
    utterance.onerror = event => {
      if (!["canceled","interrupted"].includes(event.error)) setSpeechError("Tap Read question or Preview to start voice playback.");
    };
    utterance.rate = rate;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  }, [voice, voiceId, rate]);

  const spokenQuestion = useRef("");
  const questionText = game.question ? `${game.question.question}. ${game.question.options.map((option,index) => `Option ${String.fromCharCode(65+index)}. ${option}.`).join(" ")}` : "";
  useEffect(() => {
    if (game.phase !== "quiz" || !questionText || !voice || !speechSupported) return;
    const key = `${game.game_id}:${game.position}`;
    let timer: number;
    const read = () => {
      if (document.hidden || spokenQuestion.current === key) return;
      timer = window.setTimeout(() => {
        if (document.hidden || spokenQuestion.current === key) return;
        spokenQuestion.current = key;
        speak(questionText);
      }, 350);
    };
    read();
    document.addEventListener("visibilitychange", read);
    return () => {window.clearTimeout(timer); document.removeEventListener("visibilitychange", read);};
  }, [game.game_id, game.position, game.phase, questionText, voice, speechSupported, speak]);

  function nova(kind: string) {
    return task(async () => {
      const result = await api<{game: Game; message: string}>(`games/${game.game_id}/nova/`, "POST",
        {kind, message, position: game.position});
      change(result.game);
      setReply(result.message);
      setMessage("");
      speak(result.message);
    });
  }

  return <section className="tool wrap" aria-labelledby="case-title">
    <button className="text-button" onClick={back}>← Back to case files</button>
    <div className="case-heading">
      <div><span className="eyebrow"><Fingerprint size={15}/> {game.source}</span><h1 id="case-title">{game.title}</h1>{game.story_title && <p className="story-tag"><span>THIS CASE’S STORY</span>{game.story_title}</p>}<p className="lede">{game.intro}</p><p className="objective"><Crosshair size={16}/>{game.objective}</p></div>
      <span className="tag static">{game.difficulty}</span>
    </div>
    {error && <p role="alert" className="error">{error}</p>}
    <section className="voice-bar" aria-label="Voice and reading settings">
      <button className="icon-button" aria-label={voice ? "Mute voice" : "Enable voice"} aria-pressed={voice} onClick={() => {setVoice(!voice); stopSpeech();}}>{voice ? <Volume2 size={17}/> : <VolumeX size={17}/>}</button>
      <label><span className="sr-only">Character voice</span><select disabled={!speechSupported} value={voiceId} onChange={e => {setVoiceId(e.target.value); localStorage.setItem("roomverse-voice",e.target.value); if (signedIn) void api("account/voice/","POST",{voice_style:e.target.value,voice_rate:rate}).catch(() => setSpeechError("Voice changed for this session; profile saving failed.")); stopSpeech();}}>
        <option value="style:luna">Luna · brighter female voice style</option>
        <option value="style:orion">Orion · brighter male voice style</option>
      </select></label>
      <label><span className="sr-only">Reading speed</span><select value={rate} onChange={e => {const next = Number(e.target.value);setRate(next);localStorage.setItem("roomverse-rate",String(next));if (signedIn) void api("account/voice/","POST",{voice_style:voiceId,voice_rate:next}).catch(() => setSpeechError("Speed changed for this session; profile saving failed."));}}><option value={0.75}>Slow</option><option value={0.9}>Clear</option><option value={1}>Normal</option><option value={1.15}>Fast</option></select></label>
      <button disabled={!speechSupported} className="text-button" onClick={() => speak("Hello detective. Look closely and connect the clues.",true)}>Preview</button>
      <button className="text-button" onClick={() => window.speechSynthesis?.cancel()}>Stop</button>
    </section>
    <p className="voice-caption muted">Questions and options read automatically when voice is on. Voice styles use the voices installed on your device.</p>
    {speechError && <p role="status" className="error">{speechError}</p>}
    {!speechSupported && <p role="status">Voice playback is unavailable in this browser.</p>}
    <div className="investigation-grid">
      <div className="panel">
        <AnimatePresence mode="wait">
          <motion.div key={`${game.phase}-${game.position}`} initial={reduced ? false : {opacity:0,y:8}} animate={{opacity:1,y:0}} exit={reduced ? undefined : {opacity:0}} transition={{duration:.16}}>
          {game.phase === "observe" && (seconds > 0 ? <>
            <div className="split"><h2>Observe the scene</h2><span className="timer"><Clock3 size={18}/> {Math.floor(seconds/60)}:{String(seconds % 60).padStart(2,"0")}</span></div>
            <p className="muted">Study the room image and the notes. Both will be tested after the timer expires.</p>
            {game.has_change_round && <p className="notice"><strong>Spot the change</strong> · Memorize the objects. A later question shows this room with one object removed.</p>}
            <SceneViewer scene={game.id} title={game.title}/>
            {game.exhibits && <Evidence items={game.exhibits}/>}
          </> : <p role="status">Closing the evidence archive…</p>)}
          {game.phase === "quiz" && game.question && <>
            <div className="split"><span className="eyebrow">QUESTION {game.position+1} / 5</span><span className="score">{game.score} pts</span></div>
            <progress aria-label="Questions completed" max={5} value={game.position}/>
            <h2>{game.question.question}</h2>
            {game.question.changed_image && <section className="change-round" aria-label="Spot the change"><span className="eyebrow">CHANGED SCENE · TRUST YOUR MEMORY</span><p className="muted">One object has disappeared. Compare this scene with the original you studied. You can zoom and pan.</p><SceneViewer key={game.question.changed_image} scene={game.id} title="Changed room for the memory question" imageSource={game.question.changed_image}/></section>}
            <button type="button" className="text-button read-question" disabled={!speechSupported} onClick={() => speak(questionText,true)}><Volume2 size={16}/> Read question &amp; options</button>
            {game.question.evidence && <details open><summary>Fictional case dossier</summary><Evidence items={game.question.evidence}/></details>}
            <form onSubmit={e => {e.preventDefault(); void task(async () => {
              const result = await api<{game: Game; correct: boolean}>(`games/${game.game_id}/answer/`,"POST",{answer:choice,position:game.position});
              stopSpeech(); setFeedback(result.correct); setChoice(""); setReply(""); change(result.game);
            });}}>
              <fieldset className="answer-options"><legend className="sr-only">Select your answer</legend>{game.question.options.map((option,index) =>
                <label className={option === choice ? "chosen" : ""} key={option}><input type="radio" name="answer" checked={option === choice} onChange={() => setChoice(option)}/><span>{String.fromCharCode(65+index)}</span>{option}</label>)}</fieldset>
              <button className="button primary" disabled={!choice || busy}>Submit answer <ArrowRight size={17}/></button>
            </form>
            {feedback !== undefined && <p className={feedback ? "good" : "error"}>{feedback ? <Check size={16}/> : <X size={16}/>} Previous answer {feedback ? "correct" : "incorrect"}</p>}
          </>}
          {game.phase === "complete" && <>
            <ResultCard game={game} signedIn={signedIn} signIn={signIn}/><span className="eyebrow"><Check size={16}/> CASE CLOSED</span><h2>{game.score} <small>/ 1,000 pts</small></h2>
            <p>{game.completion}</p><p className="muted">{game.correct}/5 correct · {(game.correct ?? 0)*20}% accuracy · {game.hints_used} hints · {game.elapsed}s</p>
            <ol className="results">{game.review?.map((item,index) => <li key={index}><strong>{item.correct ? "Correct" : "Incorrect"} · {item.question}</strong>
              <p>Your answer: {item.submitted}. Solution: {item.answer}.</p><p className="muted">{item.explanation}</p>{item.changed_image && <details className="change-comparison"><summary>Compare original and changed scene</summary><div className="comparison-grid"><section><h3>Original</h3><SceneViewer scene={game.id} title="Original room"/></section><section><h3>Changed</h3><SceneViewer scene={game.id} title="Changed room" imageSource={item.changed_image}/></section></div></details>}</li>)}</ol>
            <div className="actions">
              <button className="button primary" onClick={() => setReview(!review)}>{review ? "Hide scene" : "Review scene"}</button>
              <button className="button outline" onClick={replay}>{game.id === "scanner" ? "Scan another room" : "Play again"}</button>
              <button className="text-button" onClick={back}>Choose next adventure</button>
            </div>
            {review && <>
              {game.id !== "scanner" && <SceneViewer scene={game.id} title={game.title}/>}
              {game.exhibits && <Evidence items={game.exhibits}/>}
            </>}
          </>}
          </motion.div>
        </AnimatePresence>
      </div>
      <aside className="panel nova" aria-label="Detective Nova">
        <div className="split"><h2><Fingerprint size={20}/> Detective Nova</h2><button className="icon-button" aria-label={voice ? "Mute Nova" : "Read Nova replies aloud"} aria-pressed={voice} onClick={() => {setVoice(!voice); stopSpeech();}}>{voice ? <Volume2 size={19}/> : <VolumeX size={19}/>}</button></div>
        <p className="muted">Hints and puzzle assistance share an allowance. Each use costs 25 points.</p>
        <div className="nova-reply" aria-live="polite">{reply || game.hints?.at(-1) || (game.phase === "complete" ? "Good work, detective. Review the evidence whenever you’re ready." : "I’ll help you connect the evidence.")}</div>
        <div className="actions"><button className="text-button" disabled={busy} onClick={() => nova("rules")}>Rules</button><button className="text-button" disabled={busy} onClick={() => nova("objective")}>Objective</button><button className="text-button" disabled={busy} onClick={() => nova("progress")}>Progress</button></div>
        {game.phase === "quiz" && <>
        <form className="ask" onSubmit={e => {e.preventDefault(); void nova("assist");}}><input aria-label="Ask Nova for puzzle assistance" placeholder="Ask for puzzle help…" maxLength={500} value={message} onChange={e => setMessage(e.target.value)}/><button className="icon-button" aria-label="Send hint request" disabled={busy || !message.trim() || !game.hints_remaining}><Send size={17}/></button></form></>}
      </aside>
    </div>
    {game.phase === "quiz" && <div className="hint-dock">
      <div className="split"><button className="button primary" disabled={busy || !game.hints_remaining} onClick={() => nova("hint")}><Lightbulb size={17}/> Reveal hint · {game.hints_remaining} left</button><span>−25 pts</span>
      <button className="icon-button" aria-label={voice ? "Mute hint reading" : "Enable hint reading"} aria-pressed={voice} onClick={() => {setVoice(!voice); stopSpeech();}}>{voice ? <Volume2 size={17}/> : <VolumeX size={17}/>}</button></div>
      {Boolean(reply || game.hints?.length) && <p aria-live="polite">{reply || game.hints?.at(-1)}</p>}
    </div>}
  </section>;
}
