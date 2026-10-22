import {test,expect} from '@playwright/test';
test('public search, history, pedigree, empty search and races',async({page})=>{
 await page.goto('/');await expect(page.getByRole('heading',{name:'한 마리의 기록에서, 경마의 세계로.'})).toBeVisible();
 await page.screenshot({path:'../.runtime/home-desktop.png',fullPage:true});
 await page.getByRole('link',{name:'경주마',exact:true}).click();
 await page.getByLabel('경주마 이름', {exact:true}).fill('유키노');const searchStart=Date.now();await page.getByRole('button',{name:'검색 ↗'}).click();
 await expect(page.locator('.horse-card')).toHaveCount(1);const elapsed=Date.now()-searchStart;expect(elapsed).toBeLessThan(3000);console.log('Browser search display latency:',elapsed,'ms');await page.locator('.horse-card').click();
 await expect(page.getByRole('heading',{name:'유키노 세레나',exact:true})).toBeVisible();await expect(page.locator('tbody tr')).toHaveCount(7);
 await page.getByRole('link',{name:'3대 혈통 탐색 ↗'}).click();await expect(page.locator('.ped-scroll')).toBeVisible();await expect(page.getByRole('heading',{name:'유키노 세레나의 혈통'})).toBeVisible();
 await page.goto('/horses?q=not-existing');await expect(page.getByText('검색 결과가 없습니다',{exact:true})).toBeVisible();
 await page.getByRole('link',{name:'경주·결과',exact:true}).click();await page.getByLabel('개최일',{exact:true}).fill('2025-01-15');await page.getByRole('button',{name:'검색 ↗'}).click();
 await expect(page.locator('.race-card')).toHaveCount(1);await page.locator('.race-card').click();await expect(page.locator('tbody tr')).toHaveCount(12);
 await expect(page.locator('tbody tr').first().locator('.rank')).toHaveText('1');
});
test('register, login, favorites, prediction and logout',async({page})=>{
 const email='browser-'+Date.now()+'@example.test';const password='Browser-test-pass-123';
 await page.goto('/register');await page.getByLabel('이메일',{exact:true}).fill(email);await page.getByLabel('비밀번호',{exact:true}).fill(password);await page.getByLabel('닉네임',{exact:true}).fill('브라우저 회원');await page.getByRole('button',{name:'회원가입 ↗'}).click();
 await expect(page.getByRole('status')).toContainText('회원가입이 완료되었습니다');await page.getByRole('link',{name:'로그인하기 →'}).click();
 await page.getByLabel('이메일',{exact:true}).fill(email);await page.getByLabel('비밀번호',{exact:true}).fill('wrong-password');await page.getByRole('button',{name:'로그인 ↗'}).click();await expect(page.getByRole('alert')).toContainText('올바르지 않습니다');
 await page.getByLabel('비밀번호',{exact:true}).fill(password);await page.getByRole('button',{name:'로그인 ↗'}).click();await expect(page.getByRole('heading',{name:'나의 즐겨찾기'})).toBeVisible();
 await page.getByRole('link',{name:'경주마',exact:true}).click();await page.getByLabel('경주마 이름',{exact:true}).fill('유키노');await page.getByRole('button',{name:'검색 ↗'}).click();await page.locator('.horse-card').click();
 await page.getByRole('button',{name:'☆ 즐겨찾기 추가'}).click();await expect(page.getByRole('status')).toContainText('추가했습니다');
 await page.getByRole('button',{name:'☆ 즐겨찾기 추가'}).click();await expect(page.getByRole('status')).toContainText('이미 즐겨찾기');
 await page.getByRole('link',{name:'즐겨찾기',exact:true}).click();await expect(page.locator('.horse-card')).toHaveCount(1);await page.getByRole('button',{name:'유키노 세레나 즐겨찾기 삭제'}).click();await expect(page.getByText('등록된 즐겨찾기가 없습니다.',{exact:false})).toBeVisible();
 await page.getByRole('link',{name:'경주·결과',exact:true}).click();await page.locator('.race-card').first().click();await page.getByRole('link',{name:'실험 모델 예측 ↗'}).click();await page.getByRole('button',{name:'출주마 예측 점수 계산 ↗'}).click();await expect(page.locator('.score-row')).toHaveCount(12);await expect(page.locator('.prediction-result')).toContainText('실제 예측 능력은 검증되지 않았습니다');
 await page.getByRole('button',{name:'로그아웃',exact:true}).click();await expect(page.getByRole('link',{name:'로그인 ↗',exact:true})).toBeVisible();await page.getByRole('link',{name:'즐겨찾기',exact:true}).click();await expect(page.getByRole('heading',{name:'다시 만나 반갑습니다'})).toBeVisible();
});
test('mobile pages fit viewport and pedigree can scroll',async({page})=>{
 await page.setViewportSize({width:375,height:812});
 for(const path of ['/','/horses','/horses/40','/horses/40/pedigree','/races','/races/1','/login']){
  await page.goto(path);await expect(page.locator('h1')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
 }
 await page.goto('/');await page.screenshot({path:'../.runtime/home-mobile.png',fullPage:true});
});

test('network failures display a Korean recovery message',async({page})=>{
 await page.route('**/api/horses?**',route=>route.abort('failed'));
 await page.goto('/horses');
 await expect(page.getByRole('alert')).toContainText('네트워크 상태를 확인');
});
