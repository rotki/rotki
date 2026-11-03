import type { BankAuthChallenge } from '@/modules/banks/types';
import { createMock } from '@test/utils/create-mock';
import { describe, expect, it } from 'vitest';
import { BankConnectionState, bankConnectionState, bankConnectionStatus } from '@/modules/banks/bank-connection-state';

type SyncStatus = Parameters<typeof bankConnectionState>[0]['syncStatus'];

function withStatus(status: Partial<SyncStatus>): { syncStatus: SyncStatus } {
  return { syncStatus: { authChallenge: null, authExpired: false, lastError: null, lastSyncTs: null, running: false, ...status } };
}

const challenge = createMock<BankAuthChallenge>();

describe('bank connection state', () => {
  it('should rank a pending TAN above an expired one, and both above an older failure', () => {
    expect(bankConnectionState(withStatus({ authChallenge: challenge, authExpired: true, lastError: 'boom' }))).toBe(BankConnectionState.AUTHENTICATION);
    expect(bankConnectionState(withStatus({ authExpired: true, lastError: 'boom' }))).toBe(BankConnectionState.EXPIRED);
    expect(bankConnectionState(withStatus({ lastError: 'boom' }))).toBe(BankConnectionState.FAILED);
    expect(bankConnectionState(withStatus({}))).toBe(BankConnectionState.OK);
  });

  it('should show nothing for a connection that is fine, and a short status for one that is not', () => {
    expect(bankConnectionStatus(bankConnectionState(withStatus({})))).toBeUndefined();
    expect(bankConnectionStatus(bankConnectionState(withStatus({ lastError: 'boom' })))?.short).toBe('bank_balances.status.short.failed');
    expect(bankConnectionStatus(bankConnectionState(withStatus({ authExpired: true })))?.textClass).toBe('text-rui-warning');
  });
});
