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

test('popularity, win odds, sorting and unavailable snapshots',async({page})=>{
 await page.goto('/races/1');
 await expect(page.getByRole('columnheader',{name:'인기',exact:true})).toBeVisible();
 await expect(page.getByRole('columnheader',{name:'단승 배당',exact:true})).toBeVisible();
 await expect(page.locator('.odds-note')).toContainText('가상 샘플');
 await expect(page.locator('.odds-value strong')).toHaveCount(12);
 await expect(page.locator('.odds-value time').first()).toContainText('KST 기준');
 await page.getByLabel('출주마 정렬').selectOption('popularityRank');
 await expect(page.locator('tbody tr').first().locator('.popularity-value')).toHaveText('1위');
 await expect(page.locator('tbody tr').first().locator('.odds-value strong')).toHaveText('2.4배');
 await page.getByLabel('출주마 정렬').selectOption('winOdds');
 const odds=await page.locator('.odds-value strong').allTextContents();
 const values=odds.map(value=>parseFloat(value));expect(values).toEqual([...values].sort((a,b)=>a-b));
 await page.getByLabel('출주마 정렬').selectOption('number');
 await expect(page.locator('tbody tr').first().locator('td').first()).toHaveText('01');
 await page.getByLabel('출주마 정렬').selectOption('finishPosition');
 await expect(page.locator('tbody tr').first().locator('.rank')).toHaveText('1');
 await page.goto('/horses/22');await expect(page.locator('.odds-value strong')).toHaveCount(7);
 await page.goto('/races/8');
 await expect(page.locator('tbody tr')).toHaveCount(12);
 await page.getByLabel('출주마 정렬').selectOption('winOdds');
 await expect(page.locator('tbody tr').last().locator('.odds-value')).toHaveText('미제공');
 await expect(page.locator('tbody tr').last().locator('.popularity-value')).toHaveText('미제공');
 await page.setViewportSize({width:375,height:812});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
 const region=page.getByRole('region',{name:'출주마 및 배당 표'});
 await region.evaluate(element=>element.scrollLeft=element.scrollWidth);
 await expect(page.getByRole('columnheader',{name:'착순',exact:true})).toBeInViewport();
});

test('compare horses and filter horse and jockey statistics',async({page})=>{
 await page.goto('/compare?ids=22,32');
 await expect(page.locator('.comparison-card')).toHaveCount(2);
 const first=page.locator('.comparison-card').first();
 const starts=first.locator('.stat-metrics > div').filter({hasText:'출전'}).locator('dd');
 await expect(starts).toHaveText('7회');
 await expect(first.locator('.recent-starts li')).toHaveCount(5);
 await page.screenshot({path:'../.runtime/comparison-desktop.png',fullPage:true});
 await page.getByLabel('거리(m)',{exact:true}).fill('1600');
 await page.getByLabel('조회 시작일').fill('2025-03-15');
 await page.getByLabel('조회 종료일').fill('2025-05-15');
 await page.getByRole('button',{name:'조건 적용',exact:true}).click();
 await expect(starts).toHaveText('2회');
 await page.getByRole('button',{name:'조건 초기화'}).click();await expect(starts).toHaveText('7회');
 await page.getByLabel('비교할 말 이름 검색').fill('아오이');await page.getByRole('button',{name:'말 검색',exact:true}).click();
 await page.getByRole('combobox',{name:'비교할 경주마',exact:true}).selectOption('1');
 await expect(page.locator('.comparison-card')).toHaveCount(3);
 await expect(page.locator('.comparison-card').last()).toContainText('조건에 맞는 완료 전적이 없습니다.');
 await page.getByRole('button',{name:'나나이로 루트 비교에서 제외'}).click();await expect(page.locator('.comparison-card')).toHaveCount(2);
 await page.goto('/statistics?horse=22');await expect(page.getByRole('heading',{name:'유키노 세레나의 성적'})).toBeVisible();
 await page.getByRole('combobox',{name:'성적을 볼 기수',exact:true}).selectOption('가상 기수 1');
 await expect(page.getByRole('heading',{name:'가상 기수 1의 성적'})).toBeVisible();
 await page.getByLabel('거리(m)',{exact:true}).fill('2000');await page.getByRole('button',{name:'조건 적용',exact:true}).click();
 await expect(page.locator('.stats-result .stat-metrics > div').filter({hasText:'출전'}).locator('dd')).toHaveText('3회');
 await page.getByRole('combobox',{name:'주로',exact:true}).selectOption('더트');await page.getByRole('button',{name:'조건 적용',exact:true}).click();
 await expect(page.getByText('조건에 맞는 완료 전적이 없습니다.',{exact:true})).toBeVisible();
 await page.setViewportSize({width:375,height:812});
 for(const path of ['/compare?ids=22,32,1,33','/statistics?horse=22','/statistics?jockey='+encodeURIComponent('가상 기수 1')]){
  await page.goto(path);await expect(page.locator('.stat-metrics').first()).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
 }
});

