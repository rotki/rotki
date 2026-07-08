import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { registryEntries } from '@/modules/settings/settings-registry';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { useSetting } from '@/modules/settings/use-setting';

describe('useSetting routing', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should return a readonly ref reflecting the current repo value', () => {
    const repo = useSettingsRepo();
    const format = useSetting('dateDisplayFormat');
    expect(get(format)).toBe(repo.general.dateDisplayFormat);
  });

  it('should stay in sync when the owning channel updates', () => {
    const repo = useSettingsRepo();
    const separator = useSetting('thousandSeparator');
    repo.updateFrontend({ thousandSeparator: '_' });
    expect(get(separator)).toBe('_');
  });

  it('should apply the projection for derived keys', () => {
    const repo = useSettingsRepo();
    const symbol = useSetting('currencySymbol');
    expect(get(symbol)).toBe(repo.general.mainCurrency.tickerSymbol);
  });

  it('should not give a projected (read-only) key a wire mapping', () => {
    for (const [key, entry] of registryEntries()) {
      if (!entry.project)
        continue;
      expect(entry.wireKey, `${key} is projected but declares a wireKey`).toBeUndefined();
      expect(entry.encode, `${key} is projected but declares an encode`).toBeUndefined();
    }
  });
});
