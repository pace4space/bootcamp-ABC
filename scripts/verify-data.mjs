#!/usr/bin/env node
// Validates src/data/*.json referential integrity and that all source file paths exist.
// Run: node scripts/verify-data.mjs

import { readFileSync, existsSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

const candidates = JSON.parse(readFileSync(`${root}/src/data/candidates.json`, 'utf8'))
const positions  = JSON.parse(readFileSync(`${root}/src/data/positions.json`, 'utf8'))
const apps       = JSON.parse(readFileSync(`${root}/src/data/applications.json`, 'utf8'))

let errors = 0

function fail(msg) {
  console.error(`  FAIL  ${msg}`)
  errors++
}
function ok(msg) {
  console.log(`  OK    ${msg}`)
}

// 1. No duplicate ids
const cvIds  = candidates.map(c => c.id)
const jobIds = positions.map(p => p.id)
const appIds = apps.map(a => a.id)

const dupCv  = cvIds.filter((id, i) => cvIds.indexOf(id) !== i)
const dupJob = jobIds.filter((id, i) => jobIds.indexOf(id) !== i)
const dupApp = appIds.filter((id, i) => appIds.indexOf(id) !== i)

dupCv.length  ? fail(`Duplicate candidate ids: ${dupCv}`)  : ok(`No duplicate candidate ids (${cvIds.length} total)`)
dupJob.length ? fail(`Duplicate position ids: ${dupJob}`)  : ok(`No duplicate position ids (${jobIds.length} total)`)
dupApp.length ? fail(`Duplicate application ids: ${dupApp}`) : ok(`No duplicate application ids (${appIds.length} total)`)

// 2. Application FK integrity
const cvSet  = new Set(cvIds)
const jobSet = new Set(jobIds)

for (const app of apps) {
  if (!cvSet.has(app.candidateId))  fail(`app ${app.id}: unknown candidateId "${app.candidateId}"`)
  if (!jobSet.has(app.positionId))  fail(`app ${app.id}: unknown positionId "${app.positionId}"`)
}
const badFks = apps.filter(a => !cvSet.has(a.candidateId) || !jobSet.has(a.positionId))
if (badFks.length === 0) ok(`All application FKs resolve`)

// 3. Source CV files exist
for (const c of candidates) {
  const path = `${root}/public${c.sourceCv.path}`
  existsSync(path) ? ok(`${c.id} → ${c.sourceCv.path}`) : fail(`${c.id}: missing file ${c.sourceCv.path}`)
}

// 4. Source job email files exist
for (const p of positions) {
  const path = `${root}/public${p.sourceDocument.path}`
  existsSync(path) ? ok(`${p.id} → ${p.sourceDocument.path}`) : fail(`${p.id}: missing file ${p.sourceDocument.path}`)
}

// 5. Status values are valid
for (const c of candidates) {
  if (!['Active', 'Archived'].includes(c.status)) fail(`${c.id}: invalid status "${c.status}"`)
}
for (const p of positions) {
  if (!['Open', 'Closed'].includes(p.status)) fail(`${p.id}: invalid status "${p.status}"`)
}
for (const a of apps) {
  if (a.status !== null && !['Waiting', 'Rejected', 'Screening', 'Offer', 'Hired'].includes(a.status)) {
    fail(`${a.id}: invalid status "${a.status}"`)
  }
}
ok(`All status values valid`)

// Summary
console.log('')
if (errors === 0) {
  console.log(`✓ verify-data passed — ${candidates.length} candidates, ${positions.length} positions, ${apps.length} applications`)
} else {
  console.log(`✗ verify-data failed with ${errors} error(s)`)
  process.exit(1)
}
