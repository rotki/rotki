import type { EffectScope } from 'vue';
import { externalLinks } from '@shared/external-links';
import { createTestExchange } from '@test/utils/create-data';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { type ActionItem, type ActionItemOption, type ActionTarget, ActionUrgency, createActionItem } from '@/modules/core/action-center/types';
import { getServiceRegisterUrl } from '@/modules/core/common/helpers/url';
import { INDEXER_SETTINGS, ORACLE_SETTINGS } from '@/modules/shell/action-center/row-options';
import { useIntegrationRows } from '@/modules/shell/action-center/use-integration-rows';
import { NoIndexersCause, RaisedConditionKind, SessionCause, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

const savedKeys = ref<Record<string, string>>({});
const moneriumAuthenticated = ref<boolean>(false);
const suppressedServices = ref<string[]>([]);
const update = vi.fn<(payload: object) => Promise<{ success: boolean }>>();
const show = vi.fn<(message: { title: string; message: string }, onConfirm: () => Promise<void>) => void>();

vi.mock('@/modules/settings/api-keys/external/use-external-api-keys', () => ({
  useExternalApiKeys: (): object => ({
    getApiKey: (name: string): string => get(savedKeys)[name] ?? '',
  }),
}));

vi.mock('@/modules/integrations/monerium/use-monerium-auth', () => ({
  useMoneriumOAuth: (): object => ({ authenticated: moneriumAuthenticated }),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): Ref<string[]> => suppressedServices,
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): object => ({ update }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): object => ({ show }),
}));

const bankRows = ref<ActionItem[]>([]);

vi.mock('@/modules/shell/action-center/use-bank-rows', () => ({
  useBankRows: (): Ref<ActionItem[]> => bankRows,
}));

let scope: EffectScope | undefined;

function rows(): ComputedRef<ActionItem[]> {
  scope = effectScope();
  const result = scope.run(() => useIntegrationRows());
  assert(result);
  return result;
}

function raiseMissingKey(service: string, location?: string): void {
  useRaisedConditionsStore().raise({ kind: RaisedConditionKind.MISSING_API_KEY, location, service });
}

function onlyRow(): ActionItem {
  const [row, ...rest] = get(rows());
  assert(row);
  expect(rest).toHaveLength(0);
  return row;
}

function option(row: ActionItem, id: string): ActionItemOption {
  const found = row.options.find(candidate => candidate.id === id);
  assert(found);
  return found;
}

