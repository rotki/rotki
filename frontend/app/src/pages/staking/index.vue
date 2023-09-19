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
  <VContainer>
    <Card>
      <div class="pa-2">
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
            <VRow v-if="data.item" :key="slot" align="center">
              <VCol cols="auto">
                <AdaptiveWrapper width="24" height="24">
                  <VImg
                    width="24px"
                    contain
                    max-height="24px"
                    :src="data.item.icon"
                  />
                </AdaptiveWrapper>
              </VCol>
              <VCol class="pl-0">
                {{ data.item.name }}
              </VCol>
            </VRow>
          </template>
        </VSelect>
      </div>
    </Card>
    <div v-if="page" class="pt-4">
      <Component :is="page" />
    </div>
    <div v-else>
      <div
        class="d-flex flex-row align-center justify-md-end justify-center mt-2 mr-md-6"
      >
        <div class="flex-shrink-0">
          <VIcon>mdi-arrow-up-left</VIcon>
        </div>
        <div class="text--secondary pt-3 flex-shrink-0 ms-2">
          {{ t('staking_page.dropdown_hint') }}
        </div>
      </div>
      <FullSizeContent>
        <VRow align="center" justify="center">
          <VCol>
            <VRow align="center" justify="center">
              <VCol cols="auto">
                <span class="font-weight-bold text-h5">
                  {{ t('staking_page.page.title') }}
                </span>
              </VCol>
            </VRow>
            <VRow justify="center" class="mt-md-12 mt-4">
              <VCol cols="auto" class="mx-4">
                <InternalLink to="/staking/eth2">
                  <VImg
                    :width="iconSize"
                    :height="iconSize"
                    contain
                    src="/assets/images/protocols/ethereum.svg"
                  />
                </InternalLink>
              </VCol>
              <VCol cols="auto" class="mx-4">
                <InternalLink to="/staking/liquity">
                  <VImg
                    :width="iconSize"
                    contain
                    src="/assets/images/protocols/liquity.png"
                  />
                </InternalLink>
              </VCol>
              <VCol cols="auto" class="mx-4">
                <InternalLink to="/staking/kraken">
                  <VImg
                    :width="iconSize"
                    contain
                    src="/assets/images/protocols/kraken.svg"
                  />
                </InternalLink>
              </VCol>
            </VRow>

            <VRow class="mt-md-10 mt-2" justify="center">
              <VCol cols="auto">
                <div
                  class="font-weight-light text-h6"
                  :class="$style.description"
                >
                  {{ t('staking_page.page.description') }}
                </div>
              </VCol>
            </VRow>
          </VCol>
        </VRow>
      </FullSizeContent>
    </div>
  </VContainer>
</template>

<style lang="scss" module>
.content {
  height: calc(100% - 120px);
}

.description {
  text-align: center;
  max-width: 600px;
}
</style>
