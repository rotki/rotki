import type { ComputedRef } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import type { StakingLocation } from '@/pages/staking/staking-pages';
import { getPublicProtocolImagePath } from '@/modules/core/common/file/file';

export interface StakingInfo {
  id: StakingLocation;
  image: string;
  name: string;
  /** One line on what rotki tracks at the location, shown on its card. */
  description: string;
}

interface UseStakingLocationsReturn {
  staking: ComputedRef<StakingInfo[]>;
  getRedirectLink: (location: string) => RouteLocationRaw;
  /** The location grid, marked so the page does not jump to the last visited location. */
  overviewLink: RouteLocationRaw;
}

/**
 * The staking locations and the links between them, for the page and for anything that switches
 * between locations, such as the breadcrumb's picker.
 */
export function useStakingLocations(): UseStakingLocationsReturn {
  const { t } = useI18n({ useScope: 'global' });

  const staking = computed<StakingInfo[]>(() => [
    { description: t('staking_page.locations.eth2'), id: 'eth2', image: getPublicProtocolImagePath('ethereum.svg'), name: t('staking.eth2') },
    { description: t('staking_page.locations.liquity'), id: 'liquity', image: getPublicProtocolImagePath('liquity.png'), name: t('staking.liquity') },
    { description: t('staking_page.locations.kraken'), id: 'kraken', image: getPublicProtocolImagePath('kraken.svg'), name: t('staking.kraken') },
    { description: t('staking_page.locations.lido_csm'), id: 'lido-csm', image: getPublicProtocolImagePath('lido_csm.svg'), name: t('staking.lido_csm') },
    { description: t('staking_page.locations.hyperliquid'), id: 'hyperliquid', image: getPublicProtocolImagePath('hyperliquid.svg'), name: t('staking.hyperliquid') },
    { description: t('staking_page.locations.solana'), id: 'solana', image: getPublicProtocolImagePath('solana.svg'), name: t('staking.solana') },
  ]);

  function getRedirectLink(location: string): RouteLocationRaw {
    return {
      name: '/staking/[[location]]',
      params: { location },
    };
  }

  const overviewLink: RouteLocationRaw = {
    name: '/staking/[[location]]',
    params: { location: '' },
    query: { overview: 'true' },
  };

  return {
    getRedirectLink,
    overviewLink,
    staking,
  };
}
