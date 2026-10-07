import assert from 'node:assert/strict'
import { test } from 'node:test'

import { clearInvestmentHistory, deleteInvestmentActivity } from '../src/features/investments/api.ts'

test('deleting an activity targets its selected account and accepts an empty response', async (context) => {
  context.mock.method(globalThis, 'fetch', async (input: string, options: RequestInit) => {
    assert.equal(input, '/api/accounts/12/investment-activities/34')
    assert.equal(options.method, 'DELETE')
    return new Response(null, { status: 204 })
  })
  await deleteInvestmentActivity(12, 34)
})

test('clearing history targets only the selected account', async (context) => {
  context.mock.method(globalThis, 'fetch', async (input: string, options: RequestInit) => {
    assert.equal(input, '/api/accounts/12/investments')
    assert.equal(options.method, 'DELETE')
    return new Response(null, { status: 204 })
  })
  await clearInvestmentHistory(12)
})

test('dependent history gives useful feedback without displaying server details', async (context) => {
  context.mock.method(globalThis, 'fetch', async () => Response.json({ detail: 'PRIVATE SERVER DETAIL' }, { status: 409 }))
  await assert.rejects(deleteInvestmentActivity(12, 34), (error: Error) => {
    assert.ok(error.message.includes('needed by later trades or share adjustments'))
    assert.ok(!error.message.includes('PRIVATE SERVER DETAIL'))
    return true
  })
})

test('a failed deletion does not report success or expose server details', async (context) => {
  context.mock.method(globalThis, 'fetch', async () => Response.json({ detail: 'PRIVATE SERVER DETAIL' }, { status: 500 }))
  await assert.rejects(deleteInvestmentActivity(12, 34), { message: 'Could not delete the activity. Reload the page and try again.' })
})

test('a network failure leaves deletion unconfirmed', async (context) => {
  context.mock.method(globalThis, 'fetch', async () => { throw new TypeError('PRIVATE NETWORK DETAIL') })
  await assert.rejects(deleteInvestmentActivity(12, 34), { message: 'Could not confirm deletion. Reload the page before trying again.' })
})

test('a failed reset does not report success', async (context) => {
  context.mock.method(globalThis, 'fetch', async () => new Response(null, { status: 500 }))
  await assert.rejects(clearInvestmentHistory(12), { message: 'Could not clear investment history. Reload the page and try again.' })
})
