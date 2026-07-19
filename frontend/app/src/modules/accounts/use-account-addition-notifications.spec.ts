import type { AccountPayload } from '@/modules/accounts/blockchain-accounts';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAccountAdditionNotifications } from './use-account-addition-notifications';
import '@test/i18n';

const h = vi.hoisted(() => ({
  notifyError: vi.fn(),
  notifyInfo: vi.fn(),
  notifyWarning: vi.fn(),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({
    notifyError: h.notifyError,
    notifyInfo: h.notifyInfo,
    notifyWarning: h.notifyWarning,
  })),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({ getChainName: (chain: string): string => chain })),
}));

const account: AccountPayload = { address: '0xabc', tags: null };

describe('useAccountAdditionNotifications', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('notifyUser', () => {
    it('should notify with a chain list when not all chains were used', () => {
      const { notifyUser } = useAccountAdditionNotifications();
      notifyUser({ account, chains: ['eth', 'optimism'], isAll: false });
      expect(h.notifyInfo).toHaveBeenCalledOnce();
      const [, message] = h.notifyInfo.mock.calls[0];
      expect(message).toContain('- eth');
      expect(message).toContain('- optimism');
    });

    it('should notify without a chain list when all chains were used', () => {
      const { notifyUser } = useAccountAdditionNotifications();
      notifyUser({ account, chains: ['eth'], isAll: true });
      expect(h.notifyInfo).toHaveBeenCalledOnce();
      const [, message] = h.notifyInfo.mock.calls[0];
      expect(message).not.toContain('- eth');
    });
  });

  describe('notifyFailedToAddAddress', () => {
    it('should notify an error using EVM as the default blockchain', () => {
      const { notifyFailedToAddAddress } = useAccountAdditionNotifications();
      notifyFailedToAddAddress([account], 1);
      expect(h.notifyError).toHaveBeenCalledOnce();
    });

    it('should resolve the chain name for a specific blockchain', () => {
      const { notifyFailedToAddAddress } = useAccountAdditionNotifications();
      notifyFailedToAddAddress([account], 1, 'eth');
      expect(h.notifyError).toHaveBeenCalledOnce();
    });
  });

  describe('createFailureNotification', () => {
    it('should not notify when there are no failures', () => {
      const { createFailureNotification } = useAccountAdditionNotifications();
      createFailureNotification({}, account);
      expect(h.notifyWarning).not.toHaveBeenCalled();
    });

    it('should warn when there was no activity', () => {
      const { createFailureNotification } = useAccountAdditionNotifications();
      createFailureNotification({ noActivity: { '0xabc': ['eth'] } }, account);
      expect(h.notifyWarning).toHaveBeenCalledOnce();
      const [, message] = h.notifyWarning.mock.calls[0];
      expect(message).toContain('- eth');
      expect(message).toContain('no_activity_hint');
    });

    it('should warn for eth contracts and existing accounts', () => {
      const { createFailureNotification } = useAccountAdditionNotifications();
      createFailureNotification({ ethContracts: ['0xabc'], existed: { '0xabc': ['optimism'] } }, account);
      expect(h.notifyWarning).toHaveBeenCalledOnce();
      expect(h.notifyWarning.mock.calls[0][1]).not.toContain('no_activity_hint');
    });

    it('should skip a single binance_sc failure', () => {
      const { createFailureNotification } = useAccountAdditionNotifications();
      createFailureNotification({ failed: { '0xabc': ['binance_sc'] } }, account);
      expect(h.notifyWarning).not.toHaveBeenCalled();
    });

    it('should warn for a non-binance failed chain', () => {
      const { createFailureNotification } = useAccountAdditionNotifications();
      createFailureNotification({ failed: { '0xabc': ['eth', 'binance_sc'] } }, account);
      expect(h.notifyWarning).toHaveBeenCalledOnce();
    });
  });
});
