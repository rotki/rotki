import { type ChildProcess, spawn } from 'node:child_process';
import { randomInt } from 'node:crypto';
import * as fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { assert, toHumanReadable, toSentenceCase } from '@rotki/common';
import consola from 'consola';
import { ofetch } from 'ofetch';
import { SHUTDOWN_GRACE_SECS } from '../shared/starling/starling-args';
import { isUvAvailable } from '../shared/uv';

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

// Without a venv or uv.lock, starling falls back to whatever bare `python` is on PATH.
if (!process.env.VIRTUAL_ENV && !isUvAvailable()) {
  consola.error(
    'No python virtualenv active and `uv` is not on PATH.\n'
    + 'Activate a venv (e.g. `source .venv/bin/activate`) or install uv (https://docs.astral.sh/uv/).',
  );
  process.exit(1);
}

// The supervisor's proxy, with core, colibri and MCP behind it, clear of the dev and e2e ranges.
const PORT = 55551;
const CORE_PORT = 55552;
const COLIBRI_PORT = 55553;
const MCP_PORT = 55554;
const HOST = '127.0.0.1';
const API_URL = `http://${HOST}:${PORT}/api/1`;
const PING_URL = `${API_URL}/ping`;
const OUTPUT_FILE = 'all.json';
const imageUrl = 'https://raw.githubusercontent.com/rotki/rotki/develop/frontend/app/public/assets/images/protocols/';

// Store the backend process globally so we can terminate it later
let backendProcess: ChildProcess | null = null;

/**
 * How long the supervisor gets to bring the tree down on its own. It asks starling
 * to stop, gives it `SHUTDOWN_GRACE_SECS`, then kills it and reports the exit, so
 * the wait has to outlast that grace or we would escalate over a teardown that was
 * still progressing normally.
 */
const TEARDOWN_TIMEOUT_MS = (SHUTDOWN_GRACE_SECS + 5) * 1000;

/**
 * Terminates the backend when the script is interrupted. The handler waits for the teardown
 * rather than exiting under it: otherwise this process dies first and leaves core and colibri
 * behind, still holding their ports.
 */
function handleSignal(signal: NodeJS.Signals): void {
  consola.info(`Received ${signal} signal`);
  stopBackend()
    .then(() => cleanupUserData())
    .catch(error => consola.error('Error terminating backend:', error))
    .finally(() => process.exit(0));
}

process.on('SIGINT', () => handleSignal('SIGINT'));
process.on('SIGTERM', () => handleSignal('SIGTERM'));

function hasExited(child: ChildProcess): boolean {
  return child.exitCode !== null || child.signalCode !== null;
}

async function waitForExit(child: ChildProcess): Promise<void> {
  return new Promise((resolve) => {
    if (hasExited(child)) {
      resolve();
      return;
    }
    child.once('exit', () => resolve());
  });
}

/** Stops the backend tree and waits for it to actually be down. */
async function stopBackend(): Promise<void> {
  const child = backendProcess;
  backendProcess = null;
  if (!child)
    return;

  const { pid } = child;
  // No pid means the spawn itself failed, so there is nothing running to reap.
  if (pid === undefined || hasExited(child))
    return;

  consola.info('Terminating backend...');
  /* Signal this child alone, never its group: it stops starling over RPC, and starling brings
     core and colibri down in order. A group signal would hit starling directly and strand
     whatever it had not reaped. The escalation below is a kill for the same single child, whose
     death closes starling's stdin, which starling reads as its own cue to tear the tree down. */
  child.kill('SIGTERM');

  const escalation = setTimeout(() => {
    consola.warn(`Backend did not exit within ${TEARDOWN_TIMEOUT_MS}ms, killing the supervisor`);
    child.kill('SIGKILL');
  }, TEARDOWN_TIMEOUT_MS);

  try {
    await waitForExit(child);
    consola.success('Backend terminated');
  }
  finally {
    clearTimeout(escalation);
  }
}

/**
 * Generates a UUID username in the format "protocols-xxxxxx" with six random digits
 * @returns The generated username
 */
function generateUsername(): string {
  const randomDigits = Array.from({ length: 6 }, () => randomInt(0, 10)).join('');
  return `protocols-${randomDigits}`;
}

// Generate the username once and use it throughout the script
const username = generateUsername();
const password = '123456789';

// At module scope so the teardown can remove it without `startBackend` having run.
const userDir = path.join('/tmp', username);

/**
 * Removes the throwaway user's data directory. Only safe once the backend is
 * down, since core holds its database open for the lifetime of the process.
 *
 * Kept to this run's own directory: a stale `protocols-*` from an earlier run
 * could still belong to a live instance, and this script is not the owner of
 * anything it did not create.
 */
function cleanupUserData(): void {
  try {
    fs.rmSync(userDir, { recursive: true, force: true });
  }
  catch (error) {
    consola.warn(`Failed to remove ${userDir}:`, error);
  }
}

/**
 * Checks if the backend is running by pinging the endpoint
 * @returns True if the backend is running, false otherwise
 */
async function isBackendRunning(): Promise<boolean> {
  try {
    await ofetch(PING_URL, { timeout: 1000 });
    return true;
  }
  catch {
    return false;
  }
}

/**
 * Starts the backend with minimal parameters.
 *
 * @remarks
 * Runs against a throwaway data and log directory under the temporary user folder, so the script
 * never touches a real rotki installation.
 */
