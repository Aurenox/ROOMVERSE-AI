"use client";

import {useEffect, useRef, useState} from "react";
import {readingVoice} from "../lib/speech";
import {api, Home} from "../lib/api";

export function rememberVoice(style: string, rate: number) {
  localStorage.setItem("roomverse-voice", style);
  localStorage.setItem("roomverse-rate", String(rate));
}

export function VoiceSettings({profile, onSaved, welcome = false}: {
  profile?: Home["profile"]; onSaved: () => Promise<void> | void; welcome?: boolean;
}) {
  const [style,setStyle] = useState(profile?.voice_style || (typeof window !== "undefined" ? localStorage.getItem("roomverse-voice") : null) || "style:luna");
  const [rate,setRate] = useState(profile?.voice_rate || (typeof window !== "undefined" ? Number(localStorage.getItem("roomverse-rate")) : 0) || 0.9);
  const [notice,setNotice] = useState("");
  const [busy,setBusy] = useState(false);
  const speechRequest=useRef(0);
  function stopSpeech(){speechRequest.current++;window.speechSynthesis?.cancel();}
  useEffect(() => () => {speechRequest.current++;window.speechSynthesis?.cancel();}, []);

  async function preview() {
    if (!("speechSynthesis" in window)) {setNotice("Voice playback is unavailable in this browser."); return;}
    const request=++speechRequest.current;
    const selected=await readingVoice(style);
    if(request!==speechRequest.current)return;
    if(!selected){setNotice("The selected voice is unavailable on this device. Try again after voices load or choose another voice.");return;}
    setNotice("");
    const speech = new SpeechSynthesisUtterance("Hello detective. Look closely, remember the evidence, and connect the clues. Your next investigation awaits.");
    if (selected) {speech.voice = selected; speech.lang = selected.lang;}
    speech.pitch = style === "style:luna" ? 1.15 : 1.12;
    speech.rate = rate;
    speech.onerror = event => {if (!["canceled","interrupted"].includes(event.error)) setNotice("This voice could not play. Try Preview again.");};
    window.speechSynthesis.cancel(); window.speechSynthesis.speak(speech);
  }

  return <form className="stack" onSubmit={async event => {
    event.preventDefault(); setBusy(true); setNotice("");
    try {
      if (profile) await api("account/voice/","POST",{voice_style:style,voice_rate:rate});
      rememberVoice(style,rate); stopSpeech();
      await onSaved(); setNotice("Voice preferences saved.");
    } catch (error) {setNotice((error as Error).message);}
    finally {setBusy(false);}
  }}>
    <p className="muted">Browser text-to-speech · Luna and Orion are presets using voices installed on your device. Gemini does not generate this audio.</p>
    <label>Website voice<select value={style} onChange={e => {setStyle(e.target.value);stopSpeech();}}>
      <option value="style:luna">Female · Luna brighter style</option><option value="style:orion">Male · Orion brighter style</option>
    </select></label>
    <label>Voice speed<select value={rate} onChange={e => {setRate(Number(e.target.value));stopSpeech();}}>
      <option value={0.9}>Clear</option><option value={0.75}>Slow</option><option value={1}>Normal</option><option value={1.15}>Fast</option>
    </select></label>
    <p className="muted">Preview before setting. Your choice applies to questions, options, and hints. Voice sound depends on your device.</p>
    <div className="actions"><button className="button outline" type="button" onClick={preview}>Preview voice</button><button className="button primary" disabled={busy}>{busy ? "Saving…" : welcome ? "Set voice & open home" : "Save voice"}</button></div>
    {notice && <p role="status">{notice}</p>}
  </form>;
}

export function WelcomeVoice({profile,onDone}: {profile?:Home["profile"];onDone:()=>Promise<void>}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [ready,setReady] = useState(false);
  useEffect(() => {
    dialog.current?.showModal();
    const timer = window.setTimeout(() => setReady(true),5000);
    return () => window.clearTimeout(timer);
  }, []);
  return <dialog ref={dialog} className="welcome-dialog" aria-labelledby="welcome-title" onCancel={event => event.preventDefault()}>
    <span className="eyebrow">WELCOME, DETECTIVE</span>
    <h2 id="welcome-title">{ready ? "Choose your reading voice" : "Preparing your headquarters…"}</h2>
    {ready ? <VoiceSettings profile={profile} onSaved={onDone} welcome/> : <p role="status">{profile ? `You’re signed in, ${profile.username}.` : "You’re playing as a guest on this browser."} Voice setup opens in five seconds.</p>}
  </dialog>;
}


export function EntryChoice({guest,signIn,signUp}: {guest:()=>void;signIn:()=>void;signUp:()=>void}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {dialog.current?.showModal();}, []);
  return <dialog ref={dialog} className="welcome-dialog" aria-labelledby="entry-title" onCancel={event => event.preventDefault()}>
    <span className="eyebrow">YOUR INVESTIGATION STARTS HERE</span><h2 id="entry-title">How would you like to play?</h2>
    <p>Play as a guest now, or sign in to keep your detective record across devices.</p>
    <div className="notice guest-notice"><strong>Guest progress is temporary</strong><p>A temporary session cookie links this browser to your saved progress on our server. It is not synced to other devices. Clearing cookies or letting the session expire can remove your access. Sign in to access your progress from another device.</p></div>
    <div className="actions"><button className="button primary" onClick={guest}>Continue as guest</button><button className="button outline" onClick={signIn}>Sign in</button><button className="button outline" onClick={signUp}>Sign up</button></div>
  </dialog>;
}
