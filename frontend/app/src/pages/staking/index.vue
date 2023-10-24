<script setup lang="ts">
import { Routes } from '@/router/routes';

interface StakingInfo {
  id: string;
  icon: string;
  name: string;
  img?: boolean;
}

const props = withDefaults(
  defineProps<{
    location?: 'eth2' | 'liquity' | 'kraken' | null;
  }>(),
  {
    location: null
  }
);

const iconSize = '64px';

const pages = {
  eth2: defineAsyncComponent(
    () => import('@/components/staking/eth/EthStakingPage.vue')
  ),
  liquity: defineAsyncComponent(
    () => import('@/components/staking/liquity/LiquityPage.vue')
  ),
  kraken: defineAsyncComponent(
    () => import('@/components/staking/kraken/KrakenPage.vue')
  )
};

const { location } = toRefs(props);

const { t } = useI18n();

const staking = computed<StakingInfo[]>(() => [
  {
    id: 'eth2',
    icon: './assets/images/protocols/ethereum.svg',
    name: t('staking.eth2')
  },
  {
    id: 'liquity',
    icon: './assets/images/protocols/liquity.png',
    name: t('staking.liquity')
  },
  {
    id: 'kraken',
    icon: './assets/images/protocols/kraken.svg',
    name: t('staking.kraken')
  }
]);

const router = useRouter();

const lastLocation = useLocalStorage('rotki.staking.last_location', '');

const page = computed(() => {
  const selectedLocation = get(location);
  return selectedLocation ? pages[selectedLocation] : null;
});

const updateLocation = async (location: string) => {
  if (location) {
    set(lastLocation, location);
  }
  await router.push(Routes.STAKING.replace(':location*', location));
};

onBeforeMount(async () => {
  if (get(lastLocation)) {
    await updateLocation(get(lastLocation));
  }
});
</script>

<template>
  <div class="container">
    <RuiCard>
      <VSelect
        :value="location"
        outlined
        hide-details
        :items="staking"
        :label="t('staking_page.dropdown_label')"
        item-value="id"
        @change="updateLocation($event)"
      >
        <template v-for="slot in ['item', 'selection']" #[slot]="data">
          <div v-if="data.item" :key="slot" class="flex items-center gap-2">
            <AdaptiveWrapper width="24" height="24">
              <VImg
                width="24px"
                contain
                max-height="24px"
                :src="data.item.icon"
              />
            </AdaptiveWrapper>
            {{ data.item.name }}
          </div>
        </template>
      </VSelect>
    </RuiCard>

    <div v-if="page" class="pt-8">
      <Component :is="page" />
    </div>
    <div v-else>
      <div
        class="flex flex-row items-center justify-center justify-md-end mt-2 md:mr-6 text-rui-text-secondary gap-2"
      >
        <RuiIcon class="shrink-0" name="corner-left-up-line" />
        <div class="pt-3">
          {{ t('staking_page.dropdown_hint') }}
        </div>
      </div>
      <FullSizeContent>
        <div class="flex flex-col h-full items-center justify-center gap-6">
          <span class="font-bold text-h5">
            {{ t('staking_page.page.title') }}
          </span>
          <div class="flex gap-4">
            <InternalLink to="/staking/eth2">
              <VImg
                :width="iconSize"
                :height="iconSize"
                contain
                src="/assets/images/protocols/ethereum.svg"
              />
            </InternalLink>
            <InternalLink to="/staking/liquity">
              <VImg
                :width="iconSize"
                contain
                src="/assets/images/protocols/liquity.png"
              />
            </InternalLink>
            <InternalLink to="/staking/kraken">
              <VImg
                :width="iconSize"
                contain
                src="/assets/images/protocols/kraken.svg"
              />
            </InternalLink>
          </div>

          <div
            class="text-body-1 text-rui-text-secondary text-center max-w-[37rem]"
          >
            {{ t('staking_page.page.description') }}
          </div>
        </div>
      </FullSizeContent>
    </div>
  </div>
</template>
