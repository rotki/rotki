import { createPinia, type Pinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useAccountingSettingsStore } from '@/modules/settings/use-accounting-settings-store';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import { useSessionSettingsStore } from '@/modules/settings/use-session-settings-store';

/**
 * Contract guard for the settings-store refactor (see "Settings Registry" plan, phase A).
 *
 * ~210 files read these stores via storeToRefs, so the exported surface (the set of keys and
 * whether each is an action or a value/getter) is the public contract. This test freezes that
 * surface: any phase-A internal refactor (e.g. swapping hand-written useComputedRef lines for a
 * derived projection) must leave these snapshots byte-identical. A diff here means the refactor
 * changed the public shape and would break consumers.
 */
function shapeOf(store: object): Record<string, 'action' | 'value'> {
  const shape: Record<string, 'action' | 'value'> = {};
  // Iterate entries rather than keys + index: a pinia Store type has no string index signature,
  // so `store[key]` would force a `Record<string, unknown>` param and fail to typecheck. Sort by
  // key with an explicit comparator equivalent to the default string sort to keep the snapshot order.
  const entries = Object.entries(store).sort(([a], [b]) => {
    if (a < b)
      return -1;
    if (a > b)
      return 1;
    return 0;
  });
  for (const [key, value] of entries) {
    if (key.startsWith('$') || key.startsWith('_'))
      continue;
    shape[key] = typeof value === 'function' ? 'action' : 'value';
  }
  return shape;
}

describe('settings store exported shape', () => {
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createPinia();
  });

  it('should keep the frontend settings store surface stable', () => {
    expect(shapeOf(useFrontendSettingsStore(pinia))).toMatchSnapshot();
  });

  it('should keep the general settings store surface stable', () => {
    expect(shapeOf(useGeneralSettingsStore(pinia))).toMatchSnapshot();
  });

  it('should keep the accounting settings store surface stable', () => {
    expect(shapeOf(useAccountingSettingsStore(pinia))).toMatchSnapshot();
  });

  it('should keep the session settings store surface stable', () => {
    expect(shapeOf(useSessionSettingsStore(pinia))).toMatchSnapshot();
  });
});
