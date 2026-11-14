"use client";

import { Camera, ImageUp, Plus, ScanLine, Trash2, X, ArrowRight } from "lucide-react";
import {useEffect, useState} from "react";
import {CameraCapture} from "./camera-capture";
import {PhotoPrivacy} from "./photo-privacy";
import {api, Game, Home, Scan} from "../lib/api";

export function Scanner({home, play}: {home: Home; play: (game: Game) => void}) {
  const [camera,setCamera] = useState(false);
  const [editing,setEditing] = useState(false);
  const [file,setFile] = useState<File>();
  const [preview,setPreview] = useState("");
  const [consent,setConsent] = useState(false);
  const [scan,setScan] = useState<Scan>();
  const [objects,setObjects] = useState<string[]>([]);
  const [theme,setTheme] = useState(home.themes[0]);
  const [difficulty,setDifficulty] = useState(home.difficulty[0]);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  useEffect(() => {
    if (preview) return () => URL.revokeObjectURL(preview);
  }, [preview]);

  function choose(photo?: File) {
    if (!photo) return;
    setCamera(false); setEditing(false); setConsent(false);
    if (!["image/jpeg","image/png","image/webp"].includes(photo.type) || photo.size > 5*1024*1024) {setFile(undefined);setPreview("");setError("Choose a JPEG, PNG, or WebP photo up to 5 MB.");return;}
    setFile(photo);
    setPreview(URL.createObjectURL(photo));
    setConsent(false);
    setError("");
  }

  async function work(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return <section className="tool wrap" aria-labelledby="scanner-title">
    <span className="eyebrow"><ScanLine size={15}/> REAL-WORLD SCANNER</span>
    <h1 id="scanner-title">Every room hides a case.</h1>
    <p className="lede">Personal practice for the real world. Photograph your surroundings, confirm the objects, and train observation and reasoning.</p>
    <div className="notice"><strong>Self-improvement · never ranked</strong><p>Scanner scores, attempts, and time never enter any leaderboard. Choose Beginner for recall, Intermediate for linked deductions, or Professional for indirect evidence and logic mysteries. Gemini identifies objects and writes the story, questions, options, hints, and answers. The server checks answers against the case evidence. If generation is unavailable or fails validation, the puzzle engine supplies a playable round.</p></div>
    {!home.ai_configured && <p className="notice">Automatic analysis is unavailable. You can enter objects and play a prepared mystery.</p>}
    <div className="panel scanner-panel">
      {error && <p role="alert" className="error">{error}</p>}
      {!scan ? <>
        <div className="notice privacy-notice"><strong>Photograph objects, not personal information</strong><p>Keep yourself, other people, private photos, IDs, passwords, phone numbers, email addresses, and readable screens out of the frame. Review your photo and cover private details before sending it.</p></div>
        {camera && <CameraCapture capture={choose} close={() => setCamera(false)}/>}
        {editing && file && <PhotoPrivacy file={file} apply={choose} close={() => setEditing(false)}/>}
        <div className="upload-zone">
          {file && preview ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={preview} alt="Photograph selected for analysis" />
          ) : <><ImageUp size={40}/><strong>Choose a room photograph</strong><span>JPEG, PNG or WebP · Up to 5 MB</span></>}
          <div className="actions">
            <label className="button outline file"><ImageUp size={17}/>{file ? "Replace photo" : "Upload photo"}<input aria-label="Upload photo" type="file" accept="image/jpeg,image/png,image/webp" disabled={busy || camera || editing} onChange={e => choose(e.target.files?.[0])}/></label>
            <button className="button outline" type="button" disabled={busy || camera || editing} onClick={() => {setCamera(true);setConsent(false);}}> <Camera size={17}/> Open live camera</button>
            <label className="button outline file"><Camera size={17}/>Phone camera app<input aria-label="Use camera" type="file" accept="image/*" capture="environment" disabled={busy || camera || editing} onChange={e => choose(e.target.files?.[0])}/></label>
            {file && <button className="button outline" disabled={busy || camera || editing} onClick={() => {setEditing(true);setConsent(false);}}>Cover private details</button>}
            {file && <button className="button outline" disabled={busy || camera || editing} onClick={() => {setFile(undefined); setPreview(""); setConsent(false);}}><Trash2 size={17}/> Remove photo</button>}
          </div>
        </div>
        <p className="muted">Live camera video stays on your device. A photo is sent only after you select Process photograph. The server strips metadata and discards image bytes after processing. Gemini screening happens after submission; it cannot prevent that first transfer or guarantee every sensitive detail is detected.</p>
        <label className="check"><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)}/> I reviewed this photo, covered personal details, and consent to sending the selected photo to Google Gemini for privacy screening and object detection when available.</label>
        <button className="button primary" disabled={!file || !consent || busy || camera || editing} onClick={() => work(async () => {
          const body = new FormData();
          body.set("photo", file!); body.set("consent", "yes");
          const result = await api<Scan>("scans/", "POST", body);
          setScan(result);
          setObjects(result.objects.filter(object => object.usable_for_puzzle).map(object => object.name));
        })}><ScanLine size={18}/>{busy ? "Analyzing photograph…" : "Process photograph"}</button>
      </> : <form onSubmit={e => {e.preventDefault(); void work(async () => {
        play(await api<Game>(`scans/${scan.id}/`, "POST", {objects: objects.filter(item => item.trim()), theme, difficulty}));
      });}}>
        <h2>Confirm your evidence</h2>
        <p className="notice">{scan.privacy_status === "checked" ? "Automated screening did not flag sensitive content. This is not a guarantee; confirm that only ordinary objects are listed." : "Automated privacy screening was unavailable. Add only generic object names, without personal details."}</p>
        <p className="muted">Use names such as lamp or book. Do not enter names of people, email addresses, phone numbers, or document contents.</p>
        <p className="muted">{scan.source === "Gemini" && scan.objects.length ? "Gemini suggested these objects. Edit the list to match what you can see." : "Automatic analysis returned no usable detections. Add the objects you can see."}</p>
        {scan.objects.length > 0 && <details><summary>View detection details</summary><ul>{scan.objects.map(item => <li key={item.id}><strong>{item.name}</strong> · {item.description} ({item.confidence_label})</li>)}</ul></details>}
        {objects.map((item,index) => <div className="object-row" key={index}>
          <input aria-label={`Object ${index+1}`} value={item} maxLength={45} onChange={e => setObjects(objects.map((value,i) => i === index ? e.target.value : value))}/>
          <button className="icon-button" type="button" aria-label={`Remove object ${index+1}`} onClick={() => setObjects(objects.filter((_,i) => i !== index))}><X size={18}/></button>
        </div>)}
        <button type="button" className="button outline" disabled={objects.length >= 10} onClick={() => setObjects([...objects,""])}><Plus size={17}/> Add object</button>
        <div className="fields">
          <label>Theme<select value={theme} onChange={e => setTheme(e.target.value)}>{home.themes.map(value => <option key={value}>{value}</option>)}</select></label>
          <label>Difficulty<select value={difficulty} onChange={e => setDifficulty(e.target.value)}>{home.difficulty.map(value => <option key={value}>{value}</option>)}</select></label>
        </div>
        <div className="actions">
          <button className="button primary" disabled={busy || !objects.some(item => item.trim())}>{busy ? "Building your mystery…" : "Generate mystery"} <ArrowRight size={17}/></button>
          <button type="button" className="button outline" disabled={busy} onClick={() => work(async () => {
            await api(`scans/${scan.id}/`, "DELETE"); setScan(undefined); setFile(undefined); setPreview(""); setConsent(false);
          })}><Trash2 size={17}/> Delete scan</button>
        </div>
      </form>}
    </div>
  </section>;
}
