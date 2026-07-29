import type { GeneralSettingsSuggestion, SuggestionTranslate } from './settings-suggestions';
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
export const BLOCKSCOUT_FIRST_GNOSIS_ORDER: EvmIndexer[] = [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN];

export const ETHERSCAN_FIRST_GNOSIS_ORDER: EvmIndexer[] = [EvmIndexer.ETHERSCAN, EvmIndexer.BLOCKSCOUT];

const BLOCKSCOUT_SERVICE: ExternalServiceName = 'blockscout';

export interface GnosisIndexerContext {
  /** The whole evmIndexersOrder setting, keyed by evm chain name. */
  indexersOrder: IndexersOrder;
  hasGnosisEvents: boolean;
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
 * The gnosis indexer decision offered at upgrade time. Only users who both have gnosis events and
 * a gnosis order of their own are asked: nobody else can be broken by the etherscan change.
 */
export function createGnosisIndexerSuggestion(
  t: SuggestionTranslate,
  { hasBlockscoutKey, hasEtherscanKey, hasGnosisEvents, indexersOrder }: GnosisIndexerContext,
): GeneralSettingsSuggestion | undefined {
  if (!hasGnosisEvents || !hasCustomGnosisOrder(indexersOrder))
    return undefined;

  // Blockscout is the only one of the two with a free tier, so it leads unless the user holds an
  // etherscan key and no blockscout one — then the key they already have is the one that can
  // still serve gnosis, assuming it is on a paid plan.
  const blockscoutFirst = hasBlockscoutKey || !hasEtherscanKey;
  const recommendedChoice = blockscoutFirst ? EvmIndexer.BLOCKSCOUT : EvmIndexer.ETHERSCAN;
  const withGnosisOrder = (order: EvmIndexer[]): IndexersOrder => ({
    ...indexersOrder,
    [Blockchain.GNOSIS]: order,
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
