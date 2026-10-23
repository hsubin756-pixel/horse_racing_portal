import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';

test('sectional positions, running style, trend selection, payouts, calendar and people',async({page})=>{
 await page.goto('/horses/22');await expect(page.locator('.style-summary')).toContainText('선행');await expect(page.locator('.style-summary')).toContainText('7개');
 await page.getByRole('button',{name:'2025-01-15 3위 구간 기록 보기'}).click();
 await expect(page.getByRole('region',{name:'구간별 통과 기록'})).toContainText('96.96초');
 await expect(page.getByRole('region',{name:'구간별 통과 기록'}).locator('tbody tr')).toHaveCount(4);
 await page.screenshot({path:'../.runtime/running-style-desktop.png',fullPage:true});
 await page.goto('/horses/33');await expect(page.locator('.style-summary')).toContainText('판단 보류');await expect(page.getByText('구간 기록이 없습니다. 기록을 추정하여 채우지 않습니다.')).toBeVisible();
 await page.goto('/races/1');await expect(page.locator('.race-facts')).toContainText('15:30');await expect(page.getByRole('region',{name:'조합별 환급표'})).toContainText('13,870엔');
 await page.getByRole('combobox',{name:'기록을 볼 출주마',exact:true}).selectOption('33');await expect(page.getByText('구간 기록이 없습니다. 기록을 추정하여 채우지 않습니다.')).toBeVisible();
 await page.goto('/calendar?month=2025-01');await expect(page.locator('.calendar-day.has-races')).toHaveCount(1);await page.locator('.calendar-day.has-races a').click();await expect(page.locator('h1')).toHaveText('가상 사쿠라 컵');
 await page.goto('/people?kind=JOCKEY&year=2025');await expect(page.getByRole('region',{name:'인물 성적 순위'}).locator('tbody tr')).toHaveCount(12);await page.getByRole('region',{name:'인물 성적 순위'}).locator('tbody a').first().click();await expect(page.locator('.facts')).toContainText('7회');
 await page.setViewportSize({width:375,height:812});
 for(const path of ['/horses/22','/races/1','/calendar?month=2025-01','/people?kind=TRAINER']){await page.goto(path);await expect(page.locator('h1')).toBeVisible();await page.waitForLoadState('networkidle');expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),path).toBeTruthy();}
 await page.goto('/horses/22');await expect(page.locator('.style-summary')).toContainText('선행');await page.screenshot({path:'../.runtime/running-style-mobile.png',fullPage:true});
});

test('private notes, inbox and non-admin access',async({page,request})=>{
 const email='notes-browser-'+Date.now()+'@example.test',password='Browser-notes-12345';
 expect((await request.post('http://127.0.0.1:8080/api/auth/register',{data:{email,password,nickname:'메모 회원'}})).status()).toBe(201);
 await page.goto('/notes');await expect(page.locator('h1')).toHaveText('다시 만나 반갑습니다');
 await page.getByLabel('이메일',{exact:true}).fill(email);await page.getByLabel('비밀번호',{exact:true}).fill(password);await page.getByRole('button',{name:'로그인 ↗'}).click();await expect(page.locator('h1')).toHaveText('나의 즐겨찾기');
 await page.getByRole('link',{name:'경주마',exact:true}).click();await page.getByLabel('경주마 이름',{exact:true}).fill('유키노');await page.getByRole('button',{name:'검색 ↗'}).click();await expect(page.locator('.horse-card')).toHaveCount(1);await page.locator('.horse-card').click();
 await page.getByRole('link',{name:'개인 메모 작성 ↗'}).click();await page.getByLabel('관찰 내용').fill('초반 선두, 다음 경주 관찰 <script>');await page.getByLabel('태그',{exact:true}).fill('선행,관찰');await page.getByRole('button',{name:'메모 저장'}).click();
 await expect(page.locator('.note-list article')).toHaveCount(1);await expect(page.locator('.note-body')).toContainText('<script>');
 await page.locator('.note-list').getByRole('button',{name:'수정',exact:true}).click();await page.getByLabel('관찰 내용').fill('수정한 관찰 기록');await page.getByRole('button',{name:'메모 저장'}).click();await expect(page.locator('.note-body')).toHaveText('수정한 관찰 기록');
 await page.setViewportSize({width:375,height:812});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
 await page.locator('.note-list').getByRole('button',{name:'삭제',exact:true}).click();await expect(page.locator('.note-list article')).toHaveCount(0);
 await page.getByRole('link',{name:'알림함',exact:true}).click();await expect(page.getByRole('status')).toContainText('읽지 않은 알림 0개');await page.getByRole('button',{name:'알림 갱신'}).click();await expect(page.getByText('새 알림이 없습니다.')).toBeVisible();
 await page.getByRole('link',{name:'자료 관리',exact:true}).click();await expect(page.getByRole('alert')).toContainText('관리자 권한');
});

