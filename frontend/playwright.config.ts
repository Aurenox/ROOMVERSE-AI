import {defineConfig, devices} from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  use: {baseURL: process.env.ROOMVERSE_TEST_URL || "http://localhost:3000"},
  projects: [
    {name:"desktop", use:{...devices["Desktop Edge"], channel:"msedge"}},
    {name:"mobile", use:{...devices["Pixel 7"], channel:"msedge"}},
  ],
});
