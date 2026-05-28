import fs from 'node:fs';
import process from 'node:process';
import { cac } from 'cac';
import consola from 'consola';
import { config } from 'dotenv';
import {
  cleanAll,
  cleanInstance,
  clearManagedEnvBlock,
  DEFAULT_PORTS,
  type InstanceRuntime,
  PortSlotAllocationError,
  prepareInstance,
  printInstanceList,
  pruneInstances,
  readManagedInstanceName,
  repairRegistry,
} from './dev-instance';
import { errorMessage, formatPort } from './dev-instance/format';
import { getCurrentGitBranch } from './dev-instance/git';
import { ensurePrerequisites, parsePort } from './dev/prerequisites';
import { registerShutdownHandlers, terminateSubprocesses } from './dev/process-pool';
import { startDevelopmentEnvironment } from './dev/services';

const ENV_FILE_RELATIVE = 'app/.env.development.local';

const logger = consola.withTag('[36mdev[0m');

interface DevCliOptions {
  web?: boolean;
  webPort?: string;
  colibriPort?: string;
  profilingArgs?: string;
  profilingCmd?: string;

  // management subcommands
  list?: boolean;
  clean?: string | boolean;
  cleanAll?: boolean;
  prune?: boolean;
  repair?: boolean;
  yes?: boolean;
  olderThan?: string;

  // runtime instance-mode flags
  instance?: string | boolean;
  seed?: boolean;
  acceptManagedEnv?: boolean;
  includeBackups?: boolean;

  // dev-proxy gate
  proxy?: boolean;
}

async function dispatchManagementSubcommand(options: DevCliOptions): Promise<boolean> {
  if (options.list) {
    await printInstanceList();
    return true;
  }
  if (options.cleanAll) {
    await cleanAll({ yes: options.yes, envFile: ENV_FILE_RELATIVE });
    return true;
  }
  if (options.clean !== undefined) {
    if (typeof options.clean !== 'string' || options.clean.length === 0) {
      logger.error('--clean requires an instance name (e.g. --clean my-instance)');
      process.exit(1);
    }
    await cleanInstance(options.clean, { yes: options.yes, envFile: ENV_FILE_RELATIVE });
    return true;
  }
  if (options.prune) {
    await pruneInstances({ yes: options.yes, olderThan: options.olderThan, envFile: ENV_FILE_RELATIVE });
    return true;
  }
  if (options.repair) {
    await repairRegistry({ yes: options.yes });
    return true;
  }
  return false;
}

function loadDevEnv(): void {
  if (fs.existsSync(ENV_FILE_RELATIVE)) {
    config({ path: ENV_FILE_RELATIVE });
  }
}

const DEV_PROXY_ASYNC_MOCK = 'dev-proxy/async-mock.json';

/**
 * Resolves whether to spawn the dev-proxy:
 *  - explicit `--proxy` / `--no-proxy` always wins
 *  - else auto-on if PREMIUM_COMPONENT_DIR resolves to a real dir, or
 *    dev-proxy/async-mock.json exists (the two features the proxy provides
 *    beyond plain pass-through)
 *  - else off — the frontend talks directly to the backend (CORS allows it)
 *
 * Note: `PREMIUM_COMPONENT_DIR` must be set in `frontend/app/.env.development.local`
 * or in the shell for auto-detect to see it — `frontend/dev-proxy/.env` is only
 * read by the proxy subprocess itself.
 */
function shouldUseProxy(options: DevCliOptions): boolean {
  if (options.proxy === true)
    return true;
  if (options.proxy === false)
    return false;
  const premiumDir = process.env.PREMIUM_COMPONENT_DIR;
  if (premiumDir && fs.existsSync(premiumDir) && fs.statSync(premiumDir).isDirectory())
    return true;
  if (fs.existsSync(DEV_PROXY_ASYNC_MOCK))
    return true;
  return false;
}

function pickInstanceName(option: DevCliOptions['instance']): string | undefined {
  if (typeof option === 'string' && option.length > 0)
    return option;
  if (option === true) {
    // Bare `--instance` → user explicitly wants instance mode without typing a name.
    // Fall back to INSTANCE_NAME env (wt-managed case), then current git branch,
    // then error.
    const envName = process.env.INSTANCE_NAME;
    if (envName)
      return envName;
    const branch = getCurrentGitBranch();
    if (branch) {
      logger.info(`--instance with no name — deriving from current git branch "${branch}"`);
      return branch;
    }
    logger.error(
      '--instance requires a name (e.g. --instance scratch).\n'
      + 'No INSTANCE_NAME env var or git branch was available to derive one. '
      + 'Use --no-instance to disable instance mode.',
    );
    process.exit(1);
  }
  return process.env.INSTANCE_NAME || undefined;
}

function readSlotHint(resolvedName: string): number | undefined {
  const raw = process.env.INSTANCE_PORT_SLOT;
  if (raw === undefined)
    return undefined;
  // INSTANCE_NAME and INSTANCE_PORT_SLOT are written as a pair by the managed
  // env block. If the resolved instance differs from the name that block was
  // written for, the slot hint doesn't apply to us — ignore it rather than
  // trying to grab another instance's slot.
  const pairedName = process.env.INSTANCE_NAME;
  if (pairedName && pairedName !== resolvedName) {
    logger.info(
      `Ignoring INSTANCE_PORT_SLOT=${raw}: it was paired with INSTANCE_NAME="${pairedName}", `
      + `but this run resolved to "${resolvedName}".`,
    );
    return undefined;
  }
  const slot = Number.parseInt(raw, 10);
  if (!Number.isFinite(slot)) {
    logger.error(`INSTANCE_PORT_SLOT="${raw}" is not a valid integer.`);
    process.exit(1);
  }
  return slot;
}

