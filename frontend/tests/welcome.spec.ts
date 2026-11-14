import {expect,test} from "@playwright/test";

test("first visit offers guest mode and preserves guest voice without an account",async ({page}) => {
  let voiceSaves = 0;
  page.on("request",request => {if (request.url().includes("/account/voice/")) voiceSaves++;});
  await page.goto("/");
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("heading",{name:"How would you like to play?"})).toBeVisible();
  await expect(dialog.getByText(/temporary session cookie links this browser/)).toBeVisible();
  await dialog.getByRole("button",{name:"Continue as guest"}).click();
  await expect(dialog.getByText("Preparing your headquarters…")).toBeVisible();
  await expect(dialog.getByRole("combobox",{name:"Website voice"})).toBeVisible({timeout:8000});
  await dialog.getByRole("combobox",{name:"Website voice"}).selectOption("style:orion");
  await dialog.getByRole("combobox",{name:"Voice speed"}).selectOption("1");
  await dialog.screenshot({path:`test-results/guest-voice-${test.info().project.name}.png`});
  await dialog.getByRole("button",{name:"Set voice & open home"}).click();
  await expect(dialog).toHaveCount(0);
  expect(voiceSaves).toBe(0);
  await expect(page.getByRole("button",{name:"Login",exact:true})).toBeVisible();
  await expect(page.getByRole("button",{name:"Sign up",exact:true})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.locator(".site-header").screenshot({path:`test-results/guest-navbar-${test.info().project.name}.png`});
  await expect(page.getByRole("heading",{name:"Train how you notice and reason."})).toBeVisible();
  await page.getByRole("button",{name:"Open The Midnight Office",exact:true}).click();
  await expect(page.getByRole("combobox",{name:"Character voice",exact:true})).toHaveValue("style:orion");
  await expect(page.getByRole("combobox",{name:"Reading speed"})).toHaveValue("1");
  await page.reload();
  await expect(page.getByRole("heading",{name:"Observe the scene"})).toBeVisible();
  await expect(dialog).toHaveCount(0);
});

test("entry sign-in and top navigation open the correct auth forms",async ({page}) => {
  await page.goto("/");
  await page.getByRole("dialog").getByRole("button",{name:"Sign in",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Sign in",exact:true})).toBeVisible();
  await page.getByRole("button",{name:"Sign up",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Create an account",exact:true})).toBeVisible();
  await expect(page.locator(".auth-panel .auth-form")).toBeVisible();
  const signupStyle = await page.locator(".auth-panel").getAttribute("class");
  await page.locator(".auth-panel").screenshot({path:`test-results/signup-style-${test.info().project.name}.png`});
  await page.getByRole("button",{name:"Login",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Sign in",exact:true})).toBeVisible();
  await expect(page.locator(".auth-panel")).toHaveAttribute("class",signupStyle!);
});
