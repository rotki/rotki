import type { EvmChainInfo } from '@/modules/core/api/types/chains';
import type { ProblemItem } from '@/modules/core/notifications/problems/backend-problem-tree';
import { assert, type Blockchain, Severity } from '@rotki/common';
import { mount } from '@vue/test-utils';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { useDetectedAccountsStore } from '@/modules/accounts/use-detected-accounts-store';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { RequestCancelledError } from '@/modules/core/api/request-queue/errors';
import { useMessageHandling } from '@/modules/core/messaging';
import { SocketMessageType } from '@/modules/core/messaging/types';
import { useBackendProblemsStore } from '@/modules/core/notifications/problems/use-backend-problems-store';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import { usePremium } from '@/modules/premium/use-premium';

const { mockConsumeMessages } = vi.hoisted((): { mockConsumeMessages: ReturnType<typeof vi.fn> } => ({
  mockConsumeMessages: vi.fn(),
}));

vi.mock('@/modules/session/api/use-session-api', () => ({
  useSessionApi: vi.fn().mockReturnValue({
    consumeMessages: mockConsumeMessages,
  }),
}));

vi.mock('@shared/utils', async (importOriginal): Promise<typeof import('@shared/utils')> => {
  const actual = await importOriginal<typeof import('@shared/utils')>();
  return {
    ...actual,
    // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- the stub skips the retry delays; the generic backoff signature cannot be reproduced inline
    backoff: (async (_retries: number, call: () => Promise<unknown>) => call()) as typeof actual.backoff,
  };
});

/** A user message as `GET /messages` returns it: the websocket shape plus its count. */
const LAST_SENT = 1790773550;

function held(data: Record<string, unknown>, count = 1, type: SocketMessageType = SocketMessageType.USER_MESSAGE): Record<string, unknown> {
  return { count, data, lastSent: LAST_SENT, type };
}

function localDbMessage(value: string): Record<string, unknown> {
  return { verbosity: 'error', value, key: 'local_db', subject: null, fields: { entry: 'tag' }, group: ['error', 'local_db', null, 'tag'] };
}

const PREMIUM_ACTIVE = { expired: false, isPremiumActive: true };

/** Every backend problem item filed so far, across parents. */
function filedItems(): ProblemItem[] {
  return get(storeToRefs(useBackendProblemsStore()).problems).flatMap(({ items }) => items);
}

function setup(): ReturnType<typeof useMessageHandling> {
  let messageHandling: ReturnType<typeof useMessageHandling> | undefined;
  mount({
    template: '<div/>',
    setup() {
      messageHandling = useMessageHandling();
    },
  });
  assert(messageHandling);
  return messageHandling;
}

vi.mock('@/modules/core/notifications/use-notifications-store', async () => {
  const { shallowRef } = await import('vue');
  return {
    useNotificationsStore: vi.fn().mockReturnValue({
      data: shallowRef([]),
    }),
  };
});

vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: vi.fn().mockReturnValue({
    notify: vi.fn(),
  }),
}));

const { mockRefreshBalances } = vi.hoisted((): { mockRefreshBalances: ReturnType<typeof vi.fn> } => ({
  mockRefreshBalances: vi.fn(),
}));
vi.mock('@/modules/balances/blockchain/use-token-detection-orchestrator', async () => {
  const { computed } = await import('vue');
  return {
    useTokenDetectionOrchestrator: vi.fn().mockReturnValue({
      detectTokens: vi.fn(),
      detectAllTokens: vi.fn(),
      useIsDetecting: vi.fn().mockReturnValue(computed(() => false)),
    }),
  };
});
vi.mock('@/modules/balances/use-blockchain-balances', () => ({
  useBlockchainBalances: vi.fn().mockReturnValue({ refreshBlockchainBalances: mockRefreshBalances }),
}));

