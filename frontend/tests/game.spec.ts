import {expect, test} from "@playwright/test";
test.beforeEach(async ({page}) => {await page.addInitScript(() => sessionStorage.setItem("roomverse-entry","guest"));});

test("case archive, observation, and saved game", async ({page}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", {name:"Open a case file."})).toBeVisible();
  await page.getByRole("button", {name:"View all case files"}).click();
  await expect(page.getByRole("article")).toHaveCount(10);
  await page.getByRole("button", {name:"Special Challenge"}).click();
  await expect(page.getByRole("article")).toHaveCount(1);
  await page.getByRole("button",{name:"Beginner",exact:true}).click();
  await page.getByRole("button",{name:"Open The Midnight Office"}).click();
  await expect(page.getByRole("heading",{name:"Observe the scene"})).toBeVisible();
  await expect(page.locator(".story-tag")).toBeVisible();
  const storyTitle = await page.locator(".story-tag").innerText();
  await page.reload();
  await expect(page.getByRole("heading",{name:"Observe the scene"})).toBeVisible();
  await expect(page.locator(".story-tag")).toHaveText(storyTitle,{useInnerText:true});
  await page.locator(".case-heading").screenshot({path:`test-results/story-heading-${test.info().project.name}.png`});
  await expect(page.getByRole("combobox",{name:"Character voice",exact:true})).toBeVisible();
  const viewport = page.locator(".scene-viewport");
  await page.getByRole("button",{name:"Zoom in",exact:true}).click();
  await page.getByRole("button",{name:"Zoom in",exact:true}).click();
  await expect(page.getByLabel("Scene zoom",{exact:true})).toHaveText("196%");
  const bounds = await viewport.evaluate(element => {
    element.scrollLeft = element.scrollWidth;
    element.scrollTop = element.scrollHeight;
    return {x:element.scrollLeft,y:element.scrollTop};
  });
  expect(bounds.x).toBeGreaterThan(0);
  expect(bounds.y).toBeGreaterThan(0);
  await page.getByRole("button",{name:"Reset scene zoom"}).click();
  await expect(page.getByLabel("Scene zoom",{exact:true})).toHaveText("100%");
});

test("photo validation and prepared case through results", async ({page}) => {
  await page.goto("/");
  await page.getByRole("button",{name:"Scan my room"}).click();
  await expect(page.getByRole("button",{name:"Process photograph"})).toBeDisabled();
  await page.getByLabel("Upload photo").setInputFiles("public/art/midnight.webp");
  await page.getByRole("checkbox").check();
  await page.getByRole("button",{name:"Process photograph"}).click();
  await expect(page.getByRole("heading",{name:"Confirm your evidence"})).toBeVisible();
  await page.getByRole("button",{name:"Add object"}).click();
  await page.getByRole("textbox",{name:/Object \d+/}).last().fill("Desk lamp");
  await page.getByRole("button",{name:"Generate mystery"}).click();
  await expect(page.getByText("QUESTION 1 / 5")).toBeVisible();
  await page.getByRole("button",{name:"Reveal hint"}).click();
  await expect(page.getByRole("button",{name:/2 left/})).toBeVisible();
  await page.getByRole("textbox",{name:"Ask Nova for puzzle assistance"}).fill("Which evidence should I focus on?");
  await page.getByRole("button",{name:"Send hint request"}).click();
  await expect(page.getByRole("button",{name:/1 left/})).toBeVisible();
  for (let i=0;i<5;i++) {
    await expect(page.getByText(`QUESTION ${i+1} / 5`)).toBeVisible();
    await page.getByRole("radio").first().check();
    await page.getByRole("button",{name:"Submit answer"}).click();
  }
  await expect(page.getByText("CASE CLOSED",{exact:true})).toBeVisible();
  await page.getByRole("button",{name:"Review scene"}).click();
  await expect(page.locator(".evidence").first()).toContainText("Desk lamp");
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(await page.evaluate(() => window.innerWidth));
});



