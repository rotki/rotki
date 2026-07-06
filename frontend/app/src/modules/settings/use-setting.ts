import { type Ref, toRef } from 'vue';
import { useAccountingSettingsStore } from '@/modules/settings/use-accounting-settings-store';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import { useSessionSettingsStore } from '@/modules/settings/use-session-settings-store';

const storeFactories = {
  accounting: useAccountingSettingsStore,
  frontend: useFrontendSettingsStore,
  general: useGeneralSettingsStore,
  session: useSessionSettingsStore,
} as const;

export type SettingStoreTag = keyof typeof storeFactories;

/**
 * Explicit routing from a logical setting key to the store that owns it. This is the single place
 * that knows where a setting lives: `useSetting` and every domain facade built on it read through
 * here, so when the backing store is later replaced the routing changes in exactly one spot.
 *
 * The table grows as consumers migrate onto `useSetting` — add a key here the first time a consumer
 * needs it. Keys are grouped by their owning store and kept alphabetical within each group. A key
 * must exist on the store it is mapped to; `use-setting.spec.ts` asserts this at runtime.
 */
export const settingStore = {
  // general
  currency: 'general',
  currencySymbol: 'general',
  dateDisplayFormat: 'general',
  displayDateInLocaltime: 'general',
  floatingPrecision: 'general',
  // frontend
  abbreviateNumber: 'frontend',
  amountRoundingMode: 'frontend',
  currencyLocation: 'frontend',
  decimalSeparator: 'frontend',
  minimumDigitToBeAbbreviated: 'frontend',
  scrambleData: 'frontend',
  scrambleMultiplier: 'frontend',
  shouldShowAmount: 'frontend',
  subscriptDecimals: 'frontend',
  thousandSeparator: 'frontend',
  valueRoundingMode: 'frontend',
} as const satisfies Record<string, SettingStoreTag>;

export type SettingKey = keyof typeof settingStore;

type StoreInstance<T extends SettingStoreTag> = ReturnType<(typeof storeFactories)[T]>;

/** The value the owning store exposes for `key`, read through the store proxy (already unwrapped). */
export type SettingValue<K extends SettingKey> =
  StoreInstance<(typeof settingStore)[K]>[K & keyof StoreInstance<(typeof settingStore)[K]>];

/**
 * Reads a single setting by its logical key and returns a readonly ref to it, without the caller
 * having to know or import the owning store. This is the read primitive of the settings surface;
 * domain facades (e.g. `useAmountDisplaySettings`) bundle several of these for settings that are
 * consumed together.
 *
 * The returned ref is a getter ref (no per-key reactive effect) and stays in sync when the store
 * replaces its whole settings object, mirroring `toSettingsRefs`.
 */
export function useSetting<K extends SettingKey>(key: K): Readonly<Ref<SettingValue<K>>> {
  const store = storeFactories[settingStore[key]]();
  // `store` is the union of the four store instance types; the routing table guarantees `key`
  // indexes the resolved member, but TS cannot prove that for a generic `K`. Read through a getter
  // ref and assert the element type once, behind this typed facade (same pattern as toSettingsRefs).
  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- routing table guarantees key exists on the resolved store
  return toRef(() => (store as unknown as Record<K, SettingValue<K>>)[key]);
}
