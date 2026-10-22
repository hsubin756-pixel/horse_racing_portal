import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./e2e',workers:1,timeout:30000,use:{baseURL:'http://127.0.0.1:5173',headless:true,launchOptions:{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE||undefined}},reporter:[['list'],['html',{outputFolder:'../.runtime/browser-report',open:'never'}]],outputDir:'../.runtime/browser-results'});
