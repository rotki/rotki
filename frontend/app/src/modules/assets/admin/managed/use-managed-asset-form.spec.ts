import type { SupportedAsset } from '@rotki/common';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, ref, type Ref } from 'vue';
import { EVM_TOKEN } from '@/modules/assets/types';
import { useManagedAssetForm } from './use-managed-asset-form';

const { getAssetTypes, queryAllAssets, setMessage } = await vi.hoisted(async () => ({
  getAssetTypes: vi.fn(),
  queryAllAssets: vi.fn(),
  setMessage: vi.fn(),
}));

vi.mock('@/modules/assets/api/use-asset-management-api', () => ({
  useAssetManagementApi: (): Record<string, unknown> => ({ getAssetTypes, queryAllAssets }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, unknown> => ({ setMessage }),
}));

const wrappers: VueWrapper[] = [];

function asset(identifier: string, symbol = 'ETH'): SupportedAsset {
  return { identifier, isRebasing: false, symbol };
}

function collectionOf(data: SupportedAsset[]): Record<string, unknown> {
  return { data, found: data.length, limit: -1, total: data.length };
}

async function mountForm(identifier: Ref<string | null> = ref(null)): Promise<ReturnType<typeof useManagedAssetForm>> {
  let captured: ReturnType<typeof useManagedAssetForm> | undefined;
  let setupError: Error | undefined;
  const Host = defineComponent({
    setup(): () => ReturnType<typeof h> {
      try {
        captured = useManagedAssetForm(identifier);
      }
      catch (error) {
        setupError = error instanceof Error ? error : new Error(String(error));
      }
      return (): ReturnType<typeof h> => h('div');
    },
  });

  wrappers.push(mount(Host));
  await flushPromises();
  if (setupError)
    throw setupError;
  return captured!;
}

describe('modules/assets/admin/managed/useManagedAssetForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getAssetTypes.mockResolvedValue(['evm token', 'custom asset']);
    queryAllAssets.mockResolvedValue(collectionOf([]));
  });

  afterEach(() => {
    while (wrappers.length > 0)
      wrappers.pop()?.unmount();
  });

  describe('the asset types it offers', () => {
    it('should read them once on mount', async () => {
      const { assetTypes } = await mountForm();

      expect(getAssetTypes).toHaveBeenCalledOnce();
      expect(get(assetTypes)).toEqual(['evm token', 'custom asset']);
    });

    it('should report a failure but still let the form open', async () => {
      getAssetTypes.mockRejectedValue(new Error('offline'));

      const { add, assetTypes, modelValue } = await mountForm();

      expect(setMessage).toHaveBeenCalledOnce();
      expect(get(assetTypes)).toEqual([]);

      add();
      expect(get(modelValue)).toBeDefined();
    });
  });

  describe('adding an asset', () => {
    it('should open the form on a blank evm token', async () => {
      const { add, modelValue } = await mountForm();

      add();

      expect(get(modelValue)?.assetType).toBe(EVM_TOKEN);
      expect(get(modelValue)?.identifier).toBe('');
    });

    it('should be a create, not an edit', async () => {
      const { add, editMode } = await mountForm();

      add();

      expect(get(editMode)).toBe(false);
    });

    it('should start from a fresh asset each time, not the one last edited', async () => {
      const { add, edit, modelValue } = await mountForm();

      edit(asset('eip155:1/erc20:0xdead', 'DEAD'));
      add();

      expect(get(modelValue)?.identifier).toBe('');
      expect(get(modelValue)?.symbol).toBeUndefined();
    });
  });

  describe('editing an asset', () => {
    it('should open the form on the asset it was handed', async () => {
      const { edit, editMode, modelValue } = await mountForm();

      edit(asset('eip155:1/erc20:0xdead', 'DEAD'));

      expect(get(modelValue)?.identifier).toBe('eip155:1/erc20:0xdead');
      expect(get(editMode)).toBe(true);
    });

    it('should fetch an asset it was given only the identifier for', async () => {
      queryAllAssets.mockResolvedValue(collectionOf([asset('eip155:1/erc20:0xdead', 'DEAD')]));
      const { editAsset, editMode, modelValue } = await mountForm();

      await editAsset('eip155:1/erc20:0xdead');

      expect(queryAllAssets).toHaveBeenCalledWith({
        identifiers: ['eip155:1/erc20:0xdead'],
        limit: 1,
        offset: 0,
      });
      expect(get(modelValue)?.identifier).toBe('eip155:1/erc20:0xdead');
      expect(get(editMode)).toBe(true);
    });

    it('should leave the form closed, and not in edit mode, for an identifier the backend does not know', async () => {
      const { editAsset, editMode, modelValue } = await mountForm();

      await editAsset('eip155:1/erc20:0xmissing');

      expect(get(modelValue)).toBeUndefined();
      expect(get(editMode)).toBe(false);
    });

    it('should not ask the backend for a null identifier', async () => {
      const { editAsset } = await mountForm();

      await editAsset(null);

      expect(queryAllAssets).not.toHaveBeenCalled();
    });
  });

  describe('following the route', () => {
    it('should reopen the form when the identifier changes', async () => {
      queryAllAssets.mockResolvedValue(collectionOf([asset('eip155:1/erc20:0xbeef', 'BEEF')]));
      const identifier = ref<string | null>(null);
      const { modelValue } = await mountForm(identifier);

      set(identifier, 'eip155:1/erc20:0xbeef');
      await flushPromises();

      expect(get(modelValue)?.identifier).toBe('eip155:1/erc20:0xbeef');
    });

    it('should leave the form alone when the identifier clears', async () => {
      const identifier = ref<string | null>('eip155:1/erc20:0xbeef');
      const { modelValue } = await mountForm(identifier);
      queryAllAssets.mockClear();

      set(identifier, null);
      await flushPromises();

      expect(queryAllAssets).not.toHaveBeenCalled();
      expect(get(modelValue)).toBeUndefined();
    });
  });
});
