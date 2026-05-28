// Public surface of the dev-instance subsystem.
// Internal helpers stay unexported from this barrel; consumers (start-dev.ts,
// copy-data.ts, future scripts) import only the names below.

export {
  clearManagedEnvBlock,
  loadEnvFile,
  MANAGED_ENV_KEYS,
  readManagedInstanceName,
  writeEnvFile,
} from './env-file';

export {
  copyTree,
  type CopyTreeOptions,
  estimateSeedSize,
  freeDiskBytes,
  seedInstance,
  type SeedProgress,
  shouldSkipSeedEntry,
} from './fs-walk';

export { type InstanceRuntime, prepareInstance, type PrepareInstanceOptions } from './instance';

export {
  cleanAll,
  cleanInstance,
  type InstanceSummary,
  listInstances,
  printInstanceList,
  pruneInstances,
  repairRegistry,
} from './lifecycle';

export { baseDataDir } from './paths';

export {
  resolveInstanceDir,
  resolveInstanceParent,
  resolveSeedSource,
  sanitizeName,
} from './paths';

export {
  allocatePortSlot,
  DEFAULT_PORTS,
  INSTANCE_BASE_PORT,
  INSTANCE_SLOT_STEP,
  MAX_PORT,
  type PortName,
  type PortSet,
  portsForSlot,
  PortSlotAllocationError,
  releasePortSlot,
  RESERVED_SLOTS_END,
} from './port-registry';

export { type InstanceMeta, readMetadata, touchLastUsed, writeMetadata } from './sidecar';
