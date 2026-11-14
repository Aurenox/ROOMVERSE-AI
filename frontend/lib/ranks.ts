import {Gender} from "./api";

export const ranks = [
  {title:"Unlisted", range:"0–200", color:"#b2c2d1"},
  {title:"Clue Hunter", range:"201–400", color:"#74d9ad"},
  {title:"Field Investigator", range:"401–600", color:"#73ddeb"},
  {title:"Senior Detective", range:"601–800", color:"#b5a2ff"},
  {title:"Professional Detective", range:"801–1,000", color:"#f1ca76"},
];
export const rankTier = (score: number) => Math.min(4, Math.max(0, Math.ceil(score / 200) - 1));
export const characterRow = (gender: Gender = "others") => gender === "female" ? 0 : gender === "male" ? 1 : 2;
export const portraitStyle = (score: number, gender: Gender = "others") => ({
  backgroundImage:'url("/art/detective-ranks.png")', backgroundSize:"500% 300%",
  backgroundPosition:`${rankTier(score)*25}% ${characterRow(gender)*50}%`,
});

export const avatarStyle = (avatar: string = "radar", gender: Gender = "others") => portraitStyle(avatar === "key" ? 801 : avatar === "fingerprint" ? 401 : 1, gender);
