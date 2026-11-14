import {expect,test} from "@playwright/test";

test.beforeEach(async({page})=>{await page.addInitScript(()=>sessionStorage.setItem("roomverse-entry","guest"));});

test("header leaderboard and gender-matched avatar choices",async({page})=>{
  await page.goto("/");
  const menu=page.getByRole("button",{name:"Open menu",exact:true});
  if(await menu.isVisible())await menu.click();
  await page.getByRole("navigation",{name:"Main navigation"}).getByRole("button",{name:"Leaderboard",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Sign in to see the rankings"})).toBeVisible();
  await page.getByRole("button",{name:"Sign up",exact:true}).click();
  await page.getByRole("combobox",{name:/^Gender/}).selectOption("female");
  await expect(page.getByRole("img",{name:/female detective portrait/})).toHaveCount(3);
  await page.getByRole("radio",{name:/Chief/}).check();
  await page.getByRole("combobox",{name:/^Gender/}).selectOption("male");
  await expect(page.getByRole("img",{name:/male detective portrait/})).toHaveCount(3);
  await expect(page.getByRole("radio",{name:/Chief/})).toBeChecked();
});

test("rankings display saved avatars and refresh without reload",async({page})=>{
  await page.route("**/api/",async route=>{
    const response=await route.fetch();const home=await response.json();
    home.profile={username:"Test Detective",avatar:"key",gender:"female",voice_style:"style:luna",voice_rate:1,public_score:true};
    await route.fulfill({json:home});
  });
  let count=0;
  await page.route("**/api/leaderboard/**",route=>{
    const empty=route.request().url().includes("Intermediate");count++;
    return route.fulfill({json:empty?[]:[{name:"Test Detective",avatar:"key",character:"female",rank:1,score:count===1?2000:2500,title:"Senior Detective",attempts:2,total_time_ms:90000}]});
  });
  await page.goto("/");
  const menu=page.getByRole("button",{name:"Open menu",exact:true});if(await menu.isVisible())await menu.click();
  await page.getByRole("navigation",{name:"Main navigation"}).getByRole("button",{name:"Leaderboard",exact:true}).click();
  await expect(page.getByRole("img",{name:"Test Detective's detective avatar"})).toBeVisible();
  await expect(page.getByText("2,000 pts",{exact:true})).toBeVisible();
  await expect(page.getByText("2,500 pts",{exact:true})).toBeVisible({timeout:10000});
  await page.getByLabel("Leaderboard difficulty").selectOption("Intermediate");
  await expect(page.getByRole("heading",{name:"Be the first Intermediate detective."})).toBeVisible();
});
