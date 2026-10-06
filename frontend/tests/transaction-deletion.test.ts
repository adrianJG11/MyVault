import assert from 'node:assert/strict'
import { test } from 'node:test'

import { clearTransactionHistory, deleteTransaction } from '../src/features/transactions/api.ts'

test('deleting a transaction targets its account and accepts an empty response', async (context) => {
  context.mock.method(globalThis, 'fetch', async (input: string, options: RequestInit) => {
    assert.equal(input, '/api/accounts/12/transactions/34')
    assert.equal(options.method, 'DELETE')
    return new Response(null, { status: 204 })
  })
  await deleteTransaction(12, 34)
})

test('clearing bank history targets only bank transactions in the selected account', async (context) => {
  context.mock.method(globalThis, 'fetch', async (input: string, options: RequestInit) => {
    assert.equal(input, '/api/accounts/12/transactions')
    assert.equal(options.method, 'DELETE')
    return new Response(null, { status: 204 })
  })
  await clearTransactionHistory(12)
})

test('a bank deletion failure does not expose server details', async (context) => {
  context.mock.method(globalThis, 'fetch', async () => Response.json({ detail: 'PRIVATE SERVER DETAIL' }, { status: 500 }))
  await assert.rejects(deleteTransaction(12, 34), { message: 'Could not delete the transaction. Reload the page and try again.' })
})

test('a bank reset network failure asks the user to reload before retrying', async (context) => {
  context.mock.method(globalThis, 'fetch', async () => { throw new TypeError('PRIVATE NETWORK DETAIL') })
  await assert.rejects(clearTransactionHistory(12), { message: 'Could not confirm the reset. Reload the page before trying again.' })
})
