// Capture screenshots of the Euresis Thought Space.
// usage: node scripts/screenshot.mjs [space/space.html] [outdir]
import { createRequire } from "module";
import path from "path";
import fs from "fs";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const file = path.resolve(process.argv[2] || "space/space.html");
const out = path.resolve(process.argv[3] || "space/screenshots");
fs.mkdirSync(out, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1.5 });
await page.goto("file://" + file);
await page.waitForFunction(() => window.EURESIS);

async function shot(name, fn, arg) {
  await page.evaluate(([f, a]) => { window.EURESIS.select(null, false); (new Function("a", f))(a); }, [fn, arg]);
  await page.waitForTimeout(250);
  await page.screenshot({ path: path.join(out, name) });
  console.log("saved", path.join(out, name));
}
const focus = `const E = window.EURESIS; const n = E.find(a.q).filter(n => !a.k || n.k === a.k)[0];
  if (!n) return; E.flyTo(n.x + (a.dx || 0), n.y + (a.dy || 0), a.z, 0); if (a.sel) E.select(n.id, false);`;

await shot("01-overview.png", `const E = window.EURESIS; const xs = E.nodes.map(n => n.x), ys = E.nodes.map(n => n.y);
  const z = Math.min(1600 / (Math.max(...xs) - Math.min(...xs) + 1400), 1000 / (Math.max(...ys) - Math.min(...ys) + 1400));
  E.flyTo((Math.max(...xs) + Math.min(...xs)) / 2, (Math.max(...ys) + Math.min(...ys)) / 2, z, 0);`);
await shot("02-core-constants-and-scales.png", `window.EURESIS.flyTo(0, 0, 0.22, 0);`);
await shot("03-planck-scale-discovery.png", focus, { q: "Planck scales: length", k: "scale", z: 0.55, sel: true, dx: 250 });
await shot("04-gravity-electromagnetism-analogy.png", focus, { q: "Newton's law of universal gravitation ≅ Coulomb", k: "analogy", z: 0.42, sel: true, dx: 250 });
await shot("05-verified-prediction.png", focus, { q: "Earth: escape speed", k: "prediction", z: 0.5, sel: true, dx: 250 });
await shot("06-mechanics-up-close.png", focus, { q: "Mechanics", k: "domain", z: 0.9, dx: 150, dy: 120 });
await shot("07-frontier-problems.png", focus, { q: "Quantum gravity", k: "frontier", z: 0.16, sel: true, dx: 600 });
await shot("08-hierarchy-insight.png", focus, { q: "Gravity is", k: "insight", z: 0.5, sel: true, dx: 250 });
await browser.close();
