import {expect,test} from "@playwright/test";

for(const source of ["Gemini generated","Puzzle engine fallback"]){
  test(`round identifies ${source}`,async({page})=>{
    await page.addInitScript(()=>sessionStorage.setItem("roomverse-entry","guest"));
    await page.route("**/api/start/",route=>route.fulfill({json:{
      id:"midnight",game_id:"generation-check",title:"The Midnight Office",difficulty:"Beginner",
      intro:"Inspect the room and the fictional evidence records.",objective:"Reconstruct the recorded route.",
      source,story_title:"The Unfinished Evidence Review",phase:"observe",position:0,score:0,
      hints_remaining:3,deadline:new Date(Date.now()+60000).toISOString(),server_time:new Date().toISOString(),
      exhibits:[["Case record","A fictional delivery is under review."]],
    }}));
    await page.goto("/");await page.getByRole("button",{name:"Open The Midnight Office"}).click();
    await expect(page.getByText(source,{exact:true})).toBeVisible();
    await expect(page.getByRole("heading",{name:"Observe the scene"})).toBeVisible();
    await expect(page.locator(".story-tag")).toContainText("The Unfinished Evidence Review");
  });
}
