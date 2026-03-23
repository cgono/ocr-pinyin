import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { test } from 'vitest'

const root = path.resolve(import.meta.dirname, '../../src')


test('upload form contains take photo and upload affordances', async () => {
  const source = await readFile(path.join(root, 'features/process/components/UploadForm.jsx'), 'utf8')

  assert.match(source, /Take Photo/)
  assert.match(source, /Upload image/)
  assert.match(source, /submit/i)
})


test('api client posts to v1 process endpoint', async () => {
  const source = await readFile(path.join(root, 'lib/api-client.js'), 'utf8')

  assert.match(source, /\/v1\/process/)
  assert.match(source, /method:\s*'POST'/)
})
