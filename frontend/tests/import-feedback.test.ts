import assert from 'node:assert/strict'
import { test } from 'node:test'

import { importIbercajaTransactions } from '../src/features/transactions/api.ts'

const file = new File(['synthetic workbook'], 'ibercaja.xlsx')

test('an import returns both the added and skipped counts', async (context) => {
  context.mock.method(globalThis, 'fetch', async () =>
    Response.json({ imported: 1, skipped: 2 }, { status: 201 }),
  )

  assert.deepEqual(await importIbercajaTransactions(1, file), {
    imported: 1,
    skipped: 2,
  })
})

for (const [status, message] of [
  [422, 'This file is not a valid Ibercaja XLSX export.'],
  [404, 'The selected account is no longer available.'],
  [413, 'The file is too large.'],
  [500, 'The server could not complete the import.'],
] as const) {
  test(`an HTTP ${status} response gives a safe, useful message`, async (context) => {
    context.mock.method(globalThis, 'fetch', async () =>
      Response.json({ detail: 'PRIVATE SERVER DETAIL' }, { status }),
    )

    await assert.rejects(importIbercajaTransactions(1, file), (error: Error) => {
      assert.ok(error.message.startsWith(message))
      assert.ok(!error.message.includes('PRIVATE SERVER DETAIL'))
      return true
    })
  })
}

test('a network failure explains that the import is unconfirmed', async (context) => {
  context.mock.method(globalThis, 'fetch', async () => {
    throw new TypeError('PRIVATE NETWORK DETAIL')
  })

  await assert.rejects(importIbercajaTransactions(1, file), {
    message:
      'Could not confirm the import. Check your connection and reload the page before trying again.',
  })
})

test('an unreadable success response asks the user to check before retrying', async (context) => {
  context.mock.method(globalThis, 'fetch', async () =>
    new Response('PRIVATE INVALID RESPONSE', { status: 201 }),
  )

  await assert.rejects(importIbercajaTransactions(1, file), {
    message:
      'Could not read the import result. Reload the page to check your transactions before trying again.',
  })
})