test('admin CSV preview and save, edit with audit, mobile form',async({page,request})=>{
 const email='admin-browser-'+Date.now()+'@example.test',password='Browser-admin-12345';let personId:number|undefined;
 expect((await request.post('http://127.0.0.1:8080/api/auth/register',{data:{email,password,nickname:'검증 관리자'}})).status()).toBe(201);
 execFileSync('python3',['../scripts/admin.py',email]);
 try{
  await page.goto('/login');await page.getByLabel('이메일',{exact:true}).fill(email);await page.getByLabel('비밀번호',{exact:true}).fill(password);await page.getByRole('button',{name:'로그인 ↗'}).click();await expect(page.locator('h1')).toHaveText('나의 즐겨찾기');
  await page.getByRole('link',{name:'자료 관리',exact:true}).click();await expect(page.locator('.admin-form')).toBeVisible();
  await page.getByRole('combobox',{name:'자료 종류',exact:true}).selectOption('people');
  await page.getByText('CSV로 여러 자료 가져오기 · 최대 100행 / 200KB',{exact:true}).click();
  await page.getByLabel('CSV 내용',{exact:true}).fill('kind,name,biography,source\nTRAINER,브라우저 검증 조교사,"가상 소개, 메모",synthetic_test\n');
  await page.getByRole('button',{name:'CSV 미리보기'}).click();await expect(page.getByRole('heading',{name:'입력 검사 완료 · 1행'})).toBeVisible();
  await page.getByRole('button',{name:'저장 대기 목록에 담기'}).click();
  const saved=page.waitForResponse(r=>r.url().endsWith('/api/admin/changes'));
  await page.getByRole('button',{name:'전체 변경 저장'}).click();personId=(await (await saved).json()).batches[0].ids[0];
  await expect(page.getByRole('status')).toContainText('변경 묶음을 저장했습니다');
  await page.locator('.admin-records').getByRole('button',{name:new RegExp('^#'+personId+' ·')}).click();
  await page.getByRole('textbox',{name:'소개',exact:true}).fill('수정한 가상 소개');await page.getByRole('button',{name:'입력 미리보기'}).click();await page.getByRole('button',{name:'저장 대기 목록에 담기'}).click();await page.getByRole('button',{name:'전체 변경 저장'}).click();await expect(page.getByRole('status')).toContainText('변경 묶음을 저장했습니다');
  await page.getByText('최근 변경 이력 100건',{exact:true}).click();await expect(page.locator('section > details').last()).toContainText('기수·조교사 #'+personId);
  await page.setViewportSize({width:375,height:812});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
  await page.screenshot({path:'../.runtime/admin-mobile.png',fullPage:true});
 }finally{
  execFileSync('python3',['../scripts/admin.py',email,'--revoke']);
  if(personId)execFileSync('python3',['-c',"import sys;sys.path.insert(0,'../scripts');from backup import mysql;mysql('DELETE FROM person WHERE id='+str(int(sys.argv[1]))+';','keiba')",String(personId)]);
 }
});
