// Wait for the device voice list instead of speaking with an unrelated default.
export async function readingVoice(style:string):Promise<SpeechSynthesisVoice | undefined> {
  const female=style!=="style:orion";
  const pattern=female ? /zira|hazel|heera|samantha|victoria|female/i : /david|mark|george|james|daniel|alex|aaron|guy|male/i;
  const find=()=>window.speechSynthesis.getVoices().find(v=>pattern.test(v.name) && (female || !/female/i.test(v.name)));
  const ready=find();if(ready)return ready;
  return new Promise(resolve=>{
    const finish=()=>{clearTimeout(timeout);clearInterval(poll);window.speechSynthesis.removeEventListener("voiceschanged",check);resolve(find());};
    const check=()=>{if(find())finish();};
    const timeout=setTimeout(finish,3000);
    const poll=setInterval(check,100);
    window.speechSynthesis.addEventListener("voiceschanged",check);
  });
}