async function startBackend(): Promise<void> {
  const dataDir = path.join(userDir, 'data');
  const logsDir = path.join(userDir, 'logs');

  if (!fs.existsSync(userDir)) {
    fs.mkdirSync(userDir, { recursive: true });
  }

  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }

  if (!fs.existsSync(logsDir)) {
    fs.mkdirSync(logsDir, { recursive: true });
  }

  // The same launcher the app and the e2e suite use; `/api/1/*` reaches core through it.
  const args = [
    path.join(process.cwd(), 'scripts', 'start-starling.ts'),
    '--data',
    dataDir,
    '--logs',
    logsDir,
    '--port',
    PORT.toString(),
    '--core-port',
    CORE_PORT.toString(),
    '--colibri-port',
    COLIBRI_PORT.toString(),
    '--mcp-port',
    MCP_PORT.toString(),
  ];

  consola.info('Starting backend...');

  /* Its own process group insulates it from the terminal's Ctrl+C, so the handlers here drive
     the teardown in one order. Not unref'd: this script owns the child's lifetime. `tsx`
     directly, never `pnpm run`, which does not forward the directed SIGTERM below. */
  backendProcess = spawn('tsx', args, {
    stdio: 'inherit',
    detached: true,
  });
}

/** Waits until the backend answers, or gives up after the retry budget. */
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
 * @returns True if the user was created successfully, false otherwise
 */
async function createUser(): Promise<boolean> {
  try {
    consola.info(`Creating user ${username}...`);
    await ofetch(`${API_URL}/users`, {
      method: 'PUT',
      body: {
        name: username,
        password,
        initial_settings: {
          submit_usage_analytics: false,
        },
      },
    });

    consola.success(`User ${username} created successfully!`);
    return true;
  }
  catch (error) {
    consola.error(`Error creating user ${username}:`, error);
    return false;
  }
}

/**
 * Fetches data from the backend API
 * @param endpoint - The API endpoint to fetch data from
 * @returns The fetched data
 */
async function fetchFromApi(endpoint: string): Promise<any> {
  try {
    const response = await ofetch<{ result: any }>(`${API_URL}/${endpoint}`);
    return response.result;
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

/**
 * The single identifier that stands for a group of related protocols.
 *
 * @remarks
 * The unversioned identifier wins when the group contains it, then any variant that is not a
 * `-v<n>`. Only when the group is versions all the way down does the base name stand in, as a
 * synthetic entry that has no counterparty of its own.
 */
function representativeFor(baseProtocol: string, items: string[]): string {
  if (items.includes(baseProtocol))
    return baseProtocol;

  const nonVersionedVariant = items.find(item =>
    item.startsWith(baseProtocol)
    && !new RegExp(`^${baseProtocol}-v\\d+$`).test(item),
  );

  return nonVersionedVariant ?? baseProtocol;
}

/**
 * The image and label to publish for one selected protocol.
 *
 * @remarks
 * A synthetic base name matches no counterparty, so its image is borrowed from its first versioned
 * variant and its label built from the name itself. Every other identifier is looked up directly.
 */
function toProtocolEntry(item: string, counterparties: Counterparty[], known: string[]): { image: string; label: string } {
  if (!known.includes(item)) {
    const versionedVariant = known.find(protocol => protocol.startsWith(`${item}-v`));

    if (versionedVariant) {
      const variantData = counterparties.find(counterparty => counterparty.identifier === versionedVariant);
      assert(variantData);
      return {
        image: `${imageUrl}${variantData.image}`,
        label: toHumanReadable(item, 'sentence'),
      };
    }
  }

  const data = counterparties.find(counterparty => counterparty.identifier === item);
  assert(data);
  return {
    image: `${imageUrl}${data.image}`,
    label: toHumanReadable(data.label, 'sentence'),
  };
}

function getCounterparties(counterparties: Counterparty[]) {
  const identifiers = counterparties.map((item: Counterparty) => item.identifier);
  const filteredCounterparties = identifiers
    .filter((item: string) => item !== 'gas')
    .sort((a: string, b: string) => a.localeCompare(b, undefined, { sensitivity: 'base' }));

  // Group protocols by their base name (part before any dash)
  const protocolGroups = filteredCounterparties.reduce<Record<string, string[]>>((groups, item: string) => {
    const dash = item.indexOf('-');
    const baseProtocol = dash === -1 ? item : item.slice(0, dash);
    if (!groups[baseProtocol]) {
      groups[baseProtocol] = [];
    }
    groups[baseProtocol].push(item);
    return groups;
  }, {});

  const selectedProtocols = Object.entries(protocolGroups)
    .map(([baseProtocol, items]) => representativeFor(baseProtocol, items));

  return selectedProtocols.map(item => toProtocolEntry(item, counterparties, filteredCounterparties));
}

/**
 * Generates the JSON data for protocols, blockchains, and exchanges
 * @returns The generated JSON data
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

  await stopBackend();
  cleanupUserData();
}
catch (error) {
  consola.error('Error:', error);

  // Terminate the backend even if there's an error
  await stopBackend();

  // Kept on failure: its logs are the only record of why the backend would not come up.
  consola.info(`Left the backend data directory behind for inspection: ${userDir}`);

  process.exit(1);
}