vi.mock('@/modules/accounts/use-blockchain-account-management', () => ({
  useBlockchainAccountManagement: vi.fn().mockReturnValue({
    fetchAccounts: vi.fn(),
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const { computed } = await import('vue');
  const { Blockchain } = await import('@rotki/common');
  return {
    useSupportedChains: vi.fn().mockReturnValue({
      txEvmChains: computed(() => [{
        evmChainName: 'optimism',
        id: Blockchain.OPTIMISM,
        type: 'evm',
        image: '',
        name: 'Optimism',
        nativeToken: 'ETH',
      } satisfies EvmChainInfo]),
      evmAndEvmLikeTxChainsInfo: computed(() => [{
        evmChainName: 'optimism',
        id: Blockchain.OPTIMISM,
        type: 'evm',
        name: 'Optimism',
        image: '',
        nativeToken: 'ETH',
      } satisfies EvmChainInfo]),
      getChain: () => Blockchain.OPTIMISM,
      getChainName: () => Blockchain.OPTIMISM,
      getNativeAsset: (chain: Blockchain) => chain,
      isEvm: (_chain: Blockchain) => true,
      matchChain: () => undefined,
    }),
  };
});

describe('useMessageHandling', () => {
  beforeAll(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    vi.clearAllMocks();
    set(storeToRefs(useNotificationsStore()).data, []);
    set(storeToRefs(useBackendProblemsStore()).problems, []);
  });

  it('should mark the detected accounts and run token detection, without notifying', async () => {
    let messageHandling: ReturnType<typeof useMessageHandling> | undefined;

    mount({
      template: '<div/>',
      setup() {
        messageHandling = useMessageHandling();
      },
    });

    assert(messageHandling);

    const { handleMessage } = messageHandling;
    const { notify } = useNotificationDispatcher();
    const { canRequestData } = storeToRefs(useSessionAuthStore());
    set(canRequestData, true);
    await handleMessage(
      JSON.stringify({
        type: SocketMessageType.EVM_ACCOUNTS_DETECTION,
        data: [
          {
            chain: 'optimism',
            address: '0xdead',
          },
        ],
      }),
    );

    expect(mockRefreshBalances).toHaveBeenCalledTimes(1);
    expect(mockRefreshBalances).toHaveBeenCalledWith(
      { blockchain: 'optimism' },
      'background',
      { detect: true, detectAddresses: ['0xdead'] },
    );
    expect(useDetectedAccountsStore().isDetected('optimism', '0xdead')).toBe(true);
    expect(notify).not.toHaveBeenCalled();
  });

  it('should ignore a message with an invalid format', async () => {
    const { handleMessage } = setup();
    const { notify } = useNotificationDispatcher();

    await handleMessage(JSON.stringify({ foo: 'bar' }));

    expect(notify).not.toHaveBeenCalled();
  });

  it('should route each held message once, in the order the backend returned them', async () => {
    mockConsumeMessages.mockResolvedValue({
      dropped: 0,
      messages: [
        held(localDbMessage('first')),
        held(localDbMessage('second')),
      ],
    });

    const { consume } = setup();

    await consume();

    expect(filedItems()).toMatchObject([{ repeats: 2, source: { value: 'second' } }]);
  });

  it('should tell the user how many messages the backend dropped to stay within its limits', async () => {
    mockConsumeMessages.mockResolvedValue({ dropped: 12, messages: [] });

    const { consume } = setup();
    const { notify } = useNotificationDispatcher();

    await consume();

    expect(notify).toHaveBeenCalledTimes(1);
    expect(vi.mocked(notify).mock.calls[0][0]).toMatchObject({
      message: 'actions.notifications.consume.dropped::12',
      severity: Severity.WARNING,
    });
  });

  it('should route a valid typed polling message to its handler', async () => {
    mockConsumeMessages.mockResolvedValue({
      dropped: 0,
      messages: [{
        type: SocketMessageType.EVM_ACCOUNTS_DETECTION,
        data: [{ address: '0xdead', chain: 'optimism' }],
        count: 1,
        lastSent: LAST_SENT,
      }],
    });

    const { canRequestData } = storeToRefs(useSessionAuthStore());
    set(canRequestData, true);

    const { consume } = setup();
    const { notify } = useNotificationDispatcher();

    await consume();

    expect(mockRefreshBalances).toHaveBeenCalledWith(
      { blockchain: 'optimism' },
      'background',
      { detect: true, detectAddresses: ['0xdead'] },
    );
    expect(notify).not.toHaveBeenCalled();
  });

  it('should drop a polled message that fails the schema and still show the rest', async () => {
    mockConsumeMessages.mockResolvedValue({
      dropped: 0,
      messages: [
        { unexpected: true, count: 1, lastSent: LAST_SENT },
        held(localDbMessage('valid')),
      ],
    });

    const { consume } = setup();

    await consume();

    expect(filedItems().map(({ source }) => source.value)).toEqual(['valid']);
  });

  it('should file a polled classified user message as a backend problem, without notifying', async () => {
    mockConsumeMessages.mockResolvedValue({
      dropped: 0,
      messages: [held({
        verbosity: 'error',
        value: 'Failed to deserialize a kucoin balance. Ignoring it.',
        key: 'bad_data',
        subject: 'kucoin',
        fields: { record: 'balance', error: 'Missing key: amount' },
        group: ['error', 'bad_data', 'kucoin', 'balance'],
      })],
    });

    const { consume } = setup();
    const { notify } = useNotificationDispatcher();

    await consume();

    expect(notify).not.toHaveBeenCalled();
    expect(filedItems().map(({ source }) => source.value)).toEqual(['Failed to deserialize a kucoin balance. Ignoring it.']);
  });

  it('should count a held user message as every time the backend sent it', async () => {
    mockConsumeMessages.mockResolvedValue({
      dropped: 0,
      messages: [held(localDbMessage('kucoin is down'), 4)],
    });

    const { consume } = setup();

    await consume();

    expect(filedItems()).toMatchObject([{ repeats: 4 }]);
  });

  it('should date a held user message by when the backend last sent it, not when it was read', async () => {
    mockConsumeMessages.mockResolvedValue({
      dropped: 0,
      messages: [held(localDbMessage('kucoin is down'))],
    });

    const { consume } = setup();

    await consume();

    expect(filedItems()[0].lastSeen).toEqual(new Date(LAST_SENT * 1000));
  });

  it('should date a held notification by when the backend last sent it, not when it was read', async () => {
    set(usePremium(), false);
    mockConsumeMessages.mockResolvedValue({
      dropped: 0,
      messages: [held(PREMIUM_ACTIVE, 1, SocketMessageType.PREMIUM_STATUS_UPDATE)],
    });

    const { consume } = setup();
    const { notify } = useNotificationDispatcher();

    await consume();

    expect(vi.mocked(notify).mock.calls[0][0].date).toEqual(new Date(LAST_SENT * 1000));
  });

  it('should leave a websocket message to be dated when it arrives', async () => {
    set(usePremium(), false);
    const { handleMessage } = setup();
    const { notify } = useNotificationDispatcher();

    await handleMessage(JSON.stringify({ type: SocketMessageType.PREMIUM_STATUS_UPDATE, data: PREMIUM_ACTIVE }));

    expect(vi.mocked(notify).mock.calls[0][0].date).toBeUndefined();
  });

  it('should notify when message consumption fails', async () => {
    mockConsumeMessages.mockRejectedValue(new Error('network down'));

    const { consume } = setup();
    const { notify } = useNotificationDispatcher();

    await consume();

    expect(notify).toHaveBeenCalledTimes(1);
    expect(vi.mocked(notify).mock.calls[0][0].message).toContain('network down');
  });

  it('should not notify when the session refuses the poll', async () => {
    mockConsumeMessages.mockRejectedValue(new RequestCancelledError('No live session'));

    const { consume } = setup();
    const { notify } = useNotificationDispatcher();

    await consume();

    expect(mockConsumeMessages).toHaveBeenCalledOnce();
    expect(notify).not.toHaveBeenCalled();
  });
});
