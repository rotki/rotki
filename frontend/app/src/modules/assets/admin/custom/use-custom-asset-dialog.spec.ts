import type { CustomAsset } from '@/modules/assets/types';
import { flushPromises } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type Ref, ref, shallowRef } from 'vue';
import { useCustomAssetDialog } from './use-custom-asset-dialog';

interface RouteHolder {
  route?: Ref<{ query: Record<string, string> }>;
}

let assets: Ref<CustomAsset[]>;
let identifier: Ref<string | null>;

const { held, replace } = vi.hoisted(() => {
  const held: RouteHolder = {};
  return {
    held,
    replace: vi.fn(async () => Promise.resolve()),
  };
});

vi.mock('vue-router', async () => {
  const { ref: actualRef } = await vi.importActual<typeof import('vue')>('vue');
  held.route = actualRef({ query: {} });
  return {
    useRoute: (): unknown => held.route,
    useRouter: (): Record<string, unknown> => ({ replace }),
  };
});

function asset(overrides: Partial<CustomAsset> = {}): CustomAsset {
  return {
    customAssetType: 'real estate',
    identifier: 'custom-1',
    name: 'A house',
    notes: '',
    ...overrides,
  };
}

let scope: ReturnType<typeof effectScope>;

function dialog(): ReturnType<typeof useCustomAssetDialog> {
  scope = effectScope();
  return scope.run(() => useCustomAssetDialog({ assets, identifier }))!;
}

function setQuery(query: Record<string, string>): void {
  assert(held.route);
  set(held.route, { query });
}

describe('modules/assets/admin/custom/useCustomAssetDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    assets = ref<CustomAsset[]>([]);
    identifier = shallowRef<string | null>(null);
    setQuery({});
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('the add and edit dialog', () => {
    it('should open on a blank asset to add', () => {
      const { add, modelEditableItem, modelOpenDialog } = dialog();
      add();

      expect(get(modelOpenDialog)).toBe(true);
      expect(get(modelEditableItem)).toBeNull();
    });

    it('should open on an existing asset to edit', () => {
      const existing = asset({ identifier: 'custom-9' });

      const { edit, modelEditableItem, modelOpenDialog } = dialog();
      edit(existing);

      expect(get(modelOpenDialog)).toBe(true);
      expect(get(modelEditableItem)).toEqual(existing);
    });

    it('should go back to adding after an edit', () => {
      const { add, edit, modelEditableItem } = dialog();
      edit(asset());
      add();

      expect(get(modelEditableItem)).toBeNull();
    });
  });

  describe('opening an asset the route names', () => {
    it('should edit the one whose identifier matches', () => {
      const wanted = asset({ identifier: 'custom-2', name: 'A boat' });
      set(assets, [asset(), wanted]);

      const { editAsset, modelEditableItem, modelOpenDialog } = dialog();
      editAsset('custom-2');

      expect(get(modelOpenDialog)).toBe(true);
      expect(get(modelEditableItem)).toEqual(wanted);
    });

    it('should do nothing for an identifier the page does not hold', () => {
      set(assets, [asset()]);

      const { editAsset, modelOpenDialog } = dialog();
      editAsset('custom-absent');

      expect(get(modelOpenDialog)).toBe(false);
    });

    it('should do nothing without an identifier', () => {
      set(assets, [asset()]);

      const { editAsset, modelOpenDialog } = dialog();
      editAsset(null);

      expect(get(modelOpenDialog)).toBe(false);
    });

    it('should follow the identifier when the route changes it', async () => {
      const wanted = asset({ identifier: 'custom-3' });
      set(assets, [asset(), wanted]);

      const { modelEditableItem } = dialog();
      set(identifier, 'custom-3');
      await flushPromises();

      expect(get(modelEditableItem)).toEqual(wanted);
    });
  });

  describe('an ?add= link', () => {
    it('should open the dialog and clear the query', async () => {
      setQuery({ add: 'true' });

      const { consumeAddQuery, modelOpenDialog } = dialog();
      await consumeAddQuery();

      expect(get(modelOpenDialog)).toBe(true);
      expect(replace).toHaveBeenCalledWith({ query: {} });
    });

    it('should do nothing when the query does not ask for it', async () => {
      const { consumeAddQuery, modelOpenDialog } = dialog();
      await consumeAddQuery();

      expect(get(modelOpenDialog)).toBe(false);
      expect(replace).not.toHaveBeenCalled();
    });
  });
});
