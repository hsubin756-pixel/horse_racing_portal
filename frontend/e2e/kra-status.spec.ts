import {test,expect} from '@playwright/test';

test('administrator status view separates task and race counts, supports refresh and mobile',async({page})=>{
 let reads=0;
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  let body:unknown=[];
  if(path==='/api/auth/login')body={nickname:'화면 검증 관리자',expiresIn:3600,token:'fixture'};
  if(path==='/api/admin/access')body={admin:true};
  if(path==='/api/admin/kra-status'){
   reads++;body={database:{races:100,voidRaces:1,firstDate:'2026-07-26',lastDate:'2026-10-25',lastImportedAt:'2026-10-28T01:00:00Z'},unreadableFiles:0,limited:false,note:'가상 진행표 검증',
    jobs:[{id:'20260726-20261025-123',updatedAt:'2026-10-28T10:00:00+09:00',tasks:276,siteCompleted:269,trainingCompleted:276,importedRaces:99,heldRaces:56,calls:602,
     issues:[{task:'1:20260824',race:'1',reason:'ord: 착순 미제공'}]}]};
  }
  await route.fulfill({json:body});
 });
 await page.goto('/login');await page.getByLabel('이메일',{exact:true}).fill('fixture@example.test');
 await page.getByLabel('비밀번호',{exact:true}).fill('fixture-password');await page.getByRole('button',{name:'로그인 ↗'}).click();
 await page.getByRole('link',{name:'자료 관리',exact:true}).click();
 const status=page.locator('.kra-status');await expect(status).toContainText('사이트 완료 269개');
 await expect(status).toContainText('보류 경주 56개');
 await status.getByText('보류·실패 사유 1건').click();await expect(status).toContainText('20260824 서울 1R');
 const before=reads;await status.getByRole('button',{name:'수집 상태 새로고침'}).click();await expect.poll(()=>reads).toBeGreaterThan(before);
 await page.setViewportSize({width:375,height:812});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
});