describe('modules/shell/action-center/use-integration-rows', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    update.mockResolvedValue({ success: true });
    set(savedKeys, {});
    set(moneriumAuthenticated, false);
    set(suppressedServices, []);
    set(bankRows, []);
  });

  afterEach(() => {
    scope?.stop();
  });

  it('should list the bank rows ahead of the raised conditions', () => {
    const bank = createActionItem<ActionTarget, string>({
      actionLabel: 'authenticate',
      count: 1,
      description: 'tan',
      icon: 'lu-shield-alert',
      id: 'bank-authentication-fints-main',
      target: { kind: 'route', to: { name: '/api-keys/banks/' } },
      title: 'tan',
      urgency: ActionUrgency.BLOCKING,
    });
    set(bankRows, [bank]);
    raiseMissingKey('etherscan');

    expect(get(rows()).map(row => row.id)).toEqual(['bank-authentication-fints-main', 'missing-api-key-etherscan']);
  });

  describe('missing api key rows', () => {
    it('should raise one row per service a query needed a key for', () => {
      raiseMissingKey('etherscan');
      raiseMissingKey('blockscout');

      expect(get(rows()).map(row => row.id)).toEqual(['missing-api-key-etherscan', 'missing-api-key-blockscout']);
    });

    it('should take a row down as soon as a key is saved for its service', () => {
      raiseMissingKey('etherscan');
      const result = rows();

      set(savedKeys, { etherscan: 'a-key' });

      expect(get(result)).toEqual([]);
    });

    it('should keep a refused key\'s row while that key is saved, and say the key was refused', () => {
      set(savedKeys, { blockscout: 'refused-key' });
      useRaisedConditionsStore().raise({ keyRejected: true, kind: RaisedConditionKind.MISSING_API_KEY, location: 'base', service: 'blockscout' });

      const row = onlyRow();

      expect(row.title).toBe('action_center.rows.integrations.missing_api_key.title_rejected::Base, Blockscout');
      expect(row.description).toBe('action_center.rows.integrations.missing_api_key.description_blockscout_rejected::Base, Blockscout');
    });

    it('should take a row down once its service is suppressed, even one raised before', () => {
      raiseMissingKey('helius');
      const result = rows();

      set(suppressedServices, ['helius']);

      expect(get(result)).toEqual([]);
    });

    it('should open the service settings on the service the row is about', () => {
      raiseMissingKey('helius');

      expect(onlyRow().target).toEqual({ kind: 'route', to: getServiceRegisterUrl('helius')?.route });
    });

    it('should name the location when the report carried one', () => {
      raiseMissingKey('thegraph', 'arbitrum_one');
      const row = onlyRow();

      expect(row.title).toBe('action_center.rows.integrations.missing_api_key.title_location::Arbitrum One, Thegraph');
      expect(row.description).toBe('action_center.rows.integrations.missing_api_key.description_thegraph::Arbitrum One, Thegraph');
    });

    it('should say what the missing key costs for each service, and fall back to the generic wording', () => {
      raiseMissingKey('blockscout');
      raiseMissingKey('etherscan');
      raiseMissingKey('helius');
      raiseMissingKey('alchemy');

      expect(get(rows()).map(row => row.description)).toEqual([
        'action_center.rows.integrations.missing_api_key.description_blockscout::Blockscout',
        'action_center.rows.integrations.missing_api_key.description_etherscan::Etherscan',
        'action_center.rows.integrations.missing_api_key.description_helius::Helius',
        'action_center.rows.integrations.missing_api_key.description::Alchemy',
      ]);
    });

    it('should treat a key that only adds data as a to-do rather than a warning', () => {
      raiseMissingKey('beaconchain');
      raiseMissingKey('blockscout');

      const [beaconchain, blockscout] = get(rows());

      expect(beaconchain.urgency).toBe(ActionUrgency.TODO);
      expect(beaconchain.description).toBe('action_center.rows.integrations.missing_api_key.description_beaconchain::Beaconchain');
      expect(blockscout.urgency).toBe(ActionUrgency.DECISION);
    });
  });

  describe('missing api key options', () => {
    it('should offer the indexer order and a key link to an indexer that needs a user supplied key', () => {
      raiseMissingKey('blockscout');
      const row = onlyRow();

      expect(row.options.map(({ id }) => id)).toEqual(['change-indexer-order', 'get-key', 'do-not-show-again']);
      expect(option(row, 'change-indexer-order').target).toEqual(INDEXER_SETTINGS);
      expect(option(row, 'get-key').target).toEqual({ kind: 'external', url: getServiceRegisterUrl('blockscout')?.external });
    });

    it('should not offer Etherscan a key link, since it keeps working on its packaged key', () => {
      raiseMissingKey('etherscan');

      expect(onlyRow().options.map(({ id }) => id)).toEqual(['change-indexer-order', 'do-not-show-again']);
    });

    it('should point The Graph at its guide as well as a key link', () => {
      raiseMissingKey('thegraph', 'arbitrum_one');
      const row = onlyRow();

      expect(row.options.map(({ id }) => id)).toEqual(['get-key', 'guide', 'do-not-show-again']);
      expect(option(row, 'guide').target).toEqual({ kind: 'external', url: externalLinks.usageGuideSection.theGraphApiKey });
    });

    it('should offer only what applies to a service that cannot be suppressed', () => {
      raiseMissingKey('alchemy');

      expect(onlyRow().options).toEqual([]);
    });

    it('should ask before suppressing a service, then add it to the suppressed services', async () => {
      set(suppressedServices, ['beaconchain']);
      raiseMissingKey('helius');

      const suppress = option(onlyRow(), 'do-not-show-again');
      expect(suppress.danger).toBe(true);
      assert(suppress.target.kind === 'run');
      suppress.target.run();

      expect(update).not.toHaveBeenCalled();
      const [message, onConfirm] = show.mock.calls[0];
      expect(message.message).toBe('action_center.rows.integrations.missing_api_key.suppress_confirm.message::Helius');

      await onConfirm();

      expect(update).toHaveBeenCalledWith({ suppressMissingKeyMsgServices: ['beaconchain', 'helius'] });
    });
  });

  describe('refused exchange key rows', () => {
    const main = { location: 'binance', name: 'main' };

    function raiseRefusedKey(account: { location: string; name: string }): void {
      useRaisedConditionsStore().raise({ kind: RaisedConditionKind.EXCHANGE_KEY_REJECTED, ...account });
    }

    it('should raise one row per refused account, opening the keys of that account', () => {
      useConnectedExchangesStore().setConnectedExchanges([createTestExchange('binance', 'main')]);
      raiseRefusedKey(main);

      const row = onlyRow();

      expect(row).toMatchObject({
        id: 'exchange-key-rejected-binance-main',
        target: { kind: 'route', to: { name: '/api-keys/exchanges/', query: main } },
        title: 'action_center.rows.integrations.exchange_key_rejected.title::Binance, main',
        urgency: ActionUrgency.DECISION,
      });
    });

    it('should take a row down once its account is no longer connected', async () => {
      const connected = useConnectedExchangesStore();
      connected.setConnectedExchanges([createTestExchange('binance', 'main'), createTestExchange('binance', 'other')]);
      raiseRefusedKey(main);
      const result = rows();

      connected.setConnectedExchanges([createTestExchange('binance', 'other')]);
      await nextTick();

      expect(get(result)).toEqual([]);
    });
  });

  describe('set-aside oracle rows', () => {
    it('should ask nothing of the user and open the oracle order', () => {
      useRaisedConditionsStore().raise({ kind: RaisedConditionKind.ORACLE_PENALIZED, oracle: 'coingecko', reason: 'timeout', until: 0 });

      expect(onlyRow()).toMatchObject({
        description: 'action_center.rows.integrations.oracle_penalized.description_timeout::Coingecko',
        id: 'oracle-penalized-coingecko',
        target: ORACLE_SETTINGS,
        urgency: ActionUrgency.AUTOMATIC,
      });
    });

    it('should explain repeated failures differently from a silent oracle', () => {
      useRaisedConditionsStore().raise({ kind: RaisedConditionKind.ORACLE_PENALIZED, oracle: 'defillama', reason: 'errors', until: 0 });

      expect(onlyRow().description).toBe('action_center.rows.integrations.oracle_penalized.description_errors::Defillama');
    });
  });

  describe('session rows', () => {
    it('should keep a Monerium row only while the session reads unauthenticated', () => {
      useRaisedConditionsStore().raise({ cause: SessionCause.EXPIRED, kind: RaisedConditionKind.MONERIUM_SESSION });
      const result = rows();

      expect(get(result).map(row => row.id)).toEqual(['monerium-session']);
      expect(get(result)[0].target).toEqual({ kind: 'route', to: { name: '/api-keys/external/', query: { service: 'monerium' } } });

      set(moneriumAuthenticated, true);

      expect(get(result)).toEqual([]);
    });

    it('should keep a Gnosis Pay row until its condition is cleared', () => {
      const store = useRaisedConditionsStore();
      store.raise({ cause: SessionCause.EXPIRED, kind: RaisedConditionKind.GNOSIS_PAY_SESSION });
      const result = rows();

      expect(get(result).map(row => row.id)).toEqual(['gnosis-pay-session']);
      expect(get(result)[0].title).toBe('action_center.rows.integrations.gnosis_pay_session.title');
      expect(get(result)[0].actionLabel).toBe('external_services.actions.reauthenticate');

      store.clear(({ kind }) => kind === RaisedConditionKind.GNOSIS_PAY_SESSION);

      expect(get(result)).toEqual([]);
    });

    it('should ask a user who never connected Gnosis Pay to connect, not to sign in again', () => {
      useRaisedConditionsStore().raise({ cause: SessionCause.NOT_CONNECTED, kind: RaisedConditionKind.GNOSIS_PAY_SESSION });

      expect(onlyRow().title).toBe('action_center.rows.integrations.gnosis_pay_session.title_not_connected');
      expect(onlyRow().description).toBe('action_center.rows.integrations.gnosis_pay_session.description_not_connected');
      expect(onlyRow().actionLabel).toBe('external_services.actions.authenticate');
    });

    it('should ask a user who never connected Monerium to connect, not to sign in again', () => {
      useRaisedConditionsStore().raise({ cause: SessionCause.NOT_CONNECTED, kind: RaisedConditionKind.MONERIUM_SESSION });

      expect(onlyRow().title).toBe('action_center.rows.integrations.monerium_session.title_not_connected');
      expect(onlyRow().description).toBe('action_center.rows.integrations.monerium_session.description_not_connected');
      expect(onlyRow().actionLabel).toBe('external_services.actions.authenticate');
    });
  });

  it('should leave conditions of other modules to their own rows', () => {
    useRaisedConditionsStore().raise({ cause: NoIndexersCause.UNAVAILABLE, chain: 'base', kind: RaisedConditionKind.NO_AVAILABLE_INDEXERS });

    expect(get(rows())).toEqual([]);
  });
});
