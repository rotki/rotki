import { OnlineHistoryEventsQueryType } from '@/types/history/events';
import { type HistoryEventEntry } from '@/types/history/events';
import historyEvents from '../../../fixtures/history-events.json';

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    isTaskRunning: vi.fn().mockReturnValue(false),
    awaitTask: vi.fn().mockResolvedValue({})
  })
}));

vi.mock('@/composables/api/history/events', () => ({
  useHistoryEventsApi: vi.fn().mockReturnValue({
    addTransactionHash: vi.fn(),
    fetchEvmTransactionsTask: vi.fn().mockResolvedValue({}),
    deleteHistoryEvent: vi.fn(),
    decodeHistoryEvents: vi.fn().mockResolvedValue({}),
    reDecodeMissingTransactionEvents: vi.fn(),
    addHistoryEvent: vi.fn(),
    editHistoryEvent: vi.fn(),
    queryOnlineHistoryEvents: vi.fn().mockResolvedValue({}),
    fetchHistoryEvents: vi.fn().mockResolvedValue(historyEvents.result)
  })
}));

describe('composables::history/events/tx', async () => {
  let events: HistoryEventEntry[];

  beforeAll(async () => {
    setActivePinia(createPinia());

    const eventsCollection = await useHistoryEvents().fetchHistoryEvents({
      limit: -1,
      offset: 0,
      eventIdentifiers: [],
      groupByEventIds: false
    });

    events = eventsCollection.data;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  test('initialize composable correctly', async () => {
    const eventsApi = useHistoryEventsApi();
    const addHistorySpy = vi.spyOn(eventsApi, 'addTransactionHash');
    const addHistoryEventSpy = vi.spyOn(eventsApi, 'addHistoryEvent');
    const editHistoryEventSpy = vi.spyOn(eventsApi, 'editHistoryEvent');
    const decodeTxSpy = vi.spyOn(eventsApi, 'decodeHistoryEvents');
    const deleteHistoryEventSpy = vi.spyOn(eventsApi, 'deleteHistoryEvent');
    const queryEvSpy = vi.spyOn(eventsApi, 'queryOnlineHistoryEvents');

    const event = {
      address: '',
      counterparty: '',
      product: '',
      txHash: '',
      ...events[0]
    };

    const editEvent = { ...event, identifier: 1 };

    const {
      addTransactionHash,
      addHistoryEvent,
      editHistoryEvent,
      deleteHistoryEvent,
      fetchTransactionEvents,
      refreshTransactions
    } = useHistoryTransactions();

    // add a hash and check the spy function is called
    await addTransactionHash({
      txHash: '0x9',
      associatedAddress: '0x0...',
      evmChain: ''
    });

    expect(addHistorySpy).toHaveBeenCalledOnce();

    // add a transaction event and check the spy function is called
    await addHistoryEvent(event);
    expect(addHistoryEventSpy).toHaveBeenCalledOnce();
    expect(addHistoryEventSpy).toHaveBeenCalledWith(event);

    // edit a transaction and check the spy function is called
    await editHistoryEvent(editEvent);

    expect(editHistoryEventSpy).toHaveBeenCalledOnce();
    expect(editHistoryEventSpy).toHaveBeenCalledWith(editEvent);

    // fetch transactions and check the spy function is called
    await fetchTransactionEvents(null, true);

    expect(decodeTxSpy).toHaveBeenCalledOnce();

    // delete transaction with empty array and check the spy function is not called
    await deleteHistoryEvent([], true);

    expect(deleteHistoryEventSpy).toHaveBeenCalledOnce();
    expect(deleteHistoryEventSpy).toHaveBeenCalledWith([], true);

    // add a transaction and check the spy function is called
    await refreshTransactions([]);
    expect(queryEvSpy).toHaveBeenCalledOnce();
    expect(queryEvSpy).toHaveBeenCalledWith({
      asyncQuery: true,
      queryType: OnlineHistoryEventsQueryType.EXCHANGES
    });

    // fetch all transaction and check the spy function is called
    await fetchTransactionEvents([], true);

    expect(decodeTxSpy).toHaveBeenCalledOnce();
  });
});
