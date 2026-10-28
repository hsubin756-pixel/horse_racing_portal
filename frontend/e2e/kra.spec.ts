import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';

test('void race preserves roster, shows no placings and offers no prediction',async({page})=>{
 const {raceId}=JSON.parse(execFileSync('python3',['../tests/kra_browser_fixture.py','create','서울','void'],{encoding:'utf8'}));
 try{
  await page.goto('/races/'+raceId);
  await expect(page.getByText('경주불성립으로 확정된 경주입니다.',{exact:false})).toBeVisible();
  await expect(page.getByRole('link',{name:'실험 모델 예측 ↗'})).toHaveCount(0);
  await expect(page.locator('.entry-table tbody tr')).toHaveCount(2);
  for(const row of await page.locator('.entry-table tbody tr').all()){
   await expect(row.locator('.rank')).toHaveText('—');
   await expect(row.getByRole('cell',{name:'경주불성립',exact:true})).toBeVisible();
  }
 }finally{execFileSync('python3',['../tests/kra_browser_fixture.py','clean',String(raceId)]);}
});

test('non-finishers retain distinct remarks without invented times or scratched popularity',async({page})=>{
 const {raceId}=JSON.parse(execFileSync('python3',['../tests/kra_browser_fixture.py','create','서울','nonfinishers'],{encoding:'utf8'}));
 try{
  await page.goto('/races/'+raceId);
  await expect(page.locator('.entry-table tbody tr')).toHaveCount(5);
  for(const [number,label] of [[3,'주행중지'],[4,'경주제외'],[5,'출전취소']] as const){
   const row=page.locator('.entry-table tbody tr').filter({hasText:`가상 비완주말 ${number}`});
   await expect(row.getByRole('cell',{name:label,exact:true})).toBeVisible();
   await expect(row.getByRole('cell',{name:'기록 없음',exact:true})).toBeVisible();
   await expect(row.locator('.rank')).toHaveText('—');
   if(number!==3)await expect(row.locator('.odds-value')).toHaveText('미제공');
   if(number===4){
    await expect(row.getByRole('cell',{name:'이름만 제공된 조교사',exact:true})).toBeVisible();
    await expect(row.getByRole('link',{name:/이름만 제공된 조교사/})).toHaveCount(0);
   }
  }
  await page.setViewportSize({width:375,height:812});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
 }finally{execFileSync('python3',['../tests/kra_browser_fixture.py','clean',String(raceId)]);}
});

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
  await expect(page.locator('.odds-provenance')).toContainText('수집');
  await expect(page.locator('.entry-table')).toContainText('경주 당시 조교사');
  await expect(page.locator('.run-detail')).toContainText('39.30초');
  await expect(page.getByRole('region',{name:'코너별 통과 기록'})).toContainText('24.30초');
  await expect(page.getByRole('region',{name:'코너별 통과 기록'}).locator('tbody tr')).toHaveCount(2);
  await page.getByRole('link',{name:'실험 모델 예측 ↗'}).click();
  await expect(page.locator('.eyebrow')).toContainText('KRA OPEN DATA MODEL');
  await expect(page.locator('.notice').first()).toContainText('시장 정보는 입력에 넣지 않았고');
  await page.goBack();
  await expect(page.getByText('100엔당',{exact:false})).toHaveCount(0);
  await page.locator('.entry-table tbody tr').first().getByRole('link',{name:'가상 검증 조교사 ↗'}).click();
  await expect(page.locator('.facts')).toContainText('2회');
  await page.goto('/races/'+raceId);
  await page.locator('.entry-table tbody tr').first().getByRole('link',{name:'가상 KRA 검증말 1 ↗'}).click();
  await expect(page.locator('.detail-head')).toContainText('한국마사회 자료 · 마번 9700001');
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

for(const [meet,last600] of [['제주','50.30초'],['부경','38.10초']]){
 test(`${meet}: converted sectionals show final 600m and running style`,async({page})=>{
  const {raceId}=JSON.parse(execFileSync('python3',['../tests/kra_browser_fixture.py','create',meet],{encoding:'utf8'}));
  try{
   await page.goto('/races/'+raceId);
   await expect(page.locator('.run-detail')).toContainText(last600);
   await expect(page.locator('.run-detail')).toContainText('선행');
   if(meet==='제주'){
    await expect(page.getByRole('region',{name:'코너별 통과 기록'})).toContainText('32.40초');
   }else{
    await expect(page.getByRole('region',{name:'코너별 통과 기록'})).toHaveCount(0);
   }
   await page.setViewportSize({width:375,height:812});
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
  }finally{
   execFileSync('python3',['../tests/kra_browser_fixture.py','clean',String(raceId),meet]);
  }
 });
}
