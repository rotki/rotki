import type { EffectScope } from 'vue';
import { externalLinks } from '@shared/external-links';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type ActionItem, type ActionItemOption, ActionUrgency } from '@/modules/core/action-center/types';
import { getServiceRegisterUrl } from '@/modules/core/common/helpers/url';
import { INDEXER_SETTINGS } from '@/modules/shell/action-center/row-options';
import { useIntegrationRows } from '@/modules/shell/action-center/use-integration-rows';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

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
  });

  afterEach(() => {
    scope?.stop();
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

  describe('session rows', () => {
    it('should keep a Monerium row only while the session reads unauthenticated', () => {
      useRaisedConditionsStore().raise({ kind: RaisedConditionKind.MONERIUM_SESSION });
      const result = rows();

      expect(get(result).map(row => row.id)).toEqual(['monerium-session']);
      expect(get(result)[0].target).toEqual({ kind: 'route', to: { name: '/api-keys/external/', query: { service: 'monerium' } } });

      set(moneriumAuthenticated, true);

      expect(get(result)).toEqual([]);
    });

    it('should keep a Gnosis Pay row until its condition is cleared', () => {
      const store = useRaisedConditionsStore();
      store.raise({ kind: RaisedConditionKind.GNOSIS_PAY_SESSION });
      const result = rows();

      expect(get(result).map(row => row.id)).toEqual(['gnosis-pay-session']);
      expect(get(result)[0].title).toBe('action_center.rows.integrations.gnosis_pay_session.title');

      store.clear(({ kind }) => kind === RaisedConditionKind.GNOSIS_PAY_SESSION);

      expect(get(result)).toEqual([]);
    });
  });

  it('should leave conditions of other modules to their own rows', () => {
    useRaisedConditionsStore().raise({ chain: 'base', kind: RaisedConditionKind.NO_AVAILABLE_INDEXERS, paidKeyRequired: false });

    expect(get(rows())).toEqual([]);
  });
});
