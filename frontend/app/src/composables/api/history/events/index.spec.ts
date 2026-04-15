import type { TransactionRequestPayload } from '@/modules/history/events/event-payloads';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import { BigNumber, bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { server } from '@test/setup-files/server';
import { type DefaultBodyType, http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type NewOnlineHistoryEventPayload, OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import { useHistoryEventsApi } from './index';

function createNewEventPayload(overrides?: Partial<NewOnlineHistoryEventPayload>): NewOnlineHistoryEventPayload {
  return {
    amount: bigNumberify(0),
    asset: 'ETH',
    entryType: HistoryEventEntryType.HISTORY_EVENT,
    eventSubtype: 'none',
    eventType: 'informational',
    groupIdentifier: 'test-123',
    location: 'ethereum',
    locationLabel: '0x123',
    sequenceIndex: 0,
    timestamp: 1700000000,
    ...overrides,
  };
}

function createFetchPayload(overrides?: Partial<HistoryEventRequestPayload>): HistoryEventRequestPayload {
  return {
    aggregateByGroupIds: false,
    limit: 50,
    offset: 0,
    ...overrides,
  };
}

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/history/events/index', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchTransactionsTask', () => {
    it('should fetch transactions as async task', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.post(`${backendUrl}/api/1/blockchains/transactions`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: { task_id: 123 },
            message: '',
          });
        }),
      );

      const { fetchTransactionsTask } = useHistoryEventsApi();
      const payload: TransactionRequestPayload = {
        accounts: [{ address: '0x123', blockchain: 'eth' }],
      };
      const result = await fetchTransactionsTask(payload);

      expect(capturedBody).toEqual({
        accounts: [{ address: '0x123', blockchain: 'eth' }],
        async_query: true,
      });
      expect(result.taskId).toBe(123);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/blockchains/transactions`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch transactions',
          })),
      );

      const { fetchTransactionsTask } = useHistoryEventsApi();

      await expect(fetchTransactionsTask({ accounts: [] }))
        .rejects
        .toThrow('Failed to fetch transactions');
    });
  });

  describe('deleteTransactions', () => {
    it('should delete transactions for a chain', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/transactions`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteTransactions } = useHistoryEventsApi();
      const result = await deleteTransactions('eth');

      expect(capturedBody).toEqual({ chain: 'eth' });
      expect(result).toBe(true);
    });

    it('should delete specific transaction by tx_ref', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/transactions`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteTransactions } = useHistoryEventsApi();
      const result = await deleteTransactions('eth', '0xabc123');

      expect(capturedBody).toEqual({ chain: 'eth', tx_ref: '0xabc123' });
      expect(result).toBe(true);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/transactions`, () =>
          HttpResponse.json({
            result: null,
            message: 'Transaction not found',
          })),
      );

      const { deleteTransactions } = useHistoryEventsApi();

      await expect(deleteTransactions('eth', '0xabc'))
        .rejects
        .toThrow('Transaction not found');
    });
  });

  describe('decodeTransactions', () => {
    it('should decode transactions for a chain', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.post(`${backendUrl}/api/1/blockchains/transactions/decode`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: { task_id: 456 },
            message: '',
          });
        }),
      );

      const { decodeTransactions } = useHistoryEventsApi();
      const result = await decodeTransactions('eth');

      expect(capturedBody).toEqual({
        async_query: true,
        chain: 'eth',
      });
      expect(result.taskId).toBe(456);
    });

    it('should support ignore_cache flag', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.post(`${backendUrl}/api/1/blockchains/transactions/decode`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: { task_id: 789 },
            message: '',
          });
        }),
      );

      const { decodeTransactions } = useHistoryEventsApi();
      await decodeTransactions('eth', true);

      expect(capturedBody).toEqual({
        async_query: true,
        chain: 'eth',
        ignore_cache: true,
      });
    });
  });

  describe('addHistoryEvent', () => {
    it('should add a history event', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.put(`${backendUrl}/api/1/history/events`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: { identifier: 12345 },
            message: '',
          });
        }),
      );

      const { addHistoryEvent } = useHistoryEventsApi();
      const result = await addHistoryEvent(createNewEventPayload({
        sequenceIndex: 0,
        timestamp: 1700000000,
        locationLabel: '0x123',
      }));

      expect(capturedBody).toMatchObject({
        sequence_index: 0,
        timestamp: 1700000000,
        location_label: '0x123',
      });
      expect(result.identifier).toBe(12345);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/history/events`, () =>
          HttpResponse.json({
            result: null,
            message: 'Invalid event data',
          })),
      );

      const { addHistoryEvent } = useHistoryEventsApi();

      await expect(addHistoryEvent(createNewEventPayload()))
        .rejects
        .toThrow('Invalid event data');
    });
  });

  describe('editHistoryEvent', () => {
    it('should edit a history event', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.patch(`${backendUrl}/api/1/history/events`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { editHistoryEvent } = useHistoryEventsApi();
      const result = await editHistoryEvent({
        ...createNewEventPayload({ userNotes: 'Updated notes' }),
        identifier: 12345,
      });

      expect(capturedBody).toMatchObject({
        identifier: 12345,
        user_notes: 'Updated notes',
      });
      expect(result).toBe(true);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.patch(`${backendUrl}/api/1/history/events`, () =>
          HttpResponse.json({
            result: null,
            message: 'Event not found',
          })),
      );

      const { editHistoryEvent } = useHistoryEventsApi();

      await expect(editHistoryEvent({ ...createNewEventPayload(), identifier: 999 }))
        .rejects
        .toThrow('Event not found');
    });
  });

  describe('deleteHistoryEvent', () => {
    it('should delete history events', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.delete(`${backendUrl}/api/1/history/events`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteHistoryEvent } = useHistoryEventsApi();
      const result = await deleteHistoryEvent({ identifiers: ['1', '2', '3'] });

      expect(capturedBody).toEqual({
        force_delete: false,
        identifiers: ['1', '2', '3'],
      });
      expect(result).toBe(true);
    });

    it('should support force delete', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.delete(`${backendUrl}/api/1/history/events`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteHistoryEvent } = useHistoryEventsApi();
      await deleteHistoryEvent({ identifiers: ['1'] }, true);

      expect(capturedBody).toEqual({
        force_delete: true,
        identifiers: ['1'],
      });
    });

    it('should throw error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/history/events`, () =>
          HttpResponse.json({
            result: null,
            message: 'Events not found',
          })),
      );

      const { deleteHistoryEvent } = useHistoryEventsApi();

      await expect(deleteHistoryEvent({ identifiers: ['999'] }))
        .rejects
        .toThrow('Events not found');
    });
  });

  describe('getEventDetails', () => {
    it('should get event details', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/history/events/details`, ({ request }) => {
          const url = new URL(request.url);
          expect(url.searchParams.get('identifier')).toBe('12345');
          return HttpResponse.json({
            result: {
              liquity_staking: {
                staked_amount: '100',
                asset: 'ETH',
              },
            },
            message: '',
          });
        }),
      );

      const { getEventDetails } = useHistoryEventsApi();
      const result = await getEventDetails(12345);

      expect(result?.liquityStaking?.stakedAmount).toBeInstanceOf(BigNumber);
      expect(result?.liquityStaking?.stakedAmount.toString()).toBe('100');
    });
  });

  describe('addTransactionHash', () => {
    it('should add transaction hash', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.put(`${backendUrl}/api/1/blockchains/transactions`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { addTransactionHash } = useHistoryEventsApi();
      const result = await addTransactionHash({
        blockchain: 'eth',
        txRef: '0xabc123',
        associatedAddress: '0x456',
      });

      expect(capturedBody).toEqual({
        blockchain: 'eth',
        tx_ref: '0xabc123',
        associated_address: '0x456',
      });
      expect(result).toBe(true);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/blockchains/transactions`, () =>
          HttpResponse.json({
            result: null,
            message: 'Invalid transaction hash',
          })),
      );

      const { addTransactionHash } = useHistoryEventsApi();

      await expect(addTransactionHash({ blockchain: 'eth', txRef: 'invalid', associatedAddress: '0x123' }))
        .rejects
        .toThrow('Invalid transaction hash');
    });
  });

  describe('getTransactionTypeMappings', () => {
    it('should get transaction type mappings', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/history/events/type_mappings`, () =>
          HttpResponse.json({
            result: {
              global_mappings: {},
              entry_type_mappings: {},
              event_category_details: {},
              accounting_events_icons: {},
            },
            message: '',
          })),
      );

      const { getTransactionTypeMappings } = useHistoryEventsApi();
      const result = await getTransactionTypeMappings();

      expect(result).toHaveProperty('globalMappings');
      expect(result).toHaveProperty('entryTypeMappings');
    });

    it('should throw error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/history/events/type_mappings`, () =>
          HttpResponse.json({
            result: null,
            message: 'Service unavailable',
          })),
      );

      const { getTransactionTypeMappings } = useHistoryEventsApi();

      await expect(getTransactionTypeMappings())
        .rejects
        .toThrow('Service unavailable');
    });
  });

  describe('getHistoryEventCounterpartiesData', () => {
    it('should get counterparties data', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/history/events/counterparties`, () =>
          HttpResponse.json({
            result: [
              { identifier: 'uniswap', label: 'Uniswap', image: 'uniswap.png' },
              { identifier: 'aave', label: 'Aave', image: 'aave.png' },
            ],
            message: '',
          })),
      );

      const { getHistoryEventCounterpartiesData } = useHistoryEventsApi();
      const result = await getHistoryEventCounterpartiesData();

      expect(result).toHaveLength(2);
      expect(result[0].identifier).toBe('uniswap');
    });

    it('should throw error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/history/events/counterparties`, () =>
          HttpResponse.json({
            result: null,
            message: 'Service unavailable',
          })),
      );

      const { getHistoryEventCounterpartiesData } = useHistoryEventsApi();

      await expect(getHistoryEventCounterpartiesData())
        .rejects
        .toThrow('Service unavailable');
    });
  });

  describe('fetchHistoryEvents', () => {
    it('should fetch history events', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.post(`${backendUrl}/api/1/history/events`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: {
              entries: [],
              entries_found: 0,
              entries_limit: 50,
              entries_total: 0,
            },
            message: '',
          });
        }),
      );

      const { fetchHistoryEvents } = useHistoryEventsApi();
      const result = await fetchHistoryEvents(createFetchPayload());

      expect(capturedBody).toMatchObject({
        limit: 50,
        offset: 0,
      });
      expect(result.entriesFound).toBe(0);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/history/events`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch events',
          })),
      );

      const { fetchHistoryEvents } = useHistoryEventsApi();

      await expect(fetchHistoryEvents(createFetchPayload()))
        .rejects
        .toThrow('Failed to fetch events');
    });
  });

  describe('queryOnlineHistoryEvents', () => {
    it('should query online history events', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.post(`${backendUrl}/api/1/history/events/query`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: { task_id: 999 },
            message: '',
          });
        }),
      );

      const { queryOnlineHistoryEvents } = useHistoryEventsApi();
      const result = await queryOnlineHistoryEvents({
        asyncQuery: true,
        queryType: OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
      });

      expect(capturedBody).toMatchObject({
        async_query: true,
        query_type: 'eth_withdrawals',
      });
      expect(result.taskId).toBe(999);
    });
  });

  describe('queryExchangeEvents', () => {
    it('should query exchange events', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.post(`${backendUrl}/api/1/history/events/query/exchange`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: { task_id: 888 },
            message: '',
          });
        }),
      );

      const { queryExchangeEvents } = useHistoryEventsApi();
      const result = await queryExchangeEvents({
        location: 'binance',
        name: 'my-account',
      });

      expect(capturedBody).toMatchObject({
        location: 'binance',
        name: 'my-account',
        async_query: true,
      });
      expect(result.taskId).toBe(888);
    });
  });

  describe('deleteStakeEvents', () => {
    it('should delete stake events', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/eth2/stake/events`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteStakeEvents } = useHistoryEventsApi();
      const result = await deleteStakeEvents('withdrawal');

      expect(capturedBody).toEqual({ entry_type: 'withdrawal' });
      expect(result).toBe(true);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/eth2/stake/events`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to delete events',
          })),
      );

      const { deleteStakeEvents } = useHistoryEventsApi();

      await expect(deleteStakeEvents('withdrawal'))
        .rejects
        .toThrow('Failed to delete events');
    });
  });

  describe('getTransactionStatusSummary', () => {
    it('should get transaction status summary', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/history/status/summary`, () =>
          HttpResponse.json({
            result: {
              evm_last_queried_ts: 1700000000,
              exchanges_last_queried_ts: 1700100000,
              has_evm_accounts: true,
              has_exchanges_accounts: true,
              undecoded_tx_count: 10,
            },
            message: '',
          })),
      );

      const { getTransactionStatusSummary } = useHistoryEventsApi();
      const result = await getTransactionStatusSummary();

      expect(result.evmLastQueriedTs).toBe(1700000000);
      expect(result.exchangesLastQueriedTs).toBe(1700100000);
      expect(result.hasEvmAccounts).toBe(true);
      expect(result.hasExchangesAccounts).toBe(true);
      expect(result.undecodedTxCount).toBe(10);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/history/status/summary`, () =>
          HttpResponse.json({
            result: null,
            message: 'Service unavailable',
          })),
      );

      const { getTransactionStatusSummary } = useHistoryEventsApi();

      await expect(getTransactionStatusSummary())
        .rejects
        .toThrow('Service unavailable');
    });
  });
});
