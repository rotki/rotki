import type { APIRequestContext, Page } from '@playwright/test';
import { backendUrl, colibriUrl } from '../../../playwright.config';
import { TIMEOUT_LONG } from './constants';

const WAIT_TIME_MS = 5000;
const MAX_RETRIES = TIMEOUT_LONG / WAIT_TIME_MS;

/**
 * Delays execution for the specified number of milliseconds.
 */
async function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Logs out the currently logged-in user via API.
 * Also logs out from colibri service.
 */
export async function apiLogout(request: APIRequestContext): Promise<void> {
  const usersResponse = await request.get(`${backendUrl}/api/1/users`, {
    failOnStatusCode: false,
  });

  if (!usersResponse.ok()) {
    return;
  }

  const body = await usersResponse.json();
  const result = body.result;

  if (!result) {
    return;
  }

  const loggedUsers = Object.keys(result).filter(user => result[user] === 'loggedin');

  if (loggedUsers.length !== 1) {
    return;
  }

  const user = loggedUsers[0];

  await request.patch(`${backendUrl}/api/1/users/${user}`, {
    failOnStatusCode: false,
    data: {
      action: 'logout',
    },
  });

  // Also logout from colibri
  await request.post(`${colibriUrl}/user/logout`, {
    failOnStatusCode: false,
  });
}

/**
 * Performs a soft reset of assets via API.
 */
export async function apiUpdateAssets(request: APIRequestContext): Promise<void> {
  const response = await request.delete(`${backendUrl}/api/1/assets/updates`, {
    failOnStatusCode: false,
    data: {
      reset: 'soft',
    },
  });

  // Wait for response to complete - no logging needed
  await response.body();
}

/**
 * Disables all active modules via API.
 */
export async function apiDisableModules(request: APIRequestContext): Promise<void> {
  const response = await request.put(`${backendUrl}/api/1/settings`, {
    failOnStatusCode: false,
    data: {
      settings: {
        active_modules: [],
      },
    },
  });

  // Wait for response to complete - no logging needed
  await response.body();
}

/**
 * Checks for the completion of a task by polling the backend API.
 */
async function checkForTaskCompletion(
  request: APIRequestContext,
  taskId: number,
  currentRetry: number = 1,
): Promise<void> {
  const response = await request.get(`${backendUrl}/api/1/tasks`);

  if (response.ok()) {
    const body = await response.json();

    if (
      body.result
      && body.result.completed
      && Array.isArray(body.result.completed)
      && body.result.completed.includes(taskId)
    ) {
      // Fetch the task result to clear it
      await request.get(`${backendUrl}/api/1/tasks/${taskId}`);
      return;
    }
  }

  if (currentRetry > MAX_RETRIES) {
    throw new Error('Exceeded maximum retries for task completion check');
  }

  await delay(WAIT_TIME_MS);
  await checkForTaskCompletion(request, taskId, currentRetry + 1);
}

/**
 * Creates a new user account via API.
 * Also logs in to colibri to establish the session.
 */
export async function apiCreateAccount(
  request: APIRequestContext,
  username: string,
  password: string = '1234',
): Promise<void> {
  const response = await request.put(`${backendUrl}/api/1/users`, {
    timeout: TIMEOUT_LONG,
    failOnStatusCode: false,
    data: {
      name: username,
      password,
      initial_settings: {
        submit_usage_analytics: true,
      },
      async_query: true,
    },
  });

  const body = await response.json();

  if (body.result?.task_id) {
    await checkForTaskCompletion(request, body.result.task_id);
  }

  // Login to colibri after account creation
  await apiColibriLogin(request, username, password);
}

/**
 * Logs in an existing user via API (without recreating the account).
 * Also logs in to colibri to establish the session.
 */
export async function apiLogin(
  request: APIRequestContext,
  username: string,
  password: string = '1234',
): Promise<boolean> {
  const response = await request.patch(`${backendUrl}/api/1/users/${username}`, {
    timeout: TIMEOUT_LONG,
    failOnStatusCode: false,
    data: {
      action: 'login',
      password,
      sync_approval: 'unknown',
      async_query: true,
    },
  });

  const body = await response.json();

  if (body.result?.task_id) {
    await checkForTaskCompletion(request, body.result.task_id);
    // Login to colibri after backend login succeeds
    await apiColibriLogin(request, username, password);
    return true;
  }

  if (response.ok()) {
    // Login to colibri after backend login succeeds
    await apiColibriLogin(request, username, password);
  }

  return response.ok();
}

/**
 * Logs in to colibri service to establish the database session.
 */
export async function apiColibriLogin(
  request: APIRequestContext,
  username: string,
  password: string,
): Promise<void> {
  await request.post(`${colibriUrl}/user`, {
    failOnStatusCode: false,
    data: {
      username,
      password,
    },
  });
}

/**
 * Adds an Etherscan API key to external services.
 */
