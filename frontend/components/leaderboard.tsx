"use client";

import {useEffect,useState} from "react";
import {api,Home,Gender} from "../lib/api";
import {avatarStyle} from "../lib/ranks";

type Leader={name:string;avatar:string;character:Gender;rank:number;score:number;title:string;attempts:number;total_time_ms:number};
export function Leaderboard({home,signIn,profile,play}:{home:Home;signIn:()=>void;profile:()=>void;play:()=>void}) {
  const [league,setLeague]=useState("Beginner");
  const [rows,setRows]=useState<Leader[]>();
  const [error,setError]=useState("");
  useEffect(()=>{
    if (!home.profile) return;
    let active=true,pending=false;
    async function update(){
      if(pending || document.hidden)return;
      pending=true;
      try{const next=await api<Leader[]>(`leaderboard/?difficulty=${encodeURIComponent(league)}`);if(active){setRows(next);setError("");}}
      catch{if(active)setError("Could not refresh rankings. Check your connection; we will retry automatically.");}
      finally{pending=false;}
    }
    void update();const timer=setInterval(update,5000);window.addEventListener("focus",update);
    return()=>{active=false;clearInterval(timer);window.removeEventListener("focus",update);};
  },[home.profile,league]);
  return <section className="wrap tool"><span className="eyebrow">AGENCY RANKINGS</span><h1>Leaderboard</h1>
    <p className="lede">Meet the detectives leading each difficulty. Rankings refresh every five seconds.</p>
    {!home.profile ? <div className="panel"><h2>Sign in to see the rankings</h2><p>Complete a virtual case and enable score sharing in your profile to join. Scanner practice stays unranked.</p><button className="button primary" onClick={signIn}>Sign in</button></div> : <>
      {!home.profile.public_score && <div className="notice"><strong>Your scores are private.</strong><p>Enable score sharing in your profile to appear here after completing a virtual case.</p><button className="button outline" onClick={profile}>Manage score sharing</button></div>}
      <section className="panel"><label>Leaderboard difficulty<select value={league} onChange={e=>{setLeague(e.target.value);setRows(undefined);setError("");}}>{["Beginner","Intermediate","Professional","Special Challenge"].map(level=><option key={level}>{level}</option>)}</select></label>
        <p className="muted">Every completed virtual case adds to your total in this difficulty. Higher totals win; ties favor fewer completed cases, then shorter total duration. Exact ties share rank, with the earlier final completion displayed first. Detective titles reflect your best single-case score.</p>
        {error && <p role="alert" className="error">{error}</p>}
        {rows?.length ? <ol className="history leaderboard-rows">{rows.map(row=><li key={row.name}><span className="rank-position">#{row.rank}</span><span className="rank-portrait" role="img" aria-label={`${row.name}'s detective avatar`} style={avatarStyle(row.avatar,row.character)}/><div className="rank-player"><strong>{row.name}</strong><span>{row.title}</span><small>{row.attempts} completed cases · {(row.total_time_ms/1000).toFixed(3)}s total</small></div><strong>{row.score.toLocaleString()} pts</strong></li>)}</ol> : rows ? <div className="leaderboard-empty"><h2>Be the first {league} detective.</h2><p>No eligible scores in this league yet. Finish a {league} virtual case while signed in and enable score sharing. Unfinished cases, private scores, and scanner practice do not appear.</p><div className="actions"><button className="button primary" onClick={play}>Choose a virtual case</button><button className="button outline" onClick={profile}>Profile and score sharing</button></div></div> : !error && <p role="status">Loading rankings…</p>}
      </section></>}
  </section>;
}