test("hint controls stay in view and read the revealed hint", async ({page}) => {
  test.setTimeout(100_000);
  await page.addInitScript(() => {
    Object.defineProperty(window,"SpeechSynthesisUtterance",{value:class {voice?:{name:string};constructor(public text:string){}}});
    Object.defineProperty(speechSynthesis,"getVoices",{value:()=>[{name:"Microsoft Zira",lang:"en-US"},{name:"Microsoft David",lang:"en-US"}]});
    Object.defineProperty(window.speechSynthesis, "speak", {
      value: (utterance: SpeechSynthesisUtterance) => {
        document.documentElement.dataset.spoken = utterance.text;
      },
    });
  });
  await page.goto("/");
  const started=page.waitForResponse(response=>response.url().endsWith("/api/start/") && response.request().method()==="POST");
  await page.getByRole("button", {name:"Open The Midnight Office",exact:true}).click();
  const hasChange=(await (await started).json()).has_change_round;
  await expect(page.getByRole("combobox", {name:"Character voice",exact:true})).toBeVisible();
  await expect(page.getByText("QUESTION 1 / 5")).toBeVisible({timeout:75_000});
  await expect(page.locator("html")).toHaveAttribute("data-spoken",/Option A\..*Option B\..*Option C\./);
  const voice = page.getByRole("combobox",{name:"Character voice",exact:true});
  await expect(voice.locator("option")).toHaveCount(2);
  await voice.selectOption("style:orion");
  await page.getByRole("button",{name:"Read question & options"}).click();
  await expect(page.locator("html")).toHaveAttribute("data-spoken",/Option A\./);
  await page.evaluate(() => window.scrollTo(0,document.body.scrollHeight));
  const hint = page.getByRole("button", {name:"Reveal hint"});
  await expect(hint).toBeInViewport();
  const hinted=page.waitForResponse(response=>response.url().includes("/nova/") && response.request().method()==="POST");
  await hint.click();
  const firstHint=(await (await hinted).json()).message;
  await expect(page.locator(".hint-dock p")).toHaveText(firstHint);
  await expect(page.locator("html")).toHaveAttribute("data-spoken",firstHint);
  await page.getByRole("button",{name:"Mute hint reading"}).click();
  const nextHint=page.waitForResponse(response=>response.url().includes("/nova/") && response.request().method()==="POST");
  await hint.click();
  await expect(page.locator(".hint-dock p")).toHaveText((await (await nextHint).json()).message);
  await expect(page.locator("html")).toHaveAttribute("data-spoken",firstHint);
  for (let index=0;index<5;index++) {
    await expect(page.getByText(`QUESTION ${index+1} / 5`)).toBeVisible();
    if (index === 1 && hasChange) {
      await expect(page.getByRole("region",{name:"Spot the change",exact:true})).toBeVisible();
      await expect(page.locator(".change-round .scene-surface")).toHaveCSS("background-image",/midnight-change-/);
    }
    await page.getByRole("radio").first().check();
    await page.getByRole("button",{name:"Submit answer"}).click();
  }
  if(hasChange){
  await page.getByText("Compare original and changed scene",{exact:true}).click();
  await expect(page.locator(".comparison-grid .scene-surface")).toHaveCount(2);
  await page.locator(".comparison-grid").screenshot({path:`test-results/change-comparison-${test.info().project.name}.png`});
  }
  await expect(page.getByRole("button",{name:"Download card",exact:true})).toHaveCount(0);
  await expect(page.getByRole("button",{name:"Share result",exact:true})).toHaveCount(0);
  await expect(page.getByRole("region",{name:"Detective result card"}).getByRole("img")).toBeVisible();
  await page.getByRole("region",{name:"Detective result card"}).getByRole("img").screenshot({path:`test-results/result-card-${test.info().project.name}.png`});
});


test("gender choice and all five rank characters are visible", async ({page}) => {
  await page.goto("/");
  await page.getByRole("button",{name:"Detective profile",exact:true}).click();
  await page.getByRole("button",{name:"Create an account",exact:true}).click();
  const gender = page.getByRole("combobox",{name:"Gender",exact:false});
  await expect(gender).toBeVisible();
  await expect(gender.locator("option")).toHaveText(["Male","Female","Others"]);
  await gender.selectOption("female");
  await expect(gender).toHaveValue("female");
  await expect(page.locator(".rank-tile")).toHaveCount(5);
  await page.locator(".rank-gallery").screenshot({path:`test-results/rank-gallery-${test.info().project.name}.png`});
});
