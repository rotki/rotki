import type { Router } from 'vue-router';
import { assert, type Notification, type NotificationAction, NotificationCategory, NotificationGroup, Severity } from '@rotki/common';
import { mockT } from '@test/i18n';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { createMissingApiKeyHandler } from '@/modules/core/messaging/handlers/missing-api-key';

const { mockOpenUrl, mockUpdate } = vi.hoisted(() => ({ mockOpenUrl: vi.fn(), mockUpdate: vi.fn() }));
const mockSuppressList = ref<string[]>([]);
const mockPush = vi.fn();

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: vi.fn(() => ({
    openUrl: mockOpenUrl,
  })),
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: vi.fn(() => ({
    update: mockUpdate,
  })),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => mockSuppressList),
}));

const router = createMock<Router>({ push: mockPush });

function actionsOf(notification: Notification | null | void): (NotificationAction | undefined)[] {
  assert(notification);
  return Array.isArray(notification.action) ? notification.action : [notification.action];
}

function findAction(notification: Notification | null | void, labelPart: string): NotificationAction {
  const action = actionsOf(notification).find(a => a?.label.includes(labelPart));
  assert(action);
  return action;
}

describe('createMissingApiKeyHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(mockSuppressList, []);
    mockUpdate.mockResolvedValue(undefined);
  });

  it('should build a warning notification for etherscan', async () => {
    const handler = createMissingApiKeyHandler(mockT, router);
    const result = await handler.handle({ service: 'etherscan' });

    assert(result);
    expect(result.category).toBe(NotificationCategory.ETHERSCAN);
    expect(result.severity).toBe(Severity.WARNING);
    expect(result.display).toBe(true);
  });

  it('should group per service so repeats collapse but different services stay separate', async () => {
    const handler = createMissingApiKeyHandler(mockT, router);

    const etherscan = await handler.handle({ service: 'etherscan' });
    const blockscout = await handler.handle({ service: 'blockscout' });
    const etherscanAgain = await handler.handle({ service: 'etherscan' });

    assert(etherscan);
    assert(blockscout);
    assert(etherscanAgain);
    expect(etherscan.group).toBe(`${NotificationGroup.MISSING_API_KEY}:etherscan`);
    expect(etherscanAgain.group).toBe(etherscan.group);
    expect(blockscout.group).not.toBe(etherscan.group);
  });

  it('should route to the external service settings from the primary action', async () => {
    const handler = createMissingApiKeyHandler(mockT, router);
    const result = await handler.handle({ service: 'etherscan' });

    const action = findAction(result, 'missing_api_key.action');
    await action.action();

    expect(mockPush).toHaveBeenCalledWith({
      name: '/api-keys/external/',
      query: { service: 'etherscan' },
    });
  });

  it('should offer to change the indexer order for transaction indexers', async () => {
    const handler = createMissingApiKeyHandler(mockT, router);
    const result = await handler.handle({ service: 'etherscan' });

    const action = findAction(result, 'change_indexer_order');
    await action.action();

    expect(mockPush).toHaveBeenCalledWith({ hash: '#indexer', name: '/settings/chains/' });
  });

  it('should offer to open the registration url for blockscout', async () => {
    const handler = createMissingApiKeyHandler(mockT, router);
    const result = await handler.handle({ service: 'blockscout' });

    const action = findAction(result, 'get_key');
    await action.action();

    expect(mockOpenUrl).toHaveBeenCalledOnce();
  });

  it('should not offer a get-key action for etherscan', async () => {
    const handler = createMissingApiKeyHandler(mockT, router);
    const result = await handler.handle({ service: 'etherscan' });

    expect(actionsOf(result).some(a => a?.label.includes('get_key'))).toBe(false);
  });

  it('should present beaconchain as a non-displayed info notification', async () => {
    const handler = createMissingApiKeyHandler(mockT, router);
    const result = await handler.handle({ service: 'beaconchain' });

    assert(result);
    expect(result.category).toBe(NotificationCategory.BEACONCHAIN);
    expect(result.severity).toBe(Severity.INFO);
    expect(result.display).toBe(false);
  });

  it('should include the docs url for thegraph', async () => {
    const handler = createMissingApiKeyHandler(mockT, router);
    const result = await handler.handle({ service: 'thegraph' });

    assert(result);
    expect(result.category).toBe(NotificationCategory.THEGRAPH);
    expect(result.i18nParam?.props?.docsUrl).toBeTruthy();
  });

  it('should fall back to the etherscan config for an unknown service', async () => {
    const handler = createMissingApiKeyHandler(mockT, router);
    const result = await handler.handle({ service: 'unknown-service' });

    assert(result);
    expect(result.category).toBe(NotificationCategory.ETHERSCAN);
  });

  describe('suppress action', () => {
    it('should add the service to the suppress list after confirmation', async () => {
      const handler = createMissingApiKeyHandler(mockT, router);
      const confirmStore = useConfirmStore();
      const result = await handler.handle({ service: 'etherscan' });

      const suppress = findAction(result, 'do_not_show_again');
      await suppress.action();
      expect(confirmStore.visible).toBe(true);

      await confirmStore.confirm();

      expect(mockUpdate).toHaveBeenCalledWith({ suppressMissingKeyMsgServices: ['etherscan'] });
    });

    it('should not update when the service is already suppressed', async () => {
      set(mockSuppressList, ['etherscan']);
      const handler = createMissingApiKeyHandler(mockT, router);
      const confirmStore = useConfirmStore();
      const result = await handler.handle({ service: 'etherscan' });

      await findAction(result, 'do_not_show_again').action();
      await confirmStore.confirm();

      expect(mockUpdate).not.toHaveBeenCalled();
    });

    it('should not update when the confirmation is dismissed', async () => {
      const handler = createMissingApiKeyHandler(mockT, router);
      const confirmStore = useConfirmStore();
      const result = await handler.handle({ service: 'etherscan' });

      await findAction(result, 'do_not_show_again').action();
      await confirmStore.dismiss();

      expect(mockUpdate).not.toHaveBeenCalled();
    });
  });
});
