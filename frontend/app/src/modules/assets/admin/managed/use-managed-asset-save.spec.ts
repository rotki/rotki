import type { Ref } from 'vue';
import { EvmTokenKind, type SupportedAsset, type UnderlyingToken } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { EVM_TOKEN } from '@/modules/assets/types';

const addAsset = vi.fn<(asset: Record<string, unknown>) => Promise<{ identifier: string }>>();
const editAsset = vi.fn<(asset: Record<string, unknown>) => Promise<boolean>>();

vi.mock('@/modules/assets/api/use-asset-management-api', () => ({
  useAssetManagementApi: vi.fn().mockReturnValue({
    get addAsset() {
      return addAsset;
    },
    get editAsset() {
      return editAsset;
    },
  }),
}));

const { useManagedAssetSave } = await import('@/modules/assets/admin/managed/use-managed-asset-save');

describe('useManagedAssetSave', () => {
  let asset: Ref<SupportedAsset>;
  let underlyingTokens: Ref<UnderlyingToken[]>;

  beforeEach(() => {
    addAsset.mockReset();
    editAsset.mockReset();
    addAsset.mockResolvedValue({ identifier: 'minted-by-the-backend' });
    editAsset.mockResolvedValue(true);
    asset = ref<SupportedAsset>({
      address: '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
      assetType: EVM_TOKEN,
      decimals: 6,
      evmChain: 'ethereum',
      identifier: 'existing-identifier',
      isRebasing: false,
      name: 'USD Coin',
      symbol: 'USDC',
      tokenKind: EvmTokenKind.ERC20,
    });
    underlyingTokens = ref<UnderlyingToken[]>([]);
  });

  it('should edit under the identifier the asset already has', async () => {
    const { saveAsset } = useManagedAssetSave({ asset, editMode: true, underlyingTokens });

    const identifier = await saveAsset();

    expect(identifier).toBe('existing-identifier');
    expect(editAsset).toHaveBeenCalledWith(
      expect.objectContaining({ identifier: 'existing-identifier', symbol: 'USDC' }),
    );
    expect(addAsset).not.toHaveBeenCalled();
  });

  it('should add without an identifier and answer with the minted one', async () => {
    const { saveAsset } = useManagedAssetSave({ asset, editMode: false, underlyingTokens });

    const identifier = await saveAsset();

    expect(identifier).toBe('minted-by-the-backend');
    // The backend mints it, so sending the empty one the form carries would be a lie.
    expect(addAsset.mock.calls[0][0]).not.toHaveProperty('identifier');
    expect(editAsset).not.toHaveBeenCalled();
  });

  it('should send the underlying tokens the form is holding', async () => {
    const token: UnderlyingToken = {
      address: '0x6B175474E89094C44Da98b954EedeAC495271d0F',
      tokenKind: EvmTokenKind.ERC20,
      weight: '100',
    };
    set(underlyingTokens, [token]);
    const { saveAsset } = useManagedAssetSave({ asset, editMode: true, underlyingTokens });

    await saveAsset();

    expect(editAsset).toHaveBeenCalledWith(
      expect.objectContaining({ underlyingTokens: [token] }),
    );
  });

  it('should read the mode when it saves, not when it is set up', async () => {
    const editMode = ref<boolean>(false);
    const { saveAsset } = useManagedAssetSave({ asset, editMode, underlyingTokens });

    set(editMode, true);
    await saveAsset();

    expect(editAsset).toHaveBeenCalledOnce();
  });
});
