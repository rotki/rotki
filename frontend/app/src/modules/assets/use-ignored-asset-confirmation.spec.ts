import type { ActionStatus } from '@/modules/core/common/action';
import type { ConfirmChoice } from '@/modules/core/common/use-confirm-store';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useIgnoredAssetConfirmation } from '@/modules/assets/use-ignored-asset-confirmation';

const spies = vi.hoisted(() => ({
  ask: vi.fn<(message: object) => Promise<ConfirmChoice>>(),
  ignoreAsset: vi.fn<(assets: string[] | string) => Promise<ActionStatus>>(),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): object => ({ ask: spies.ask }),
}));
vi.mock('@/modules/assets/use-ignored-asset-operations', () => ({
  useIgnoredAssetOperations: (): object => ({ ignoreAsset: spies.ignoreAsset }),
}));

describe('useIgnoredAssetConfirmation', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should settle only after the confirmed ignore has finished', async () => {
    spies.ask.mockResolvedValue('confirm');
    let finishIgnore: (status: ActionStatus) => void = () => {};
    spies.ignoreAsset.mockReturnValue(new Promise<ActionStatus>((resolve) => {
      finishIgnore = resolve;
    }));
    const onSuccess = vi.fn<() => void>();
    let settled = false;

    const run = useIgnoredAssetConfirmation().ignoreAssetWithConfirmation('ETH', 'Ether', onSuccess).then(() => {
      settled = true;
    });
    await vi.waitFor(() => expect(spies.ignoreAsset).toHaveBeenCalledWith('ETH'));
    expect(settled).toBe(false);

    finishIgnore({ success: true });
    await run;
    expect(onSuccess).toHaveBeenCalledOnce();
  });

  it('should not ignore when the question is dismissed', async () => {
    spies.ask.mockResolvedValue('dismiss');
    const onSuccess = vi.fn<() => void>();

    await useIgnoredAssetConfirmation().ignoreAssetWithConfirmation('ETH', 'Ether', onSuccess);

    expect(spies.ignoreAsset).not.toHaveBeenCalled();
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it('should skip the success callback when the ignore fails', async () => {
    spies.ask.mockResolvedValue('confirm');
    spies.ignoreAsset.mockResolvedValue({ message: 'boom', success: false });
    const onSuccess = vi.fn<() => void>();

    await useIgnoredAssetConfirmation().ignoreAssetWithConfirmation('ETH', 'Ether', onSuccess);

    expect(onSuccess).not.toHaveBeenCalled();
  });
});
