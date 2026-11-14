"use client";

import {useState} from "react";
import {Fingerprint, ArrowRight, Trophy, ShieldCheck} from "lucide-react";
import {api, Home, Gender} from "../lib/api";
import {VoiceSettings} from "./voice-settings";
import {portraitStyle, avatarStyle, ranks} from "../lib/ranks";

function GenderField({value = "others", change}: {value?: Gender;change?:(value:Gender)=>void}) {
  return <label>Gender<select name="gender" defaultValue={value} onChange={e=>change?.(e.target.value as Gender)} required><option value="male">Male</option><option value="female">Female</option><option value="others">Others</option></select><small className="muted">Suggests matching detective portraits. Others uses neutral characters.</small></label>;
}
function AvatarChoices({value="radar",gender}:{value?:string;gender:Gender}) {
  return <fieldset className="avatar-choices"><legend>Choose your detective avatar</legend>{["radar","fingerprint","key"].map((id,index)=><label key={id}><input type="radio" name="avatar" value={id} defaultChecked={value===id}/><span className="avatar-picture" role="img" aria-label={`${gender} detective portrait ${index+1}`} style={avatarStyle(id,gender)}/><span>{["Scout","Investigator","Chief"][index]}</span></label>)}</fieldset>;
}

export function Profile({home, refresh, resume, reset, clearReset, authenticated, initialMode = "login"}: {
  home: Home; refresh: () => Promise<void>; resume: (id: string) => void; reset: string; clearReset: () => void; authenticated: () => void; initialMode?: string;
}) {
  const [mode,setMode] = useState(initialMode);
  const [notice,setNotice] = useState("");
  const [error,setError] = useState("");
  const [busy,setBusy] = useState(false);
  const [gender,setGender] = useState<Gender>(home.profile?.gender || "others");
  const [removed,setRemoved] = useState<string[]>([]);
  const formMode = reset ? "confirm" : mode;
  async function action(path: string, method = "POST", data?: object, message = "") {
    setBusy(true); setNotice(""); setError("");
    try {await api(path,method,data); setNotice(message); await refresh(); return true;}
    catch (error) {setError((error as Error).message); return false;}
    finally {setBusy(false);}
  }

  return <section className="wrap tool">
    <span className="eyebrow"><Fingerprint size={17}/> DETECTIVE RECORDS</span>
    <h1>{home.profile ? home.profile.username : "Detective profile"}</h1>
    <p className="lede">Your investigations, field experience, and agency rankings.</p>
    {error && <p className="error" role="alert">{error}</p>}{notice && <p className="notice" role="status">{notice}</p>}
    <div className="investigation-grid">
      <div className="stack">
        <section className="panel"><h2>Investigation history</h2>
          {home.history.length ? <ul className="history">{home.history.map(item => <li key={item.id}><div><strong>{item.title}</strong><span>{item.phase === "complete" ? `${item.score} pts · Closed` : "In progress"}</span></div><button aria-label={`Open ${item.title}`} className="icon-button" onClick={() => resume(item.id)}><ArrowRight size={18}/></button></li>)}</ul> : <p className="muted">Your cases will appear here once you start an investigation.</p>}
        </section>
        <section className="panel"><h2><Trophy size={21}/> Achievements</h2><p>Level {home.level} · {home.xp} XP</p>
          {home.badges.length ? <ul className="badges">{home.badges.map(badge => <li key={badge}><Trophy size={15}/>{badge}</li>)}</ul> : <p className="muted">Close your first case to earn a badge.</p>}
        </section>
        <section className="panel"><h2>Your detective ranks</h2><p className="muted">Your best virtual case in each difficulty unlocks that difficulty’s rank. Each case is scored out of 1,000.</p><div className="rank-gallery">{ranks.map((rank,index) => <div className="rank-tile" key={rank.title} style={{borderColor:rank.color}}><span className="rank-art" role="img" aria-label={`${home.profile?.gender || "neutral"} ${rank.title}`} style={portraitStyle(index*200+1,home.profile?.gender)}/><strong style={{color:rank.color}}>{rank.title}</strong><span>{rank.range} points</span></div>)}</div></section>

      </div>
      <div className="stack">
        <section className={!home.profile || reset ? "panel auth-panel" : "panel"}>
          {!home.profile || reset ? <>
            <span className="eyebrow"><Fingerprint size={16}/> YOUR DETECTIVE ACCOUNT</span>
            <h2>{{register:"Create an account",login:"Sign in",reset:"Reset password",confirm:"Set a new password"}[formMode]}</h2>
            <p className="auth-description">{formMode === "register" ? "Start your detective record. Keep progress across devices and join your difficulty league." : formMode === "login" ? "Welcome back. Continue your investigations and keep your detective record together." : "Recover access to your detective record."}</p>
            <form className="stack auth-form" key={formMode} onSubmit={async e => {
              e.preventDefault();
              const form = new FormData(e.currentTarget);
              const ok = await action(`account/${formMode}/`,"POST", {...Object.fromEntries(form),token:reset},
                formMode === "reset" ? "If the account exists, a reset link has been sent." : formMode === "confirm" ? "Password updated. Sign in with your new password." : "");
              if (ok && (formMode === "login" || formMode === "register")) authenticated();
              if (ok && reset) clearReset();
            }}>
              {formMode !== "confirm" && <label>Username<input name="username" autoComplete="username" required maxLength={150}/></label>}
              {formMode === "register" && <><GenderField change={setGender}/><AvatarChoices gender={gender}/></>}
              {formMode === "register" && <label>Email<input name="email" type="email" maxLength={254} autoComplete="email" required/></label>}
              {formMode !== "reset" && <label>Password<input name="password" type="password" autoComplete={formMode === "login" ? "current-password" : "new-password"} required maxLength={128}/></label>}
              <button className="button primary" disabled={busy}>{formMode === "register" ? "Register" : formMode === "reset" ? "Send reset link" : formMode === "confirm" ? "Update password" : "Sign in"}</button>
            </form>
            {!reset && <div className="actions">{["login","register","reset"].filter(item => item !== mode).map(item => <button key={item} className="text-button" onClick={() => {setMode(item);setError("");setNotice("");}}>{item === "reset" ? "Forgot password?" : item === "login" ? "Sign in" : "Create an account"}</button>)}</div>}
          </> : <>
            <h2><span className="nav-avatar" style={avatarStyle(home.profile.avatar,home.profile.gender)}/> Account settings</h2>
            <form className="stack" onSubmit={e => {
              e.preventDefault();
              const form = new FormData(e.currentTarget);
              void action("account/profile/","POST",{avatar:form.get("avatar"),gender:form.get("gender"),public_score:form.has("public")},"Profile saved.");
            }}>
              <GenderField value={home.profile.gender} change={setGender}/>
              <AvatarChoices value={home.profile.avatar} gender={gender}/>
              <label className="check"><input name="public" type="checkbox" defaultChecked={home.profile.public_score}/> Share my username, detective character, and accumulated scores on the leaderboard</label>
              <div className="actions"><button className="button primary" disabled={busy}>Save profile</button><button className="button outline" type="button" disabled={busy} onClick={() => action("account/logout/","POST",{},"Signed out.")}>Sign out</button></div>
            </form>
            <details><summary>Delete account</summary><p className="muted">This removes your account, scans, and saved cases.</p><form className="stack" onSubmit={e => {
              e.preventDefault(); void action("account/delete/","POST",Object.fromEntries(new FormData(e.currentTarget)),"Account deleted.");
            }}><label>Current password<input type="password" name="password" autoComplete="current-password" required/></label><button className="button outline" disabled={busy}>Permanently delete account</button></form></details>
          </>}
        </section>
        {home.profile && <section className="panel"><h2>Reading voice</h2><VoiceSettings key={home.profile.username} profile={home.profile} onSaved={refresh}/></section>}
        <section className="panel"><h2><ShieldCheck size={20}/> Scan privacy</h2><p className="muted">The server retains detection records only. Deleting a scan removes the record. Existing cases keep the exhibit names used to build them.</p>
          {home.scans.filter(scan => !removed.includes(scan.id)).map(scan => <div key={scan.id} className="split"><span>{new Date(scan.created).toLocaleDateString()}</span><button className="text-button" disabled={busy} onClick={async () => {
            if (await action(`scans/${scan.id}/`,"DELETE",undefined,"Scan deleted.")) setRemoved(previous => [...previous,scan.id]);
          }}>Delete scan</button></div>)}
        </section>
      </div>
    </div>
  </section>;
}
