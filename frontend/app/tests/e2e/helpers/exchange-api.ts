import type { APIRequestContext } from '@playwright/test';
import { backendUrl } from '../../../playwright.config';

export type ExchangePurgeDataType = 'all' | 'trades' | 'asset_movements' | 'other';

/**
 * Purges history events for a single exchange via the public API. Pass a
 * `dataType` to scope the purge to one bucket (trades, asset movements, or
 * everything else); the default `'all'` is the same call the UI makes when no
 * category is chosen.
 *
 * Useful in `beforeEach` to reset state between purge-by-category tests
 * without recreating the user/context.
 */
export async function apiPurgeExchangeData(
  request: APIRequestContext,
  location: string,
  dataType: ExchangePurgeDataType = 'all',
): Promise<void> {
  const response = await request.delete(`${backendUrl}/api/1/exchanges/data/${location}`, {
    params: { data_type: dataType },
  });
  if (!response.ok()) {
    throw new Error(
      `Failed to purge ${dataType} data for ${location}: ${response.status()} ${await response.text()}`,
    );
  }
}

interface SeedOptions {
  location: string;
  /** Unix timestamp in milliseconds. Each event needs a unique value. */
  timestampMs: number;
  /** Position within the parent group; needs to be unique per group. */
  sequenceIndex: number;
}

/**
 * Adds a single non-trade, non-movement history event (`entry_type=history event`)
 * tagged with the given location. Falls into the `OTHER` purge bucket.
 */
export async function apiSeedHistoryEvent(
  request: APIRequestContext,
  options: SeedOptions,
): Promise<void> {
  const payload = {
    entry_type: 'history event',
    timestamp: options.timestampMs,
    location: options.location,
    sequence_index: options.sequenceIndex,
    event_type: 'staking',
    event_subtype: 'reward',
    asset: 'ETH',
    amount: '0.1',
    group_identifier: `e2e-other-${options.timestampMs}`,
  };
  await putHistoryEvent(request, payload, 'history event');
}

/**
 * Adds a single asset movement event (`entry_type=asset movement event`) tagged
 * with the given location. Falls into the `ASSET_MOVEMENTS` purge bucket.
 */
export async function apiSeedAssetMovement(
  request: APIRequestContext,
  options: SeedOptions,
): Promise<void> {
  const payload = {
    entry_type: 'asset movement event',
    timestamp: options.timestampMs,
    location: options.location,
    event_subtype: 'receive',
    amount: '0.5',
    asset: 'ETH',
    unique_id: `e2e-movement-${options.timestampMs}-${options.sequenceIndex}`,
  };
  await putHistoryEvent(request, payload, 'asset movement event');
}

/**
 * Adds a single swap/trade event (`entry_type=swap event`) tagged with the
 * given location. Falls into the `TRADES` purge bucket.
 */
export async function apiSeedSwap(
  request: APIRequestContext,
  options: SeedOptions,
): Promise<void> {
  const payload = {
    entry_type: 'swap event',
    timestamp: options.timestampMs,
    location: options.location,
    spend_amount: '1',
    spend_asset: 'ETH',
    receive_amount: '3000',
    receive_asset: 'USD',
    unique_id: `e2e-trade-${options.timestampMs}-${options.sequenceIndex}`,
  };
  await putHistoryEvent(request, payload, 'swap event');
}

/**
 * Counts existing history events at a given location, bucketed by the
 * `entry_type` values that map to the three purge categories the UI exposes.
 */
export async function apiCountExchangeEventsByCategory(
  request: APIRequestContext,
  location: string,
): Promise<{ trades: number; assetMovements: number; other: number }> {
  const response = await request.post(`${backendUrl}/api/1/history/events`, {
    data: { location, exclude_ignored_assets: false },
  });
  if (!response.ok()) {
    throw new Error(
      `Failed to query history events for ${location}: ${response.status()} ${await response.text()}`,
    );
  }
  const body = await response.json();
  const entries: Array<{ entry: { entry_type: string } }> = body.result?.entries ?? [];
  return {
    trades: entries.filter(e => e.entry.entry_type === 'swap event').length,
    assetMovements: entries.filter(e => e.entry.entry_type === 'asset movement event').length,
    other: entries.filter(e => e.entry.entry_type === 'history event').length,
  };
}

async function putHistoryEvent(
  request: APIRequestContext,
  payload: Record<string, unknown>,
  kind: string,
): Promise<void> {
  const response = await request.put(`${backendUrl}/api/1/history/events`, { data: payload });
  const body = await response.json().catch(() => null);
  // Rotki's API often returns HTTP 200 with `result: false` and a non-empty
  // `message` on validation errors, so check both transport status and the
  // body envelope.
  const apiOk = body && body.result !== false && body.result !== null && body.result !== undefined;
  if (!response.ok() || !apiOk) {
    throw new Error(
      `Failed to seed ${kind} (${response.status()}): ${JSON.stringify(body) || await response.text()}`,
    );
  }
}
