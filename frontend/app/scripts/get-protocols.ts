import { type ChildProcess, spawn } from 'node:child_process';
import { randomInt } from 'node:crypto';
import * as fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { assert, toHumanReadable, toSentenceCase } from '@rotki/common';
import axios from 'axios';
import consola from 'consola';

interface Chain {
  id: string;
  name: string;
  type: string;
  image: string;
  native_token: string;
  evm_chain_name?: string;
}

interface Location {
  image: string;
  exchange_details?: {
    is_exchange_with_key: boolean;
  };
  is_exchange?: boolean;
  label?: string;
}

type Locations = Record<string, Location>;

interface Counterparty { identifier: string; label: string; image: string }

if (!(process.env.CI || process.env.VIRTUAL_ENV)) {
  consola.error('Not CI or VIRTUAL_ENV');
  process.exit(1);
}

const PORT = 55551;
const HOST = '127.0.0.1';
const API_URL = `http://${HOST}:${PORT}/api/1`;
const PING_URL = `${API_URL}/ping`;
const OUTPUT_FILE = 'all.json';
const imageUrl = 'https://raw.githubusercontent.com/rotki/rotki/develop/frontend/app/public/assets/images/protocols/';

// Store the backend process globally so we can terminate it later
let backendProcess: ChildProcess | null = null;

// Ensure the backend is terminated when the script is interrupted
process.on('SIGINT', () => {
  consola.info('Received SIGINT signal');
  terminateBackend();
  process.exit(0);
});

process.on('SIGTERM', () => {
  consola.info('Received SIGTERM signal');
  terminateBackend();
  process.exit(0);
});

/**
 * Terminates the backend process if it's running
 * @returns {void}
 */
function terminateBackend(): void {
  if (backendProcess) {
    consola.info('Terminating backend...');
    try {
      if (process.platform === 'win32') {
        const pid = backendProcess.pid?.toString();
        if (pid)
          spawn('taskkill', ['/pid', pid, '/f', '/t']);
      }
      else {
        try {
          process.kill(-backendProcess.pid!, 'SIGTERM');
        }
        catch (error) {
          consola.warn('Failed to kill process group, trying to kill just the process:', error);
          process.kill(backendProcess.pid!, 'SIGTERM');
        }
      }
      consola.success('Backend terminated');
    }
    catch (error) {
      consola.error('Error terminating backend:', error);
    }
    finally {
      backendProcess = null;
    }
  }
}

/**
 * Generates a UUID username in the format "protocols-xxxxxx" with six random digits
 * @returns {string} The generated username
 */
function generateUsername(): string {
  const randomDigits = Array.from({ length: 6 }, () => randomInt(0, 10)).join('');
  return `protocols-${randomDigits}`;
}

// Generate the username once and use it throughout the script
const username = generateUsername();
const password = '123456789';

/**
 * Checks if the backend is running by pinging the endpoint
 * @returns {Promise<boolean>} True if the backend is running, false otherwise
 */
async function isBackendRunning(): Promise<boolean> {
  try {
    const response = await axios.get(PING_URL, { timeout: 1000 });
    return response.status === 200;
  }
  catch {
    return false;
  }
}

/**
 * Starts the backend with minimal parameters
 * @returns {Promise<void>}
 */
async function startBackend(): Promise<void> {
  // Create a folder in /tmp with the username
  const userDir = path.join('/tmp', username);
  const dataDir = path.join(userDir, 'data');
  const logsDir = path.join(userDir, 'logs');

  // Create directories if they don't exist
  if (!fs.existsSync(userDir)) {
    fs.mkdirSync(userDir, { recursive: true });
  }

  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }

  if (!fs.existsSync(logsDir)) {
    fs.mkdirSync(logsDir, { recursive: true });
  }

  const args = [
    path.join(process.cwd(), 'scripts', 'start-backend.ts'),
    '--data',
    dataDir,
    '--logs',
    logsDir,
    '--port',
    PORT.toString(),
  ];

  consola.info('Starting backend...');

  // Spawn the backend process
  backendProcess = spawn('tsx', args, {
    stdio: 'inherit',
    detached: true,
  });

  // Don't wait for the child process
  backendProcess.unref();
}

/**
 * Waits until the backend is ready
 * @returns {Promise<void>}
 */
async function waitForBackend(): Promise<void> {
  const maxRetries = 30;
  let retries = 0;

  while (retries < maxRetries) {
    consola.info(`Waiting for backend to be ready... (${retries + 1}/${maxRetries})`);
    if (await isBackendRunning()) {
      consola.success('Backend is ready!');
      return;
    }

    // Wait for 1 second before retrying
    await new Promise(resolve => setTimeout(resolve, 1000));
    retries++;
  }

  throw new Error('Backend failed to start after maximum retries');
}

/**
 * Creates a user with the given username and password
 * @returns {Promise<boolean>} True if the user was created successfully, false otherwise
 */
async function createUser(): Promise<boolean> {
  try {
    consola.info(`Creating user ${username}...`);
    const response = await axios.put(`${API_URL}/users`, {
      name: username,
      password,
      initial_settings: {
        submit_usage_analytics: false,
      },
    });

    if (response.status === 200) {
      consola.success(`User ${username} created successfully!`);
      return true;
    }

    consola.error(`Failed to create user ${username}: ${response.data}`);
    return false;
  }
  catch (error) {
    consola.error(`Error creating user ${username}:`, error);
    return false;
  }
}

