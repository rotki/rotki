import { assert, type Notification, type NotificationAction, NotificationGroup } from '@rotki/common';
import { mockT } from '@test/i18n';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { createNoAvailableIndexersHandler } from '@/modules/core/messaging/handlers/no-available-indexers';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

const updateFrontendSetting = vi.fn();

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): Record<string, ReturnType<typeof vi.fn>> => ({
    applyFrontendSettingLocal: vi.fn(),
    enableModule: vi.fn(),
    setKrakenAccountType: vi.fn(),
    update: vi.fn(),
    updateFrontendSetting,
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): { getChainName: (chain: string) => string } => ({
    getChainName: (chain: string): string => chain.toUpperCase(),
  }),
}));

const router = { push: vi.fn() };

describe('createNoAvailableIndexersHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    updateFrontendSetting.mockReset();
    updateFrontendSetting.mockResolvedValue({ success: true });
  });

  it('should return a notification when the chain is not suppressed', async () => {
    const handler = createNoAvailableIndexersHandler(mockT, router);

    const result = await handler.handle({ chain: 'optimism' });

    expect(result).toMatchObject({
      group: NotificationGroup.NO_AVAILABLE_INDEXERS,
    });
  });

  it('should route to the EVM indexer settings when the user clicks the configure action', async () => {
    const handler = createNoAvailableIndexersHandler(mockT, router);

    const result = await handler.handle({ chain: 'binance_sc' });
    assert(result);
    const actions = Array.isArray(result.action) ? result.action : [result.action];
    const configureAction = actions.find(a => a && a.label.includes('action') && !a.label.includes('do_not_show_again'));
    assert(configureAction);

    await configureAction.action();

    expect(router.push).toHaveBeenCalledWith({ path: '/settings/evm', hash: '#indexer' });
  });

  it('should return null when the chain is in the suppression list', async () => {
    const handler = createNoAvailableIndexersHandler(mockT, router);
    const store = useFrontendSettingsStore();
    store.update({ suppressNoIndexerChains: ['binance_sc'] });

    const result = await handler.handle({ chain: 'binance_sc' });

    expect(result).toBeNull();
  });

  function getSuppressAction(notification: Notification | null | void): NotificationAction {
    assert(notification);
    const actions = Array.isArray(notification.action) ? notification.action : [notification.action];
    const suppressAction = actions.find(a => a && a.label.includes('do_not_show_again'));
    assert(suppressAction);
    return suppressAction;
  }

  it('should append the chain to suppressNoIndexerChains when the user confirms', async () => {
    const handler = createNoAvailableIndexersHandler(mockT, router);
    const confirmStore = useConfirmStore();

    const result = await handler.handle({ chain: 'binance_sc' });
    const suppressAction = getSuppressAction(result);

    await suppressAction.action();
    expect(confirmStore.visible).toBe(true);

    await confirmStore.confirm();

    expect(updateFrontendSetting).toHaveBeenCalledWith({ suppressNoIndexerChains: ['binance_sc'] });
  });

  it('should not update the suppression list when the user dismisses the confirmation', async () => {
    const handler = createNoAvailableIndexersHandler(mockT, router);
    const confirmStore = useConfirmStore();

    const result = await handler.handle({ chain: 'binance_sc' });
    const suppressAction = getSuppressAction(result);

    await suppressAction.action();
    await confirmStore.dismiss();

    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should skip the update when the chain was added to the list between notification and confirmation', async () => {
    const handler = createNoAvailableIndexersHandler(mockT, router);
    const store = useFrontendSettingsStore();
    const confirmStore = useConfirmStore();

    const result = await handler.handle({ chain: 'binance_sc' });
    const suppressAction = getSuppressAction(result);

    store.update({ suppressNoIndexerChains: ['binance_sc'] });
    await suppressAction.action();
    await confirmStore.confirm();

    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });
});
