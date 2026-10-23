import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';

test('imported KRA-shaped records show provenance, independent odds, sectionals and race-time trainer',async({page})=>{
 const {raceId}=JSON.parse(execFileSync('python3',['../tests/kra_browser_fixture.py','create'],{encoding:'utf8'}));
 try{
  await page.goto('/races?date=2010-01-01');
  await expect(page.locator('.race-card')).toHaveCount(1);
  await expect(page.locator('.race-card')).toContainText('한국마사회 경주성적정보');
  await page.locator('.race-card').click();
  await expect(page.locator('h1')).toHaveText('서울 94R · 가상 KRA 검증');
  await expect(page.locator('.entry-table tbody tr')).toHaveCount(2);
  await expect(page.locator('.popularity-value').first()).toHaveText('미제공');
  await expect(page.locator('.odds-value').first()).toContainText('4.6배');
  await expect(page.locator('.odds-value').first()).toContainText('수집');
  await expect(page.locator('.entry-table')).toContainText('경주 당시 조교사');
  await expect(page.locator('.run-detail')).toContainText('39.30초');
  await expect(page.getByRole('region',{name:'코너별 통과 기록'})).toContainText('24.30초');
  await expect(page.getByRole('region',{name:'코너별 통과 기록'}).locator('tbody tr')).toHaveCount(2);
  await expect(page.getByRole('link',{name:'실험 모델 예측 ↗'})).toHaveCount(0);
  await expect(page.getByText('100엔당',{exact:false})).toHaveCount(0);
  await page.locator('.entry-table tbody tr').first().getByRole('link',{name:'가상 검증 조교사 ↗'}).click();
  await expect(page.locator('.facts')).toContainText('2회');
  await page.goto('/races/'+raceId);
  await page.locator('.entry-table tbody tr').first().getByRole('link',{name:'가상 KRA 검증말 1 ↗'}).click();
  await expect(page.locator('.detail-head')).toContainText('한국마사회 경주성적정보 · 마번 9700001');
  await expect(page.locator('.style-summary')).toContainText('판단 보류');
  await page.setViewportSize({width:375,height:812});
  await page.goto('/races/'+raceId);
  await expect(page.getByRole('region',{name:'코너별 통과 기록'})).toContainText('24.30초');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
  await page.screenshot({path:'../.runtime/kra-import-mobile.png',fullPage:true});
 }finally{
  execFileSync('python3',['../tests/kra_browser_fixture.py','clean',String(raceId)]);
 }
});