/**
 * Fetches data from the backend API
 * @param {string} endpoint - The API endpoint to fetch data from
 * @returns {Promise<any>} The fetched data
 */
async function fetchFromApi(endpoint: string): Promise<any> {
  try {
    const response = await axios.get(`${API_URL}/${endpoint}`);
    return response.data.result;
  }
  catch (error) {
    consola.error(`Error fetching from ${endpoint}:`, error);
    throw error;
  }
}

function getExchanges(locations: Locations) {
  return Object.keys(locations)
    .filter((item: string) => locations[item].is_exchange ?? locations[item].exchange_details)
    .map((item) => {
      const data = locations[item];
      const isExchangeWithKey = data?.exchange_details?.is_exchange_with_key ?? false;

      return {
        image: `${imageUrl}${data.image}`,
        label: data.label ?? toSentenceCase(item),
        ...(isExchangeWithKey ? { isExchangeWithKey: true } : {}),
      };
    });
}

function getBlockchains(chains: Chain[]) {
  return chains
    .filter((item: any) => item.name !== 'Ethereum Staking')
    .map((item: any) => ({
      image: `${imageUrl}${item.image}`,
      label: toSentenceCase(item.name),
    }));
}

function getCounterparties(counterparties: Counterparty[]) {
  const identifiers = counterparties.map((item: Counterparty) => item.identifier);
  const filteredCounterparties = identifiers
    .filter((item: string) => item !== 'gas')
    .sort((a: string, b: string) => a.localeCompare(b, undefined, { sensitivity: 'base' }));

  // Group protocols by their base name (part before any dash)
  const protocolGroups = filteredCounterparties.reduce((groups: Record<string, string[]>, item: string) => {
    const baseProtocol = item.split('-')[0];
    if (!groups[baseProtocol]) {
      groups[baseProtocol] = [];
    }
    groups[baseProtocol].push(item);
    return groups;
  }, {} as Record<string, string[]>);

  const selectedProtocols: string[] = [];

  // Process each group based on rules
  Object.entries(protocolGroups).forEach(([baseProtocol, items]) => {
    // Check if the base protocol exists by itself
    if (items.includes(baseProtocol)) {
      selectedProtocols.push(baseProtocol);
      return;
    }

    // Check if there's another protocol that starts with the base name but isn't versioned
    const nonVersionedVariant = items.find(item =>
      item.startsWith(baseProtocol)
      && !new RegExp(`^${baseProtocol}-v\\d+$`).test(item),
    );

    if (nonVersionedVariant) {
      selectedProtocols.push(nonVersionedVariant);
      return;
    }

    // If we only have versioned variants, create a synthetic base protocol
    // and use the first item's data
    selectedProtocols.push(baseProtocol);
  });

  return selectedProtocols.map((item) => {
    // For synthetic base protocols that don't exist in counterparties
    if (!filteredCounterparties.includes(item)) {
      // Find the first versioned variant to get its image
      const versionedVariant = filteredCounterparties.find(protocol =>
        protocol.startsWith(`${item}-v`),
      );

      if (versionedVariant) {
        const variantData = counterparties.find(counterparty => counterparty.identifier === versionedVariant);
        assert(variantData);
        return {
          image: `${imageUrl}${variantData.image}`,
          label: toHumanReadable(item, 'sentence'),
        };
      }
    }

    // Normal case - protocol exists in counterparties
    const data = counterparties.find(counterparty => counterparty.identifier === item);
    assert(data);
    return {
      image: `${imageUrl}${data.image}`,
      label: toHumanReadable(data.label, 'sentence'),
    };
  });
}

/**
 * Generates the JSON data for protocols, blockchains, and exchanges
 * @returns {Promise<string>} The generated JSON data
 */
async function generateJsonData(): Promise<string> {
  try {
    // Fetch necessary data from the backend API
    const chains = await fetchFromApi('/blockchains/supported');
    const { locations } = await fetchFromApi('/locations/all');
    const counterpartyData = await fetchFromApi('/history/events/counterparties');

    const blockchains = getBlockchains(chains);
    const exchanges = getExchanges(locations);
    const protocols = getCounterparties(counterpartyData);

    const data = {
      blockchains,
      exchanges,
      protocols,
    };

    return JSON.stringify(data, null, 2);
  }
  catch (error) {
    consola.error('Error generating JSON data:', error);
    throw error;
  }
}

// Use top-level await instead of an async function
try {
  await startBackend();
  await waitForBackend();

  // Create user and login
  const userCreated = await createUser();
  if (!userCreated) {
    throw new Error('Failed to create user');
  }

  consola.info('Generating JSON data...');
  const jsonData = await generateJsonData();

  consola.info(`Writing JSON data to ${OUTPUT_FILE}...`);
  fs.writeFileSync(OUTPUT_FILE, `${jsonData}\n`);

  consola.success(`JSON data written to ${OUTPUT_FILE}`);

  terminateBackend();
}
catch (error) {
  consola.error('Error:', error);

  // Terminate the backend even if there's an error
  terminateBackend();

  process.exit(1);
}
