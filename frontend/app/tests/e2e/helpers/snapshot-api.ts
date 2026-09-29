import type { APIRequestContext } from '@playwright/test';
import { backendUrl } from '../../../playwright.config';

export interface ApiBalanceSnapshot {
  amount: string;
  asset_identifier: string;
  category: string;
  timestamp: number;
  usd_value: string;
}

export interface ApiLocationDataSnapshot {
  location: string;
  timestamp: number;
  usd_value: string;
}

export interface ApiSnapshot {
  balances_snapshot: ApiBalanceSnapshot[];
  location_data_snapshot: ApiLocationDataSnapshot[];
}

/**
 * Adds assets to the user's ignored list. The app loads that list at login, so call it before a
 * (re)login for the UI to see it.
 */
export async function apiIgnoreAssets(request: APIRequestContext, assets: string[]): Promise<void> {
  const response = await request.put(`${backendUrl}/api/1/assets/ignored`, { data: { assets } });
  if (!response.ok())
    throw new Error(`Failed to ignore ${assets.join(', ')}: ${response.status()} ${await response.text()}`);
}

/**
 * Reads a snapshot directly from the backend for assertion purposes. Keys are
 * snake_case (the raw backend shape) — the frontend's camelCase is applied by
 * its own API wrapper, which we deliberately bypass here.
 */
export async function apiGetSnapshot(
  request: APIRequestContext,
  timestamp: number,
): Promise<ApiSnapshot> {
  const response = await request.get(`${backendUrl}/api/1/snapshots/${timestamp}`);
  if (!response.ok()) {
    throw new Error(
      `Failed to fetch snapshot at ${timestamp}: ${response.status()} ${await response.text()}`,
    );
  }
  const body: { result: ApiSnapshot | null; message: string } = await response.json();
  if (!body.result) {
    throw new Error(`No snapshot at ${timestamp}: ${body.message}`);
  }
  return body.result;
}
