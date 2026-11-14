import {expect,test} from "@playwright/test";
test("fullscreen has a clear close action and preserves scrollbar-free panning",async({page})=>{
  await page.addInitScript(()=>sessionStorage.setItem("roomverse-entry","guest"));
  await page.goto("/");await page.getByRole("button",{name:"Open The Midnight Office"}).click();
  await page.getByRole("button",{name:"Expand scene",exact:true}).click();
  const dialog=page.getByRole("dialog",{name:/enlarged image/});await expect(dialog).toBeVisible();
  const close=page.getByRole("button",{name:"Close expanded scene",exact:true});await expect(close).toBeVisible();await expect(close).toBeFocused();
  await page.getByRole("button",{name:"Zoom in",exact:true}).click();
  const viewport=dialog.locator(".scene-viewport");
  expect(await viewport.evaluate(el=>{el.scrollLeft=el.scrollWidth;return el.scrollLeft;})).toBeGreaterThan(0);
  expect(await viewport.evaluate(el=>getComputedStyle(el).scrollbarWidth)).toBe("none");
  await close.click();await expect(dialog).toHaveCount(0);
  await expect(page.getByRole("button",{name:"Expand scene",exact:true})).toBeFocused();
  await page.getByRole("button",{name:"Expand scene",exact:true}).click();await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  expect(await page.evaluate(()=>document.body.style.overflow)).not.toBe("hidden");
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});
