import {test,expect} from '@playwright/test';
test('compare up to four horses, sort section times and handle an empty selection',async({page})=>{
 await page.goto('/races/1');
 const area=page.getByRole('region',{name:'출주마 구간 비교',exact:true});
 await expect(area.getByRole('checkbox')).toHaveCount(12);
 const table=area.getByRole('region',{name:'출주마 구간 비교 표',exact:true});
 await expect(table.locator('tbody tr')).toHaveCount(2);
 await area.getByRole('checkbox').nth(2).check();await area.getByRole('checkbox').nth(3).check();
 await expect(area.getByRole('checkbox').nth(4)).toBeDisabled();
 await expect(table.locator('tbody tr')).toHaveCount(4);
 await area.getByLabel('비교 정렬').selectOption('last600');
 const times=await table.locator('tbody tr td:nth-child(5)').allTextContents();
 const values=times.map(t=>parseFloat(t));expect(values).toEqual([...values].sort((a,b)=>a-b));
 await page.setViewportSize({width:375,height:812});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
 for(let i=0;i<4;i++)await area.getByRole('checkbox').nth(i).uncheck();
 await expect(area.getByRole('status')).toContainText('비교할 말을 선택');
});
test('missing timing remains unavailable instead of becoming zero',async({page})=>{
 await page.route('**/api/races/8/sectionals',async route=>{
  const response=await route.fetch();const data=await response.json();
  for(const r of data){r.last600=null;r.points=[];}
  await route.fulfill({response,json:data});
 });
 await page.goto('/races/8');
 const area=page.getByRole('region',{name:'출주마 구간 비교',exact:true});
 await expect(area.getByRole('region',{name:'출주마 구간 비교 표'})).toContainText('미제공');
 await expect(area.locator('svg circle')).toHaveCount(0);
});
