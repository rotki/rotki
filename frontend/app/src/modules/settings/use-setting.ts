import type { ChannelTypeMap, RegistryEntry } from '@/modules/settings/settings-channels';
import { type Ref, toRef } from 'vue';
import { settingsRegistry } from '@/modules/settings/settings-registry';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

/** The logical key of every registered setting; the single source of setting names. */
export type SettingKey = keyof typeof settingsRegistry;

type RegistryOf<K extends SettingKey> = (typeof settingsRegistry)[K];

/** The wire field a key reads from: its explicit `wireKey` when renamed, otherwise the logical key. */
type WireField<K extends SettingKey> = RegistryOf<K> extends { wireKey: infer W extends string } ? W : K;

/**
 * The read value type for a setting, derived from its registry entry: a projected key resolves to
 * its `project` return type; every other key resolves to the field its channel object exposes.
 */
export type SettingValue<K extends SettingKey> =
  RegistryOf<K> extends { project: (settings: any) => infer V }
    ? V
    : WireField<K> extends keyof ChannelTypeMap[RegistryOf<K>['channel']]
      ? ChannelTypeMap[RegistryOf<K>['channel']][WireField<K>]
      : never;

/**
 * Reads a single setting by its logical key and returns a readonly ref to it, without the caller
 * having to know or import the owning store. This is the read primitive of the settings surface;
 * domain facades (e.g. `useAmountDisplaySettings`) bundle several of these for settings that are
 * consumed together.
 *
 * The value is projected out of the settings repo's channel object named by the key's registry
 * entry (applying its `project` transform, or reading its `wireKey` field). The returned ref is a
 * getter ref (no per-key reactive effect) and stays in sync when the repo replaces a channel object.
 */
export function useSetting<K extends SettingKey>(key: K): Readonly<Ref<SettingValue<K>>> {
  const repo = useSettingsRepo();
  const entry: RegistryEntry = settingsRegistry[key];
  const project = entry.project;
  const field = entry.wireKey ?? key;
  const read = (): SettingValue<K> => {
    // `repo[entry.channel]` is the union of the four parsed channel objects; `Reflect.get` reads the
    // dynamic `field` off it without a `Record` cast. The registry guarantees this resolves to the
    // key's value type, but that can't be proven for a generic `K`, so assert once here (the only
    // assertion behind this typed facade, same idea as pinia's storeToRefs).
    const value: unknown = project ? project(repo[entry.channel]) : Reflect.get(repo[entry.channel], field);
    // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- registry guarantees the resolved value is SettingValue<K>; use-setting.spec verifies the mapping at runtime
    return value as SettingValue<K>;
  };
  return toRef(read);
}
