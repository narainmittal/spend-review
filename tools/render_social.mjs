// Optional local rendering helper. Requires Playwright and its Chromium browser.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.BUDGET_PLAYWRIGHT_MODULE?path.resolve(process.env.BUDGET_PLAYWRIGHT_MODULE):'playwright');
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const output=path.join(root,'dist','spend-review-workflow-linkedin.png');
await fs.mkdir(path.dirname(output),{recursive:true});
try{await fs.access(output);throw new Error('Output already exists; choose a new filename or archive it before rendering again.');}
catch(error){if(error.code!=='ENOENT')throw error;}
const browser=await chromium.launch({headless:true});
try{
 const page=await browser.newPage({viewport:{width:1200,height:1500},deviceScaleFactor:1});
 await page.goto(pathToFileURL(path.join(root,'docs/assets/workflow.svg')).href);
 await page.screenshot({path:output});
 console.log('Rendered public workflow graphic:',output);
}finally{await browser.close();}
