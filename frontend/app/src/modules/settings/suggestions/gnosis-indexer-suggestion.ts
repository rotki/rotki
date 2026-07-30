import type {
  GeneralSettingsSuggestion,
  SuggestionProvider,
  SuggestionTranslate,
} from './settings-suggestions';
import type { ExternalServiceName } from '@/modules/integrations/types';
import type { GeneralSettings } from '@/modules/settings/types/user-settings';
import { Blockchain, toCapitalCase } from '@rotki/common';
import { isEqual } from 'es-toolkit';
import { EvmIndexer } from '@/modules/settings/types/evm-indexer';

type IndexersOrder = GeneralSettings['evmIndexersOrder'];

/**
 * The gnosis order 1.44 made the default: etherscan stopped serving gnosis on the free tier, so
 * blockscout leads and etherscan trails as the fallback for whoever holds a paid plan.
 */
export const BLOCKSCOUT_FIRST_GNOSIS_ORDER: readonly EvmIndexer[] = [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN];

export const ETHERSCAN_FIRST_GNOSIS_ORDER: readonly EvmIndexer[] = [EvmIndexer.ETHERSCAN, EvmIndexer.BLOCKSCOUT];

const BLOCKSCOUT_SERVICE: ExternalServiceName = 'blockscout';

/**
 * Recorded in `answeredSuggestions` once answered. Stable forever: changing it re-asks everyone who
 * already decided.
 */
export const GNOSIS_INDEXER_DECISION = 'gnosis-indexer-order-1.44';

export interface GnosisIndexerContext {
  /** The whole evmIndexersOrder setting, keyed by evm chain name. */
  indexersOrder: IndexersOrder;
  hasBlockscoutKey: boolean;
  hasEtherscanKey: boolean;
}

/**
 * True when the user kept a gnosis order of their own that is not what 1.44 made the default.
 * A chain with no entry follows the defaults and so already picked the new order up; one that
 * matches the default has nothing left to decide. Everything else is an explicit choice made
 * before etherscan tiered gnosis away, which is exactly what is worth asking about.
 */
export function hasCustomGnosisOrder(indexersOrder: IndexersOrder): boolean {
  const order = indexersOrder[Blockchain.GNOSIS];
  return order !== undefined && !isEqual(order, BLOCKSCOUT_FIRST_GNOSIS_ORDER);
}

/**
 * The gnosis indexer decision offered at upgrade time. Whether this user should be asked at all is
 * the provider's call below; this only turns an answered "yes" into the row itself.
 */
export function createGnosisIndexerSuggestion(
  t: SuggestionTranslate,
  { hasBlockscoutKey, hasEtherscanKey, indexersOrder }: GnosisIndexerContext,
): GeneralSettingsSuggestion | undefined {
  if (!hasCustomGnosisOrder(indexersOrder))
    return undefined;

  // Blockscout is the only one of the two with a free tier, so it leads unless the user holds an
  // etherscan key and no blockscout one — then the key they already have is the one that can
  // still serve gnosis, assuming it is on a paid plan.
  const blockscoutFirst = hasBlockscoutKey || !hasEtherscanKey;
  const recommendedChoice = blockscoutFirst ? EvmIndexer.BLOCKSCOUT : EvmIndexer.ETHERSCAN;
  // A fresh copy every time: these orders are module constants that end up inside the settings
  // update payload, and a shared instance would let anything downstream mutate them for good.
  const withGnosisOrder = (order: readonly EvmIndexer[]): IndexersOrder => ({
    ...indexersOrder,
    [Blockchain.GNOSIS]: [...order],
  });

  return {
    settingType: 'general',
    key: 'evmIndexersOrder',
    suggestedValue: withGnosisOrder(blockscoutFirst ? BLOCKSCOUT_FIRST_GNOSIS_ORDER : ETHERSCAN_FIRST_GNOSIS_ORDER),
    description: t('settings_suggestions.gnosis_indexer_v1_44.description'),
    note: t('settings_suggestions.gnosis_indexer_v1_44.note'),
    requirements: [
      { label: t('settings_suggestions.gnosis_indexer_v1_44.blockscout_key'), met: hasBlockscoutKey },
      { label: t('settings_suggestions.gnosis_indexer_v1_44.etherscan_key'), met: hasEtherscanKey },
    ],
    choices: [
      {
        id: EvmIndexer.BLOCKSCOUT,
        label: t('settings_suggestions.gnosis_indexer_v1_44.blockscout_first'),
        value: withGnosisOrder(BLOCKSCOUT_FIRST_GNOSIS_ORDER),
      },
      {
        id: EvmIndexer.ETHERSCAN,
        label: t('settings_suggestions.gnosis_indexer_v1_44.etherscan_first'),
        value: withGnosisOrder(ETHERSCAN_FIRST_GNOSIS_ORDER),
      },
    ],
    recommendedChoice,
    // A free etherscan key is indistinguishable from a paid one, so an etherscan key alone is no
    // proof that gnosis can be queried at all — and with neither key it certainly cannot. Both
    // cases get the same way out: blockscout, the only one of the two that can be had for free.
    ...(hasBlockscoutKey
      ? {}
      : {
          action: {
            label: t('settings_suggestions.gnosis_indexer_v1_44.add_key', { service: toCapitalCase(BLOCKSCOUT_SERVICE) }),
            service: BLOCKSCOUT_SERVICE,
          },
        }),
  };
}

/**
 * Only users who kept a gnosis order of their own and actually have gnosis activity are asked:
 * nobody else can be broken by the etherscan change.
 *
 * The order check is free and the activity check is a request, so the free one gates it. Both sit
 * behind the decision gate, so once this has been asked and answered neither runs again.
 */
export const gnosisIndexerProvider: SuggestionProvider = {
  decisionId: GNOSIS_INDEXER_DECISION,
  version: '1.44.0',
  isRelevant: ({ general }) => hasCustomGnosisOrder(general.evmIndexersOrder),
  resolve: async ({ general }, probes, t) => {
    if (!await probes.hasEvents(Blockchain.GNOSIS))
      return undefined;

    const keys = await probes.apiKeys();
    return createGnosisIndexerSuggestion(t, {
      hasBlockscoutKey: !!keys?.blockscout?.apiKey,
      hasEtherscanKey: !!keys?.etherscan?.apiKey,
      indexersOrder: general.evmIndexersOrder,
    });
  },
};
