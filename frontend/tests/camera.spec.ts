import {expect,test} from "@playwright/test";

test.beforeEach(async ({page}) => {
  await page.addInitScript(() => {
    sessionStorage.setItem("roomverse-entry","guest");
    Object.defineProperty(navigator.mediaDevices,"getUserMedia",{configurable:true,value:async () => {
      const canvas=document.createElement("canvas");canvas.width=640;canvas.height=480;
      const draw=()=>{const ctx=canvas.getContext("2d")!;ctx.fillStyle="#346789";ctx.fillRect(0,0,640,480);};draw();
      const timer=setInterval(draw,50);
      const stream=canvas.captureStream(20);
      stream.getTracks().forEach(track=>{const stop=track.stop.bind(track);track.stop=()=>{clearInterval(timer);document.documentElement.dataset.cameraStopped="yes";stop();};});
      return stream;
    }});
    Object.defineProperty(navigator.mediaDevices,"enumerateDevices",{value:async()=>[]});
  });
  await page.goto("/");
  await page.getByRole("button",{name:"Scan my room"}).click();
});

test("capture stays local until reviewed and submitted",async({page})=>{
  let uploads=0;
  await page.route("**/api/scans/",route=>{uploads++;return route.fulfill({json:{id:"mock",source:"Gemini",privacy_status:"checked",objects:[{id:"lamp",name:"Lamp",description:"A lamp",usable_for_puzzle:true,confidence_label:"high"}]}});});
  await page.getByRole("button",{name:"Open live camera"}).click();
  await expect(page.getByRole("button",{name:"Capture photo",exact:true})).toBeEnabled();
  await page.getByRole("button",{name:"Capture photo",exact:true}).click();
  await expect(page.getByAltText("Photograph selected for analysis")).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("data-camera-stopped","yes");
  expect(uploads).toBe(0);
  await expect(page.getByRole("button",{name:"Process photograph"})).toBeDisabled();
  await page.getByRole("checkbox").check();
  await page.getByRole("button",{name:"Process photograph"}).click();
  await expect(page.getByRole("heading",{name:"Confirm your evidence"})).toBeVisible();
  expect(uploads).toBe(1);
});

test("permission denial offers upload fallback",async({page})=>{
  await page.evaluate(()=>Object.defineProperty(navigator.mediaDevices,"getUserMedia",{configurable:true,value:async()=>{throw new DOMException("Denied","NotAllowedError");}}));
  await page.getByRole("button",{name:"Open live camera"}).click();
  await expect(page.getByRole("region",{name:"Live camera",exact:true}).getByRole("alert")).toContainText("Camera permission was denied");
  await page.getByRole("button",{name:"Close camera"}).click();
  await expect(page.getByLabel("Upload photo")).toBeEnabled();
});

test("private details can be covered locally before submission",async({page})=>{
  await page.getByLabel("Upload photo").setInputFiles("public/art/midnight.webp");
  await page.getByRole("checkbox").check();
  await page.getByRole("button",{name:"Cover private details",exact:true}).click();
  const canvas=page.locator(".privacy-editor canvas");
  await expect.poll(()=>canvas.evaluate(el=>(el as HTMLCanvasElement).width)).toBeGreaterThan(300);
  await canvas.scrollIntoViewIfNeeded();
  const bounds=(await canvas.boundingBox())!;
  await page.mouse.move(bounds.x+bounds.width*.2,bounds.y+bounds.height*.2);
  await page.mouse.down();
  await page.mouse.move(bounds.x+bounds.width*.6,bounds.y+bounds.height*.6,{steps:5});
  await page.mouse.up();
  expect(await canvas.evaluate(el=>{const c=el as HTMLCanvasElement;return Array.from(c.getContext("2d")!.getImageData(c.width*.4,c.height*.4,1,1).data);})).toEqual([0,0,0,255]);
  await page.getByRole("button",{name:"Use covered photo"}).click();
  await expect(page.getByRole("checkbox")).not.toBeChecked();
  await expect(page.getByRole("button",{name:"Process photograph"})).toBeDisabled();
  await expect(page.getByAltText("Photograph selected for analysis")).toBeVisible();
});
