#!/usr/bin/env node
/*
 * validate_bliss.mjs — run each exported word through bliss-svg-builder
 * (hlridge, MPL-2.0) as a structural oracle. A word is invalid when the
 * builder reports warnings (UNKNOWN_CODE, ...) or renders zero elements.
 *
 * Usage: node scripts/validate_bliss.mjs <words.jsonl> <failures.json>
 */
import fs from 'node:fs';
import readline from 'node:readline';
import { BlissSVGBuilder } from 'bliss-svg-builder';

const [inPath, outPath] = process.argv.slice(2);
const fails = [];
let total = 0;

const rl = readline.createInterface({ input: fs.createReadStream(inPath) });
for await (const line of rl) {
  if (!line.trim()) continue;
  const w = JSON.parse(line);
  total++;
  if (w.unmapped > 0) {
    fails.push({ ...w, warning_codes: ['UNREVERSIBLE_CODEPOINT'] });
    continue;
  }
  try {
    const b = new BlissSVGBuilder(w.dsl);
    const codes = (b.warnings || []).map(x => x.code).filter(c => c !== undefined);
    if (codes.length || b.elementCount < 1) {
      fails.push({ ...w, warning_codes: codes.length ? codes : ['NO_ELEMENTS'] });
    }
  } catch (e) {
    fails.push({ ...w, warning_codes: ['THREW', e.message.slice(0, 60)] });
  }
}

fs.writeFileSync(outPath, JSON.stringify(fails, null, 1));
console.log(`validated ${total} words -> ${fails.length} invalid`);
