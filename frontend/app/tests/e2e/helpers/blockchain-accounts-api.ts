import type { APIRequestContext } from '@playwright/test';
import { backendUrl } from '../../../playwright.config';
import { waitForAsyncQuery } from './api';

/**
 * Tracks a blockchain account via API, waiting for the balance query it starts.
 *
 * Adding an account here rather than seeding it into the database keeps it out of the fetch lane
 * that runs at login, whose transaction query outlives the test timeout for any address with a
 * history worth speaking of.
 */
export async function apiAddBlockchainAccount(
  request: APIRequestContext,
  address: string,
  blockchain: string = 'eth',
): Promise<void> {
  const response = await request.put(`${backendUrl}/api/1/blockchains/${blockchain}/accounts`, {
    failOnStatusCode: false,
    data: {
      accounts: [{ address }],
      async_query: true,
    },
  });

  if (!response.ok()) {
    throw new Error(`Failed to track ${address} on ${blockchain}: ${response.status()} ${await response.text()}`);
  }

  const body = await response.json();

  if (body.result?.task_id) {
    await waitForAsyncQuery(request, body.result.task_id);
  }
}
