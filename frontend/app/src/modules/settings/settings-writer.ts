import type { ActionStatus } from '@/modules/core/common/action';
import type { SettingKey, SettingValue } from '@/modules/settings/use-setting';
import { Channel, type RegistryEntry, settingsRegistry } from '@/modules/settings/settings-registry';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

/** Keys whose value is derived by a `project` transform (e.g. `currencySymbol`, `shouldShowAmount`). */
type ProjectedKey = {
  [K in SettingKey]: (typeof settingsRegistry)[K] extends { project: (settings: any) => unknown } ? K : never;
}[SettingKey];

/**
 * A setting that can be written. Projected keys are read-only derivations of another field (they have
 * no wire representation of their own), so they are excluded here rather than by a hardcoded list.
 */
export type WritableSettingKey = Exclude<SettingKey, ProjectedKey>;

type SettingsPatch = Partial<{ [K in WritableSettingKey]: SettingValue<K> }>;

/**
 * Maps a logical key/value to its wire `{ [wireKey]: wireValue }` shape using the registry's optional
 * `wireKey`/`encode` overrides. Keys without overrides are 1:1 (`{ [key]: value }`).
 */
function toWirePayload(key: WritableSettingKey, value: unknown): Record<string, unknown> {
  const entry: RegistryEntry = settingsRegistry[key];
  const wireKey = entry.wireKey ?? key;
  const wireValue = entry.encode ? entry.encode(value) : value;
  return { [wireKey]: wireValue };
}

interface ChannelPartition {
  readonly general: Record<string, unknown>;
  readonly frontend: Record<string, unknown>;
  readonly session: Record<string, unknown>;
}

/** Splits a patch into one merged wire payload per channel. */
function partitionByChannel(patch: SettingsPatch): ChannelPartition {
  const general: Record<string, unknown> = {};
  const frontend: Record<string, unknown> = {};
  const session: Record<string, unknown> = {};

  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- Object.keys widens to string[]; the patch owns exactly WritableSettingKey entries
  for (const key of Object.keys(patch) as WritableSettingKey[]) {
    const value = patch[key];
    if (value === undefined)
      continue;
    const channel = settingsRegistry[key].channel;
    if (channel === Channel.general || channel === Channel.accounting)
      Object.assign(general, toWirePayload(key, value));
    else if (channel === Channel.frontend)
      Object.assign(frontend, toWirePayload(key, value));
    else
      Object.assign(session, toWirePayload(key, value));
  }

  return { frontend, general, session };
}

interface UseSettingsWriterReturn {
  write: <K extends WritableSettingKey>(key: K, value: SettingValue<K>) => Promise<ActionStatus>;
  writeMany: (patch: SettingsPatch) => Promise<ActionStatus>;
}

/**
 * Imperative, typed write facade over `useSettingsOperations`. Callers write a logical key and its
 * read-type value; the writer derives the owning channel from the `settingStore` routing table (the
 * same table `useSetting` reads through), applies the wire-key/encode overrides, and dispatches to the
 * right per-channel operation. Network I/O, batching, premium-flag dispatch and cross-field effects
 * stay inside `useSettingsOperations`; this layer only routes.
 */
export function useSettingsWriter(): UseSettingsWriterReturn {
  const { update, updateFrontendSetting } = useSettingsOperations();
  const { updateSession } = useSettingsRepo();

  async function write<K extends WritableSettingKey>(key: K, value: SettingValue<K>): Promise<ActionStatus> {
    const channel = settingsRegistry[key].channel;
    switch (channel) {
      case Channel.general:
      case Channel.accounting:
        return update(toWirePayload(key, value));
      case Channel.frontend:
        return updateFrontendSetting(toWirePayload(key, value));
      case Channel.session:
        return updateSession(toWirePayload(key, value));
    }
  }

  async function writeMany(patch: SettingsPatch): Promise<ActionStatus> {
    const { frontend, general, session } = partitionByChannel(patch);

    const results: ActionStatus[] = [];
    if (Object.keys(general).length > 0)
      results.push(await update(general));
    if (Object.keys(frontend).length > 0)
      results.push(await updateFrontendSetting(frontend));
    if (Object.keys(session).length > 0)
      results.push(updateSession(session));

    return results.find(result => !result.success) ?? { success: true };
  }

  return {
    write,
    writeMany,
  };
}
