import type { Component, ComputedRef, MaybeRefOrGetter, Ref, WritableComputedRef } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import { startPromise } from '@shared/utils';
import { type StakingLocation, stakingPages } from '@/pages/staking/staking-pages';
import { type StakingInfo, useStakingLocations } from '@/pages/staking/use-staking-locations';

/** Where the last visited location is remembered, so a bare `/staking` reopens it. */
const LAST_LOCATION_KEY = 'rotki.staking.last_location';

interface UseStakingPageReturn {
  getRedirectLink: (location: string) => RouteLocationRaw;
  modelLocation: WritableComputedRef<StakingLocation | undefined>;
  page: ComputedRef<Component | null>;
  staking: ComputedRef<StakingInfo[]>;
}

export function useStakingPage(locationProp: MaybeRefOrGetter<StakingLocation | ''>): UseStakingPageReturn {
  const router = useRouter();
  const route = useRoute();

  const lastLocation: Ref<string> = useLocalStorage(LAST_LOCATION_KEY, '');

  const { getRedirectLink, staking } = useStakingLocations();

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

    // The breadcrumb's way back to the grid asks for the grid, not the last location.
    const remembered = get(lastLocation);
    if (!remembered || route.query.overview)
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
