import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useAccountingSettingsStore } from '@/modules/settings/use-accounting-settings-store';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import { useSessionSettingsStore } from '@/modules/settings/use-session-settings-store';
import { settingStore, type SettingStoreTag, useSetting } from '@/modules/settings/use-setting';

const stores: Record<SettingStoreTag, () => object> = {
  accounting: useAccountingSettingsStore,
  frontend: useFrontendSettingsStore,
  general: useGeneralSettingsStore,
  session: useSessionSettingsStore,
};

describe('useSetting routing', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should route every key to a store that actually exposes it', () => {
    for (const [key, tag] of Object.entries(settingStore)) {
      const store = stores[tag]();
      expect(key in store, `${key} is not exposed by the ${tag} store`).toBe(true);
    }
  });

  it('should return a readonly ref reflecting the current store value', () => {
    const store = useGeneralSettingsStore();
    const format = useSetting('dateDisplayFormat');
    expect(get(format)).toBe(store.dateDisplayFormat);
  });

  it('should stay in sync when the owning store updates', () => {
    const store = useFrontendSettingsStore();
    const separator = useSetting('thousandSeparator');
    store.update({ thousandSeparator: '_' });
    expect(get(separator)).toBe('_');
  });
});
