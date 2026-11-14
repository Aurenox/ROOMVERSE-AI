"use client";

import {useEffect, useState} from "react";
import {Download, Share2} from "lucide-react";
import {Game} from "../lib/api";
import {characterRow, rankTier, ranks} from "../lib/ranks";

function drawCard(game: Game, portrait: HTMLImageElement) {
  const canvas = document.createElement("canvas");
  canvas.width = 1200;
  canvas.height = 760;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Card rendering is unavailable.");
  const tier = rankTier(game.rank_score ?? game.score);
  const accent = ranks[tier].color;
  const gradient = ctx.createLinearGradient(0,0,1200,760);
  gradient.addColorStop(0,"#071421");
  gradient.addColorStop(1,"#173c49");
  ctx.fillStyle = gradient;
  ctx.fillRect(0,0,1200,760);
  ctx.strokeStyle = "#4b919c";
  ctx.lineWidth = 2;
  ctx.strokeRect(22,22,1156,716);
  ctx.fillStyle = accent;
  ctx.fillRect(52,55,42,4);
  function text(value: string, x: number, y: number, size: number, color: string, maxWidth: number, bold = false) {
    ctx!.font = `${bold ? "bold " : ""}${size}px Arial`;
    ctx!.fillStyle = color;
    let fitted = value;
    while (ctx!.measureText(fitted).width > maxWidth && fitted.length) fitted = fitted.slice(0,-1);
    if (fitted !== value) fitted = fitted.slice(0,-1) + "…";
    ctx!.fillText(fitted,x,y);
  }
  text("ROOMVERSE AI",110,66,24,accent,570,true);
  text("CASE CLOSED",56,132,17,"#77d9dd",650,true);
  text(game.detective_title || "Unlisted",52,205,54,"#f1f5f9",700,true);
  text(game.detective_name || "Guest Detective",56,249,25,"#afc5d1",650);
  text(`${game.practice_only ? "PRACTICE SCORE" : "LEVEL BEST"}: ${game.rank_score ?? game.score} · ${ranks[tier].range} RANK BAND`,56,330,15,accent,650);
  text(game.title,56,299,24,"#f1f5f9",650);
  text(String(game.score),52,427,110,accent,420,true);
  text("/ 1,000 POINTS",58,465,19,"#afc5d1",480);
  const statistics = [
    [`${game.correct ?? 0}/5`, "CORRECT"],
    [`${(game.correct ?? 0)*20}%`, "ACCURACY"],
    [String(game.hints_used ?? 0), "HINTS"],
    [`${Math.floor((game.elapsed ?? 0)/60)}m ${(game.elapsed ?? 0)%60}s`, "TIME"],
  ];
  statistics.forEach(([value,label],index) => {
    text(value,56+index*165,548,32,"#f1f5f9",155,true);
    text(label,56+index*165,582,14,"#afc5d1",155);
  });
  ctx.strokeStyle = "#38616f";
  ctx.beginPath(); ctx.moveTo(56,625); ctx.lineTo(1144,625); ctx.stroke();
  const rank = game.practice_only ? "PERSONAL PRACTICE · NOT RANKED" : game.leaderboard_rank ? `AGENCY RANK #${game.leaderboard_rank}` : "AGENCY RANK · UNLISTED";
  text(rank,56,672,22,accent,650,true);
  text(game.practice_only ? "Real-world observation practice · excluded from every leaderboard" : game.leaderboard_rank ? `${game.leaderboard_difficulty || game.difficulty} league · total points, completed cases, total duration` : "Sign in and opt into your difficulty leaderboard to earn a position",56,705,15,"#afc5d1",1000);
  const height = 530;
  const cellWidth = portrait.naturalWidth/5;
  const cellHeight = portrait.naturalHeight/3;
  const width = Math.min(390, height * cellWidth/cellHeight);
  const drawHeight = width * cellHeight/cellWidth;
  ctx.drawImage(portrait,tier*cellWidth,characterRow(game.character)*cellHeight,cellWidth,cellHeight,940-width/2,623-drawHeight,width,drawHeight);
  text(game.difficulty.toUpperCase(),820,65,16,"#afc5d1",310,true);
  return canvas;
}

export function ResultCard({game,signedIn,signIn}: {game: Game;signedIn:boolean;signIn:()=>void}) {
  const [card,setCard] = useState<{url:string;blob:Blob}>();
  const [notice,setNotice] = useState("");
  useEffect(() => {
    let disposed = false;
    let url = "";
    const portrait = new Image();
    portrait.onload = () => {
      if (disposed) return;
      try {
        drawCard(game,portrait).toBlob(blob => {
          if (!blob || disposed) return;
          url = URL.createObjectURL(blob);
          setCard({url,blob});
        },"image/png");
      } catch {setNotice("The card could not render. Reload to try again.");}
    };
    portrait.onerror = () => {if (!disposed) setNotice("The detective portrait could not load. Reload to try again.");};
    portrait.src = "/art/detective-ranks.png";
    return () => {disposed = true; if (url) URL.revokeObjectURL(url);};
  }, [game]);

  function download() {
    if (!card || !signedIn) return;
    const link = document.createElement("a");
    link.href = card.url;
    link.download = "roomverse-detective-result.png";
    link.click();
  }

  async function share() {
    if (!card || !signedIn) return;
    const file = new File([card.blob],"roomverse-detective-result.png",{type:"image/png"});
    if (navigator.canShare?.({files:[file]})) {
      try {await navigator.share({files:[file],title:"My ROOMVERSE detective result"});}
      catch (error) {if ((error as Error).name !== "AbortError") setNotice("Sharing is unavailable. Use Download card to save the image.");}
    } else {
      download();
      setNotice("Card downloaded. You can attach the PNG wherever you want to share it.");
    }
  }

  return <section className="result-card" aria-label="Detective result card">
    {card ? (
      // eslint-disable-next-line @next/next/no-img-element
      <img src={card.url} alt={`${game.detective_name || "Guest Detective"} earned ${game.detective_title}, ${game.score} points, ${game.correct}/5 correct, ${game.hints_used} hints. ${game.leaderboard_rank ? `Agency rank ${game.leaderboard_rank}` : "Unlisted in the leaderboard"}.`}/>
    ) : <p role="status">Preparing your detective card…</p>}
    {signedIn ? <div className="actions">
      <button className="button primary" disabled={!card} onClick={share}><Share2 size={17}/> Share result</button>
      <button className="button outline" disabled={!card} onClick={download}><Download size={17}/> Download card</button>
    </div> : <p className="notice">Sign in to share your result or download your detective card. <button className="text-button" onClick={signIn}>Sign in</button></p>}
    {notice && <p role="status">{notice}</p>}
  </section>;
}
