// usage: node render.mjs shots.json outdir W H
// npm install playwright (and `npx playwright install chromium`, or set CHROME to a Chrome binary)
import { chromium } from 'playwright';
import fs from 'fs'; import http from 'http'; import path from 'path';
const [shotsF,outDir,W=1280,H=720]=process.argv.slice(2);
const root=path.dirname(new URL(import.meta.url).pathname);
const srv=http.createServer((q,r)=>{const f=path.join(root,decodeURIComponent(q.url.split('?')[0]));fs.readFile(f,(e,d)=>{if(e){r.writeHead(404);r.end();}else{r.writeHead(200);r.end(d);}})}).listen(0);
await new Promise(r=>srv.on('listening',r)); const port=srv.address().port;
const shots=JSON.parse(fs.readFileSync(shotsF)); fs.mkdirSync(outDir,{recursive:true});
const b=await chromium.launch({...(process.env.CHROME?{executablePath:process.env.CHROME}:{}),args:['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
const p=await b.newPage({viewport:{width:+W,height:+H}});
p.on('console',m=>console.log('page:',m.text())); p.on('pageerror',e=>console.log('err',e));
await p.goto(`http://127.0.0.1:${port}/viewer.html`);
const names=[...new Set(shots.flatMap(s=>s.parts.map(x=>x.mesh)))];
await p.evaluate(([w,h,n])=>window.init(w,h,n),[+W,+H,names]);
let i=0;
for(const s of shots){
  await p.evaluate(s=>window.draw(s),s);
  const data=await p.evaluate(()=>document.getElementById('c').toDataURL('image/png'));
  fs.writeFileSync(path.join(outDir,(s.file||String(i).padStart(5,'0')+'.png')),Buffer.from(data.split(',')[1],'base64'));
  i++; if(i%100==0) console.log(i);
}
await b.close(); srv.close(); console.log('done',i);
