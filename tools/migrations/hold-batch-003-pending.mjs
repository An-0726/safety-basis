import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const BATCH_DIR = path.join(ROOT, 'content', 'batches');
const targetFiles = [
  '2026-09-08-batch-003a.json',
  '2026-09-08-batch-003b.json',
  '2026-09-08-batch-003c.json',
  '2026-09-08-batch-003d.json',
  '2026-09-08-batch-003e.json'
];
const candidateLawIds = new Set(['L016','L017','L018','L019','L020','L021','L024','L026','L028','L029']);

for (const name of targetFiles) {
  const file = path.join(BATCH_DIR, name);
  const batch = JSON.parse(await fs.readFile(file, 'utf8'));
  for (const hazard of batch.hazards ?? []) {
    if (/^H0(3[3-9]|[4-7][0-9]|8[01])$/.test(hazard.id)) {
      hazard.status = '待核验';
      hazard.checked = '';
      hazard.note = `${hazard.note || ''}\n\n交接状态：本条已完成结构化修订草稿和候选依据定位，但尚未完成逐条官方原文终审；核验完成前不得进入公开运行库。`.trim();
    }
  }
  for (const clause of batch.clauses ?? []) {
    if (/^C0(3[2-9]|[4-7][0-9]|80)$/.test(clause.id)) {
      clause.status = '待核验';
      clause.checked = '';
    }
  }
  for (const law of batch.laws ?? []) {
    if (candidateLawIds.has(law.id)) {
      law.status = '待核验';
      law.checked = '';
    }
  }
  for (const link of batch.links ?? []) {
    if (/^H0(3[3-9]|[4-7][0-9]|8[01])$/.test(link.hazardId)) {
      link.role = '候选直接依据';
      link.priority = 1;
    }
  }
  if (batch.ingestionSummary) {
    batch.ingestionSummary.newPendingHazards = (batch.hazards ?? []).filter(x => x.status === '待核验').length;
    batch.ingestionSummary.verifiedHazards = 0;
    batch.ingestionSummary.note = '已保存修订草稿与候选依据定位；逐条官方原文终审尚未完成，Batch 003 保持待核验且不进入公开运行库。';
  }
  await fs.writeFile(file, JSON.stringify(batch, null, 2) + '\n', 'utf8');
}

console.log('Batch 003 held in pending/unpublished state for handoff.');
