import type { Component, ComputedRef, MaybeRefOrGetter, Ref, WritableComputedRef } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import { startPromise } from '@shared/utils';
import { getPublicProtocolImagePath } from '@/modules/core/common/file/file';
import { type StakingLocation, stakingPages } from '@/pages/staking/staking-pages';

export interface StakingInfo {
  id: StakingLocation;
  image: string;
  name: string;
}

/** Where the last visited location is remembered, so a bare `/staking` reopens it. */
const LAST_LOCATION_KEY = 'rotki.staking.last_location';

interface UseStakingPageReturn {
  getRedirectLink: (location: string) => RouteLocationRaw;
  modelLocation: WritableComputedRef<StakingLocation | undefined>;
  page: ComputedRef<Component | null>;
  staking: ComputedRef<StakingInfo[]>;
}

export function useStakingPage(locationProp: MaybeRefOrGetter<StakingLocation | ''>): UseStakingPageReturn {
  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();

  const lastLocation: Ref<string> = useLocalStorage(LAST_LOCATION_KEY, '');

  function getRedirectLink(location: string): RouteLocationRaw {
    return {
      name: '/staking/[[location]]',
      params: { location },
    };
  }

  async function redirect(location: string): Promise<void> {
    await nextTick(() => {
      startPromise(router.push(getRedirectLink(location)));
    });
  }

  const modelLocation = computed<StakingLocation | undefined>({
    get() {
      return toValue(locationProp) || undefined;
    },
    set(value?: StakingLocation) {
      set(lastLocation, value);
      if (value)
        startPromise(redirect(value));
    },
  });

  const staking = computed<StakingInfo[]>(() => [
    { id: 'eth2', image: getPublicProtocolImagePath('ethereum.svg'), name: t('staking.eth2') },
    { id: 'liquity', image: getPublicProtocolImagePath('liquity.png'), name: t('staking.liquity') },
    { id: 'kraken', image: getPublicProtocolImagePath('kraken.svg'), name: t('staking.kraken') },
    { id: 'lido-csm', image: getPublicProtocolImagePath('lido_csm.svg'), name: t('staking.lido_csm') },
  ]);

  const page = computed<Component | null>(() => {
    const selected = get(modelLocation);
    return selected ? stakingPages[selected] : null;
  });

  onMounted(async () => {
    const current = toValue(locationProp);
    if (current) {
      // Writing it back is what records it as the remembered location.
      set(modelLocation, current);
      return;
    }

    const remembered = get(lastLocation);
    if (!remembered)
      return;

    await redirect(remembered);
  });

  return {
    getRedirectLink,
    modelLocation,
    page,
    staking,
  };
}