async function resolveInstance(options: DevCliOptions, useProxy: boolean): Promise<InstanceRuntime | null> {
  if (options.instance === false) {
    // Explicit --no-instance: erase any stale managed block from a prior
    // instance run so Vite doesn't read INSTANCE_PORT_SLOT / VITE_BACKEND_URL
    // pointing at a slot we're no longer using.
    const staleOwner = readManagedInstanceName(ENV_FILE_RELATIVE);
    if (staleOwner !== undefined) {
      clearManagedEnvBlock(ENV_FILE_RELATIVE);
      logger.info(`--no-instance: cleared managed env block left over from "${staleOwner}"`);
    }
    return null;
  }
  const name = pickInstanceName(options.instance);
  if (!name)
    return null;
  return prepareInstance({
    name,
    slotHint: readSlotHint(name),
    seed: options.seed !== false,
    acceptManagedEnv: options.acceptManagedEnv === true,
    envFile: ENV_FILE_RELATIVE,
    useProxy,
    includeBackups: options.includeBackups === true,
  });
}

function setupProfilingEnvironment(options: DevCliOptions): void {
  if (options.profilingCmd)
    process.env.ROTKI_BACKEND_PROFILING_CMD = options.profilingCmd;
  if (options.profilingArgs)
    process.env.ROTKI_BACKEND_PROFILING_ARGS = options.profilingArgs;
}

function exitOnAllocationError<T>(error: unknown): T {
  if (error instanceof PortSlotAllocationError) {
    logger.error(error.message);
    process.exit(1);
  }
  throw error;
}

async function tearDownAndExit(error: unknown, exitCode: number): Promise<never> {
  logger.error(errorMessage(error));
  try {
    await terminateSubprocesses();
  }
  catch (shutdownError) {
    logger.error(`shutdown error: ${errorMessage(shutdownError)}`);
  }
  process.exit(exitCode);
}

async function runDevAction(options: DevCliOptions): Promise<void> {
  try {
    if (await dispatchManagementSubcommand(options))
      process.exit(process.exitCode ?? 0);
  }
  catch (error) {
    exitOnAllocationError(error);
  }

  ensurePrerequisites();
  loadDevEnv();

  const useProxy = shouldUseProxy(options);
  logger.info(`dev-proxy: ${useProxy ? 'on' : 'off'}${options.proxy === undefined ? ' (auto)' : ''}`);

  let instance: InstanceRuntime | null;
  try {
    instance = await resolveInstance(options, useProxy);
  }
  catch (error) {
    return exitOnAllocationError(error);
  }
  if (instance) {
    logger.info(`Instance "${instance.name}" → slot ${instance.slot}, dir ${instance.dir}`);
    logger.info(
      `  ports: backend=${formatPort(instance.ports.restApi)} proxy=${formatPort(instance.ports.proxy)} `
      + `colibri=${formatPort(instance.ports.colibri)} dev=${formatPort(instance.ports.dev)}`,
    );
  }

  registerShutdownHandlers();
  setupProfilingEnvironment(options);

  try {
    await startDevelopmentEnvironment({
      webPort: parsePort(options.webPort, DEFAULT_PORTS.restApi),
      colibriPort: parsePort(options.colibriPort, DEFAULT_PORTS.colibri),
      noElectron: !!options.web,
      profilingArgs: options.profilingArgs,
      profilingCmd: options.profilingCmd,
      instance,
      useProxy,
      onChildExit: () => {
        terminateSubprocesses()
          .catch(error => logger.error(`shutdown error: ${errorMessage(error)}`))
          .finally(() => process.exit(0));
      },
    });
  }
  catch (error) {
    await tearDownAndExit(error, 1);
  }
}

const cli = cac();

cli.command('', 'Start the development environment')
  .option('--web', 'Start without electron as a web service (starts the backend too)')
  .option('--web-port <number>', 'The port to use for the web server', { default: DEFAULT_PORTS.restApi })
  .option('--colibri-port <number>', 'The port to use for the colibri server', { default: DEFAULT_PORTS.colibri })
  .option('--profiling-args <string>', 'Arguments to pass to the backend process (see docs.rotki.com/contribution-guides/code-profiling.html)')
  .option('--profiling-cmd <string>', 'Command used to start the backend process (see docs.rotki.com/contribution-guides/code-profiling.html)')
  .option('--instance [name]', 'Run with an isolated data dir / port slot; --no-instance forces default mode even if INSTANCE_NAME is set')
  .option('--seed', 'Seed the instance data dir from the prod rotki data dir on first run (default: true); pass --no-seed to skip', { default: true })
  .option('--include-backups', 'Include `*.backup` files when seeding (default: skipped to keep the seed lean)')
  .option('--accept-managed-env', 'Consent to dev:web managing INSTANCE_*, VITE_BACKEND_URL, VITE_COLIBRI_URL, DEV_PORT in .env.development.local')
  .option('--proxy', 'Force the dev-proxy on (default: auto, on iff PREMIUM_COMPONENT_DIR is set or async-mock.json exists)')
  .option('--list', 'List dev instances and exit')
  .option('--clean [name]', 'Remove a single instance and exit (name is required; passing --clean without a name shows usage)')
  .option('--clean-all', 'Remove all instances and exit (double-confirm)')
  .option('--prune', 'Remove instances whose worktrees no longer exist (dry-run unless --yes)')
  .option('--repair', 'Rebuild .port-index.json from sidecars (dry-run unless --yes)')
  .option('--older-than <duration>', 'Used with --prune; only consider instances whose lastUsedAt is older (e.g. 30d, 12h, 45m)')
  .option('--yes', 'Skip confirmation prompts for --clean/--clean-all/--prune/--repair')
  .action(runDevAction);

cli.help();
cli.parse();