export async function apiAddEtherscanKey(
  request: APIRequestContext,
  key: string,
): Promise<number> {
  const response = await request.put(`${backendUrl}/api/1/external_services`, {
    failOnStatusCode: false,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
    },
    data: {
      services: [{ name: 'etherscan', api_key: key }],
    },
  });

  return response.status();
}

/**
 * Waits for all running tasks to complete by checking the notification indicator.
 * Uses polling with expect().toPass() instead of hardcoded delays.
 */
export async function waitForNoRunningTasks(page: Page, timeout: number = 120000): Promise<void> {
  const { expect } = await import('@playwright/test');
  const indicator = page.locator('[data-cy=notification-indicator-progress]');

  // Poll until the indicator is detached and stays detached
  await expect(async () => {
    await expect(indicator).toBeHidden();
  }).toPass({ timeout, intervals: [500, 1000, 2000] });
}

/**
 * Waits for an async query to complete by polling the tasks endpoint.
 */
export async function waitForAsyncQuery(
  request: APIRequestContext,
  taskId: number,
): Promise<unknown> {
  await checkForTaskCompletion(request, taskId);

  const response = await request.get(`${backendUrl}/api/1/tasks/${taskId}`);
  const body = await response.json();
  return body.result?.outcome;
}

/**
 * Gets the list of currently ignored assets via API.
 */
export async function apiGetIgnoredAssets(request: APIRequestContext): Promise<string[]> {
  const response = await request.get(`${backendUrl}/api/1/assets/ignored`, {
    failOnStatusCode: false,
  });

  if (response.ok()) {
    const body = await response.json();
    return body.result || [];
  }
  return [];
}

/**
 * Adds assets to the ignored list via API.
 */
export async function apiAddIgnoredAssets(
  request: APIRequestContext,
  assets: string[],
): Promise<boolean> {
  const response = await request.put(`${backendUrl}/api/1/assets/ignored`, {
    failOnStatusCode: false,
    data: { assets },
  });

  return response.ok();
}

/**
 * Removes assets from the ignored list via API.
 */
export async function apiRemoveIgnoredAssets(
  request: APIRequestContext,
  assets: string[],
): Promise<boolean> {
  const response = await request.delete(`${backendUrl}/api/1/assets/ignored`, {
    failOnStatusCode: false,
    data: { assets },
  });

  return response.ok();
}

/**
 * Ensures specific assets are NOT in the ignored list (removes them if they are).
 */
export async function apiEnsureAssetsNotIgnored(
  request: APIRequestContext,
  assets: string[],
): Promise<void> {
  const ignoredAssets = await apiGetIgnoredAssets(request);
  const assetsToRemove = assets.filter(asset => ignoredAssets.includes(asset));

  if (assetsToRemove.length > 0) {
    await apiRemoveIgnoredAssets(request, assetsToRemove);
  }
}

/**
 * Ensures specific assets ARE in the ignored list (adds them if they aren't).
 */
export async function apiEnsureAssetsIgnored(
  request: APIRequestContext,
  assets: string[],
): Promise<void> {
  const ignoredAssets = await apiGetIgnoredAssets(request);
  const assetsToAdd = assets.filter(asset => !ignoredAssets.includes(asset));

  if (assetsToAdd.length > 0) {
    await apiAddIgnoredAssets(request, assetsToAdd);
  }
}

/**
 * Searches for an asset by symbol and returns matching asset identifiers.
 */
export async function apiSearchAssetsBySymbol(
  request: APIRequestContext,
  symbol: string,
  limit: number = 5,
): Promise<string[]> {
  const response = await request.post(`${backendUrl}/api/1/assets/search/levenshtein`, {
    failOnStatusCode: false,
    data: {
      value: symbol,
      limit,
    },
  });

  if (response.ok()) {
    const body = await response.json();
    // The result is an array of assets with 'identifier' field
    if (Array.isArray(body.result)) {
      return body.result.map((asset: { identifier: string }) => asset.identifier);
    }
  }
  return [];
}

/**
 * Ensures assets matching the given symbols are NOT ignored.
 * Searches by symbol, finds the identifiers, and removes them from ignored list if present.
 */
export async function apiEnsureSymbolsNotIgnored(
  request: APIRequestContext,
  symbols: string[],
): Promise<void> {
  const ignoredAssets = await apiGetIgnoredAssets(request);

  if (ignoredAssets.length === 0) {
    return; // Nothing is ignored, nothing to do
  }

  // Find identifiers for each symbol (search with higher limit to catch all variants)
  const identifiersToCheck: string[] = [];
  for (const symbol of symbols) {
    const identifiers = await apiSearchAssetsBySymbol(request, symbol, 10);
    identifiersToCheck.push(...identifiers);
  }

  // Filter to only those that are actually ignored
  const toRemove = identifiersToCheck.filter(id => ignoredAssets.includes(id));

  if (toRemove.length > 0) {
    await apiRemoveIgnoredAssets(request, toRemove);
  }
}
