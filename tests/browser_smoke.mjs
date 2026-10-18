// Optional browser verification. Run from the repository root with Playwright installed.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.BUDGET_PLAYWRIGHT_MODULE?path.resolve(process.env.BUDGET_PLAYWRIGHT_MODULE):'playwright');
const browser=await chromium.launch({headless:true}),root=process.cwd();
const assert=(value,message)=>{if(!value)throw new Error(message);};
try{
 const page=await browser.newPage({viewport:{width:1200,height:1100},colorScheme:'light'}),errors=[],requests=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url());});
 const original=await fs.readFile('examples/synthetic/dashboard.html','utf8');
 await page.goto(pathToFileURL(path.join(root,'examples/synthetic/dashboard.html')).href);
 assert((await page.locator('#total').textContent()).includes('1,350.00'),'Initial total');
 await page.selectOption('#month','2030-02');assert((await page.locator('#total').textContent()).includes('250.00'),'Month filter');
 await page.selectOption('#month','all');await page.selectOption('#account','everyday-card');assert((await page.locator('#total').textContent()).includes('1,050.00'),'Account filter');
 await page.selectOption('#account','all');await page.selectOption('#emi','no');assert((await page.locator('#total').textContent()).includes('1,150.00'),'EMI toggle');
 await page.selectOption('#emi','yes');await page.selectOption('#group','payee');await page.getByRole('button',{name:'Demo store',exact:true}).click();
 assert(await page.locator('#transactions tr').count()===3,'Drilldown');
 await page.locator('#clear').click();await page.selectOption('#mode','bar');assert(await page.locator('#chart rect').count()===4,'Bars');
 await page.selectOption('#group','account');await page.selectOption('#mode','pie');
 await fs.mkdir('data/screenshots',{recursive:true});await page.screenshot({path:'data/screenshots/dashboard-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 assert(!await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth),'Mobile overflow');
 await page.screenshot({path:'data/screenshots/dashboard-mobile.png',fullPage:true});await page.emulateMedia({colorScheme:'dark'});await page.screenshot({path:'data/screenshots/dashboard-dark.png',fullPage:true});
 const marker=/<script id="budget-data" type="application\/json">([\s\S]*?)<\/script>/;
 const initial=JSON.parse(original.match(marker)[1]);
 async function variant(payload){
  const encoded=JSON.stringify(payload).replace(/</g,'\\u003c');
  const html=original.replace(marker,'<script id="budget-data" type="application/json">'+encoded+'</script>');
  const file=path.join(root,'data','synthetic-browser-variant.html');await fs.writeFile(file,html);await page.goto(pathToFileURL(file).href);
 }
 const mixed=structuredClone(initial);mixed.locale='de-DE';mixed.currencies.EUR={digits:2};mixed.currencies.JPY={digits:0};mixed.currencies.KWD={digits:3};
 for(const [code,amount]of [['EUR','10005'],['JPY','12345'],['KWD','123456']]){
  mixed.accounts.push({id:'synthetic-'+code,name:'Synthetic '+code,currency:code});
  mixed.rows.push({id:'synthetic-'+code,date:'2030-01-10',currency:code,account:'synthetic-'+code,payee:'Synthetic vendor',description:'Entirely synthetic browser test',expense:amount,emi:'0'});
 }
 await variant(mixed);
 for(const [code,text]of [['EUR','100,05'],['JPY','12.345'],['KWD','123,456']]){await page.selectOption('#currency',code);assert((await page.locator('#total').textContent()).includes(text),'Currency precision/locale: '+code);}
 const large=structuredClone(initial);large.accounts=[large.accounts[0]];large.rows=[{...large.rows[0],expense:String(BigInt('123456789')*(10n**9n)+BigInt('123456789')),emi:'0'}];
 await variant(large);assert((await page.locator('#total').textContent()).includes('1,234,567,891,234,567.89'),'Exact large minor-unit formatting');
 const negative=structuredClone(initial);negative.rows.push({...negative.rows[0],id:'negative-demo',payee:'Negative demo',expense:'-20000',emi:'0'});
 await variant(negative);await page.selectOption('#group','payee');
 assert((await page.locator('#hint').textContent()).includes('signed bars'),'Negative groups must not enter pie');
 assert(await page.locator('#chart rect').count()>0,'Negative groups shown as bars');
 assert(errors.length===0,'JavaScript errors: '+errors.join('; '));assert(requests.length===0,'Unexpected network request');
 console.log('Browser checks passed: filters, drilldown, installments, mobile/dark layout, currency separation, EUR/JPY/KWD precision, locale, large exact amounts, negative bars, no network.');
}finally{await browser.close();}
