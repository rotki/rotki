import type { APIRequestContext } from '@playwright/test';
import { createConsola } from 'consola';
import { backendUrl } from '../../../playwright.config';
import { MOCK_RPC_PORT } from './constants';

const logger = createConsola({ defaults: { tag: 'rpc-mock' } });
const mockRpcUrl = `http://127.0.0.1:${MOCK_RPC_PORT}`;

interface RpcNode {
  identifier: number;
  name: string;
  endpoint: string;
  owned: boolean;
  active: boolean;
  weight: string;
}

/**
 * Checks whether the mock RPC server is running.
 */
export async function isMockRpcAvailable(): Promise<boolean> {
  try {
    const response = await fetch(`${mockRpcUrl}/health`);
    return response.ok;
  }
  catch {
    return false;
  }
}

/**
 * Switches the mock RPC server to a specific cassette.
 * Call this before configuring RPC nodes to ensure the right cassette is loaded.
 */
export async function switchMockRpcCassette(name: string): Promise<void> {
  const response = await fetch(`${mockRpcUrl}/cassette`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });

  if (response.ok) {
    const body = await response.json() as { entries: number };
    logger.info(`Switched to cassette "${name}" (${body.entries} entries)`);
  }
  else {
    logger.error(`Failed to switch cassette to "${name}": ${response.status}`);
  }
}

/**
 * Substrate chains (Polkadot/Kusama) don't use the multi-node API like EVM/Solana —
 * they have a single `<chain>_rpc_endpoint` user setting. Map each substrate chain
 * identifier to the corresponding settings key.
 */
const SUBSTRATE_ENDPOINT_SETTINGS: Record<string, string> = {
  DOT: 'dot_rpc_endpoint',
  KSM: 'ksm_rpc_endpoint',
};

/**
 * Configures the backend to use the mock RPC server for a substrate chain (DOT/KSM)
 * by updating the user setting that controls that chain's RPC endpoint.
 *
 * Setting the endpoint triggers a connection attempt that fetches chain metadata,
 * so the mock RPC server (or its recording target) must be reachable at this point.
 */
async function apiConfigureSubstrateRpcMock(
  request: APIRequestContext,
  blockchain: string,
): Promise<void> {
  const settingKey = SUBSTRATE_ENDPOINT_SETTINGS[blockchain];
  if (!settingKey) {
    logger.error(`No substrate endpoint setting mapped for ${blockchain}`);
    return;
  }

  const response = await request.put(`${backendUrl}/api/1/settings`, {
    failOnStatusCode: false,
    data: { settings: { [settingKey]: mockRpcUrl } },
  });

  if (response.ok()) {
    logger.info(`Configured ${blockchain} to use mock RPC at ${mockRpcUrl}`);
  }
  else {
    logger.error(`Failed to set ${settingKey} for ${blockchain}: ${response.status()}`);
  }
}

/**
 * Configures the backend to use the mock RPC server for the specified blockchain.
 * Removes all existing default nodes and adds the mock server as the only node.
 */
export async function apiConfigureRpcMock(
  request: APIRequestContext,
  blockchain: string = 'ETH',
): Promise<void> {
  if (blockchain in SUBSTRATE_ENDPOINT_SETTINGS) {
    await apiConfigureSubstrateRpcMock(request, blockchain);
    return;
  }

  const nodesUrl = `${backendUrl}/api/1/blockchains/${blockchain}/nodes`;

  // Get all existing nodes
  const getResponse = await request.get(nodesUrl, { failOnStatusCode: false });
  if (!getResponse.ok())
    return;

  const body = await getResponse.json();
  const nodes: RpcNode[] = body.result ?? [];

  // Delete all existing nodes
  for (const node of nodes) {
    if (node.identifier) {
      await request.delete(nodesUrl, {
        failOnStatusCode: false,
        data: { identifier: node.identifier },
      });
    }
  }

  // Add mock server as the only node
  const addResponse = await request.put(nodesUrl, {
    failOnStatusCode: false,
    data: {
      name: 'mock-rpc',
      endpoint: mockRpcUrl,
      owned: true,
      weight: '1.00',
      active: true,
    },
  });

  if (addResponse.ok()) {
    logger.info(`Configured ${blockchain} to use mock RPC at ${mockRpcUrl}`);
  }
  else {
    logger.error(`Failed to add mock RPC node for ${blockchain}: ${addResponse.status()}`);
  }
}

/**
 * Configures the given blockchains to use the mock RPC server with the specified cassette.
 * Call this after user login but before any blockchain queries.
 *
 * @param request - Playwright API request context
 * @param cassetteName - Name of the cassette file (without .json extension)
 * @param chains - Backend blockchain identifiers (e.g. 'ETH', 'SOLANA'). Defaults to ['ETH'].
 */
export async function apiConfigureRpcMocks(
  request: APIRequestContext,
  cassetteName: string,
  chains: string[] = ['ETH'],
): Promise<void> {
  const available = await isMockRpcAvailable();
  if (!available) {
    logger.warn('Mock RPC server not available, skipping configuration');
    return;
  }

  // Switch to the test-specific cassette
  await switchMockRpcCassette(cassetteName);

  for (const chain of chains) {
    await apiConfigureRpcMock(request, chain);
  }
}

/**
 * Triggers the mock RPC server to save its current cassette to disk.
 * Call this after tests complete in record mode.
 */
export async function saveMockRpcCassette(): Promise<void> {
  try {
    await fetch(`${mockRpcUrl}/save`, { method: 'POST' });
  }
  catch {
    // Server might already be shut down
  }
}
