import {expect,test} from "@playwright/test";
test.beforeEach(async({page})=>{await page.addInitScript(()=>{
  sessionStorage.setItem("roomverse-entry","guest");localStorage.setItem("roomverse-voice","style:luna");
  Object.defineProperty(window,"SpeechSynthesisUtterance",{value:class {voice?:{name:string};constructor(public text:string){}}});
  Object.defineProperty(speechSynthesis,"getVoices",{value:()=>document.documentElement.dataset.voicesReady ? [{name:"Microsoft David",lang:"en-US"},{name:"Microsoft Zira",lang:"en-US"}] : [{name:"Microsoft David",lang:"en-US"}]});
  Object.defineProperty(speechSynthesis,"speak",{value:(speech:{voice?:{name:string}})=>{document.documentElement.dataset.spokenVoice=speech.voice?.name || "default";}});
  Object.defineProperty(speechSynthesis,"cancel",{value:()=>{}});
});});

test("first gameplay preview waits for the selected female voice",async({page})=>{
  await page.goto("/");await page.getByRole("button",{name:"Open The Midnight Office"}).click();
  await page.getByRole("button",{name:"Preview",exact:true}).click();
  await expect(page.locator("html")).not.toHaveAttribute("data-spoken-voice",/.+/);
  await page.evaluate(()=>{document.documentElement.dataset.voicesReady="yes";speechSynthesis.dispatchEvent(new Event("voiceschanged"));});
  await expect(page.locator("html")).toHaveAttribute("data-spoken-voice","Microsoft Zira");
});

test("footer credit and back to top retain the current section",async({page})=>{
  await page.goto("/");await page.getByRole("button",{name:"Scan my room"}).click();
  await expect(page.getByText("© ROOMVERSE AI @2026",{exact:true})).toBeVisible();
  await expect(page.getByText("Built by Saurav B",{exact:true})).toBeVisible();
  await expect(page.locator("footer").getByRole("button",{name:"Detective records"})).toHaveCount(0);
  const centered=await page.locator(".footer-credit").boundingBox();
  expect(Math.abs(centered!.x+centered!.width/2-page.viewportSize()!.width/2)).toBeLessThan(3);
  const top=page.getByRole("button",{name:"Back to top",exact:true});await top.scrollIntoViewIfNeeded();await top.click();
  await expect.poll(()=>page.evaluate(()=>window.scrollY)).toBe(0);
  await expect(page.getByRole("heading",{name:"Every room hides a case."})).toBeVisible();
});
