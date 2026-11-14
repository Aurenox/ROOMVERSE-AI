import {expect, test} from "@playwright/test";
test.beforeEach(async ({page}) => {await page.addInitScript(() => sessionStorage.setItem("roomverse-entry","guest"));});

test("signup and login voice setup, profile persistence, and signed-in exports", async ({page}) => {
  test.setTimeout(60000);
  const username = `voice_${test.info().project.name}_${Date.now()}`;
  const password = "Roomverse-test-Voice-742!";
  await page.addInitScript(() => {
    Object.defineProperty(window,"SpeechSynthesisUtterance",{value:class {voice?:{name:string};pitch=1;rate=1;constructor(public text:string){}}});
    Object.defineProperty(speechSynthesis,"getVoices",{value:()=>[{name:"Microsoft Zira",lang:"en-US"},{name:"Microsoft David",lang:"en-US"}]});
    Object.defineProperty(window.speechSynthesis,"speak",{value:(speech:SpeechSynthesisUtterance) => {
      document.documentElement.dataset.preview = `${speech.pitch.toFixed(2)}:${speech.rate.toFixed(2)}`;
    }});
  });
  await page.goto("/");
  await expect(page.locator(".home-ranks .rank-tile")).toHaveCount(5);
  await page.getByRole("button",{name:"Detective profile",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Leaderboard",exact:true})).toHaveCount(0);
  await page.getByRole("button",{name:"Create an account",exact:true}).click();
  await page.getByLabel("Username",{exact:true}).fill(username);
  await page.getByLabel("Email",{exact:true}).fill(`${username}@example.com`);
  await page.getByLabel("Password",{exact:true}).fill(password);
  await page.getByRole("combobox",{name:"Gender"}).selectOption("female");
  await page.getByRole("button",{name:"Register",exact:true}).click();
  try {
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText("Preparing your headquarters…")).toBeVisible();
    await expect(dialog.getByRole("combobox",{name:"Website voice"})).toHaveCount(0);
    await expect(dialog.getByRole("combobox",{name:"Website voice"})).toBeVisible({timeout:8000});
    await dialog.getByRole("combobox",{name:"Website voice"}).selectOption("style:orion");
    await dialog.getByRole("combobox",{name:"Voice speed"}).selectOption("0.75");
    await dialog.getByRole("button",{name:"Preview voice"}).click();
    await expect(page.locator("html")).toHaveAttribute("data-preview","1.12:0.75");
    await dialog.screenshot({path:`test-results/voice-welcome-${test.info().project.name}.png`});
    await dialog.getByRole("button",{name:"Set voice & open home"}).click();
    await expect(dialog).toHaveCount(0);
    await expect(page.getByRole("heading",{name:"Every clue builds your rank."})).toBeVisible();
    await page.getByRole("button",{name:"Detective profile",exact:true}).click();
    await expect(page.getByRole("combobox",{name:"Website voice"})).toHaveValue("style:orion");
    await expect(page.getByRole("combobox",{name:"Voice speed"})).toHaveValue("0.75");
    const menu=page.getByRole("button",{name:"Open menu",exact:true});
    if(await menu.isVisible())await menu.click();
    await page.getByRole("navigation",{name:"Main navigation"}).getByRole("button",{name:"Leaderboard",exact:true}).click();
    await expect(page.getByRole("heading",{name:"Leaderboard",exact:true})).toBeVisible();
    const league = page.getByRole("combobox",{name:"Leaderboard difficulty"});
    await league.selectOption("Professional");
    await expect(league).toHaveValue("Professional");
    await league.selectOption("Intermediate");
    await expect(league).toHaveValue("Intermediate");
    await page.getByRole("button",{name:"Detective profile",exact:true}).click();
    await page.getByRole("combobox",{name:"Voice speed"}).selectOption("1.15");
    await page.getByRole("button",{name:"Save voice",exact:true}).click();
    await expect(page.getByText("Voice preferences saved.")).toBeVisible();
    await page.getByRole("button",{name:"Sign out",exact:true}).click();
    await page.getByLabel("Username",{exact:true}).fill(username);
    await page.getByLabel("Password",{exact:true}).fill(password);
    await page.getByRole("button",{name:"Sign in",exact:true}).click();
    await expect(dialog.getByRole("combobox",{name:"Voice speed"})).toBeVisible({timeout:8000});
    await expect(dialog.getByRole("combobox",{name:"Voice speed"})).toHaveValue("1.15");
    await dialog.getByRole("button",{name:"Set voice & open home"}).click();
    await page.route("**/api/start/",route => route.fulfill({json:{
      id:"midnight",game_id:"card-test",title:"The Midnight Office",difficulty:"Professional",intro:"Test case",objective:"Complete",source:"Virtual case",phase:"complete",position:5,score:1000,hints_remaining:3,deadline:null,server_time:new Date().toISOString(),exhibits:[],review:[],completion:"Case closed.",hints_used:0,correct:5,elapsed:70,detective_name:username,detective_title:"Professional Detective",character:"female",rank_score:1000,leaderboard_rank:null,
    }}));
    await page.getByRole("button",{name:"Open The Midnight Office",exact:true}).click();
    await expect(page.getByRole("button",{name:"Share result",exact:true})).toBeEnabled();
    const download = page.waitForEvent("download");
    await page.getByRole("button",{name:"Download card",exact:true}).click();
    expect((await download).suggestedFilename()).toBe("roomverse-detective-result.png");
  } finally {
    await page.evaluate(async password => {
      const csrf = document.cookie.split("; ").find(c => c.startsWith("csrftoken="))?.split("=")[1] || "";
      await fetch("/api/account/delete/",{method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":csrf},body:JSON.stringify({password})});
    },password);
  }
});
