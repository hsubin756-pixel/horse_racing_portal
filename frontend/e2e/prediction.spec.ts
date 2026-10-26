import {test,expect,type Page,type APIRequestContext} from '@playwright/test';
import {execFileSync} from 'node:child_process';

const API='http://127.0.0.1:8080/api',ML='http://127.0.0.1:8000';
const SYNTHETIC_RACE=8;   // 가상 미래 경주: 12두 출주, 합성 모델로 계산

async function login(page:Page,request:APIRequestContext,label:string){
 const email=label+'-'+Date.now()+'@example.test',password='Browser-predict-12345';
 expect((await request.post(API+'/auth/register',{data:{email,password,nickname:'예측 회원'}})).status()).toBe(201);
 await page.goto('/login');
 await page.getByLabel('이메일',{exact:true}).fill(email);await page.getByLabel('비밀번호',{exact:true}).fill(password);
 await page.getByRole('button',{name:'로그인 ↗'}).click();
 await expect(page.locator('h1')).toHaveText('나의 즐겨찾기');
}

// 인증 토큰은 메모리에만 있으므로 로그인 후에는 화면의 링크로 이동합니다.
async function openPrediction(page:Page,request:APIRequestContext,raceId:number){
 const {race}=await (await request.get(API+'/races/'+raceId)).json();
 await page.getByRole('link',{name:'경주·결과',exact:true}).click();
 await page.getByLabel('개최일',{exact:true}).fill(race.raceDate);
 await page.getByRole('button',{name:'검색 ↗'}).click();
 await page.locator('.race-card[href="/races/'+raceId+'"]').click();
 await page.getByRole('link',{name:'실험 모델 예측 ↗'}).click();
}

test('prediction is login-only: the page offers login and the API answers 401 without a token',async({page,request})=>{
 await page.goto('/races/'+SYNTHETIC_RACE+'/prediction');
 await expect(page.locator('h1')).toHaveText('경주 예측 실험실');
 await expect(page.getByRole('link',{name:'로그인하고 예측 실험하기 ↗'})).toBeVisible();
 await expect(page.getByRole('button',{name:'출주마 예측 점수 계산 ↗'})).toHaveCount(0);
 await expect(page.locator('.score-row')).toHaveCount(0);
 expect((await request.post(API+'/races/'+SYNTHETIC_RACE+'/prediction')).status()).toBe(401);
 await page.getByRole('link',{name:'로그인하고 예측 실험하기 ↗'}).click();
 await expect(page).toHaveURL(/\/login/);
});

test('synthetic race: scores are sorted, bounded, linked, and labelled as unverified',async({page,request})=>{
 await login(page,request,'predict-synthetic');
 await openPrediction(page,request,SYNTHETIC_RACE);
 await expect(page.locator('.eyebrow')).toContainText('SYNTHETIC DATA ONLY');
 await expect(page.locator('.notice').first()).toContainText('실제 예측 능력은 검증되지 않았습니다');
 const run=page.getByRole('button',{name:'출주마 예측 점수 계산 ↗'});
 await run.click();
 await expect(page.locator('.score-row')).toHaveCount(12);
 await expect(page.locator('.prediction-result')).toContainText('실제 예측 능력은 검증되지 않았습니다');
 await expect(page.locator('.model-info')).toHaveCount(0);     // 합성 모델에는 홀드아웃 지표·시장 기준선 표를 보이지 않음
 const scores=(await page.locator('.score-row b').allTextContents()).map(Number);
 expect(scores.every(s=>s>=0&&s<=1)).toBeTruthy();
 expect(scores).toEqual([...scores].sort((a,b)=>b-a));
 expect((await page.locator('.score-row .rank').allTextContents())).toEqual(Array.from({length:12},(_,i)=>String(i+1)));
 await page.locator('.score-row a').first().click();
 await expect(page.locator('.detail-head')).toBeVisible();
});

test('prediction outage shows the recovery message and no scores',async({page,request})=>{
 await login(page,request,'predict-outage');
 await page.route('**/api/races/*/prediction',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({message:'예측 서비스를 일시적으로 이용할 수 없습니다. 잠시 후 다시 시도하세요.'})}));
 await openPrediction(page,request,SYNTHETIC_RACE);
 await page.getByRole('button',{name:'출주마 예측 점수 계산 ↗'}).click();
 await expect(page.getByRole('alert')).toContainText('잠시 후 다시 시도하세요');
 await expect(page.locator('.score-row')).toHaveCount(0);
 await expect(page.getByRole('button',{name:'출주마 예측 점수 계산 ↗'})).toBeEnabled();   // 다시 시도 가능
});

test('real-data race: model info, market baseline and stored-history notes are shown (skipped without a real model)',async({page,request})=>{
 const health=await request.get(ML+'/health').then(r=>r.json()).catch(()=>null);
 test.skip(!health||!health.realDataModel,'ML 서비스에 실제 데이터 모델이 없습니다(ml/data 에 CSV를 두고 다시 빌드).');
 const {raceId}=JSON.parse(execFileSync('python3',['../tests/kra_browser_fixture.py','create'],{encoding:'utf8'}));
 try{
  await login(page,request,'predict-real');
  await openPrediction(page,request,raceId);
  await expect(page.locator('.eyebrow')).toContainText('KRA OPEN DATA MODEL');
  await page.getByRole('button',{name:'출주마 예측 점수 계산 ↗'}).click();
  await expect(page.locator('.score-row')).toHaveCount(2);
  await expect(page.locator('.model-info')).toContainText(health.realDataModel.cutoffDate);
  const table=page.getByRole('region',{name:'모델 홀드아웃 지표'});
  await expect(table.locator('tbody tr')).toHaveCount(2);
  await expect(table).toContainText('이 모델(시장 정보 없음)');
  await expect(table).toContainText('배당 순위만(시장 기준선)');
  const cells=await table.locator('tbody tr').first().locator('td').allTextContents();
  expect(cells.every(c=>/^\d\.\d{3}$/.test(c))).toBeTruthy();
  await expect(page.locator('.score-row small').first()).toHaveText('보존 전적 없음');   // 가상 검증 말은 학습 이력에 없음
  await expect(page.locator('.prediction-result')).toContainText('시장 정보');
  const scores=(await page.locator('.score-row b').allTextContents()).map(Number);
  expect(scores).toEqual([...scores].sort((a,b)=>b-a));
 }finally{
  execFileSync('python3',['../tests/kra_browser_fixture.py','clean',String(raceId)]);
 }
});

test('prediction page fits a phone viewport before and after calculating',async({page,request})=>{
 await login(page,request,'predict-mobile');
 await page.setViewportSize({width:375,height:812});
 await openPrediction(page,request,SYNTHETIC_RACE);
 await expect(page.locator('h1')).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
 await page.getByRole('button',{name:'출주마 예측 점수 계산 ↗'}).click();
 await expect(page.locator('.score-row')).toHaveCount(12);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
 await page.screenshot({path:'../.runtime/prediction-mobile.png',fullPage:true});
});