test('save races and merge favorite-horse schedules without duplicates',async({page,request})=>{
 const email='schedule-'+Date.now()+'@example.test',password='Schedule-test-12345';
 const registration=await request.post('http://127.0.0.1:8080/api/auth/register',{data:{email,password,nickname:'일정 회원'}});
 expect(registration.status()).toBe(201);
 await page.goto('/watchlist');await expect(page.getByRole('heading',{name:'다시 만나 반갑습니다'})).toBeVisible();
 await page.getByLabel('이메일',{exact:true}).fill(email);await page.getByLabel('비밀번호',{exact:true}).fill(password);await page.getByRole('button',{name:'로그인 ↗'}).click();
 await expect(page.getByRole('heading',{name:'나의 즐겨찾기'})).toBeVisible();
 await page.getByRole('link',{name:'경주·결과',exact:true}).click();await page.locator('.race-card').filter({hasText:'가상 미래 컵'}).click();await page.getByRole('button',{name:'☆ 관심 경주 저장'}).click();
 await expect(page.getByRole('status')).toContainText('관심 경주에 저장했습니다.');
 await page.getByRole('button',{name:'☆ 관심 경주 저장'}).click();await expect(page.getByRole('status')).toContainText('이미 관심 경주');
 await page.getByRole('link',{name:'유키노 세레나 ↗',exact:true}).click();await page.getByRole('button',{name:'☆ 즐겨찾기 추가'}).click();await expect(page.getByRole('status')).toContainText('추가했습니다');
 const loaded=page.waitForResponse(response=>response.url().includes('/api/my-schedule?'));
 await page.getByRole('link',{name:'관심 일정',exact:true}).click();
 const schedule=await (await loaded).json();const active=schedule.asOfDate<='2026-11-01'&&schedule.through>='2026-11-01';
 await expect(page.locator('.saved-race')).toHaveCount(1);
 if(active){await expect(page.locator('.schedule-list > li')).toHaveCount(1);await expect(page.locator('.scheduled-horses')).toContainText('유키노 세레나');}
 await page.setViewportSize({width:375,height:812});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
 await page.screenshot({path:'../.runtime/watchlist-mobile.png',fullPage:true});
 await page.locator('.saved-race').getByRole('button',{name:/관심 경주 삭제/}).click();await expect(page.locator('.saved-race')).toHaveCount(0);
 if(active)await expect(page.locator('.schedule-list > li')).toHaveCount(1);
 await page.getByRole('link',{name:'즐겨찾기 경주마 관리 ↗'}).click();await page.getByRole('button',{name:'유키노 세레나 즐겨찾기 삭제'}).click();
 await expect(page.locator('.horse-card')).toHaveCount(0);
 await page.getByRole('link',{name:'관심 일정',exact:true}).click();
 await expect(page.getByText('앞으로 90일 동안 관심 대상의 예정 경주가 없습니다.',{exact:true})).toBeVisible();
});
