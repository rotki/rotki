<template>
  <div>
    <full-size-content v-if="!isKrakenConnected">
      <v-row align="center" justify="center">
        <v-col>
          <v-row align="center" justify="center">
            <v-col cols="auto">
              <span class="font-weight-bold text-h5">
                {{ t('kraken_page.page.title') }}
              </span>
            </v-col>
          </v-row>
          <v-row justify="center" class="mt-md-12 mt-4">
            <v-col cols="auto" class="mx-4">
              <router-link to="/settings/api-keys/exchanges">
                <v-img
                  width="64px"
                  contain
                  src="/assets/images/exchanges/kraken.svg"
                />
              </router-link>
            </v-col>
          </v-row>

          <v-row class="mt-md-10 mt-2" justify="center">
            <v-col cols="auto">
              <div
                class="font-weight-light text-h6"
                :class="$style.description"
              >
                <i18n path="kraken_page.page.description">
                  <template #link>
                    <router-link to="/settings/api-keys/exchanges">
                      {{ t('kraken_page.page.api_key') }}
                    </router-link>
                  </template>
                </i18n>
              </div>
            </v-col>
          </v-row>
        </v-col>
      </v-row>
    </full-size-content>
    <progress-screen v-else-if="loading">
      <template #message>
        {{ t('kraken_page.loading') }}
      </template>
    </progress-screen>
    <div v-else>
      <kraken-staking />
    </div>
  </div>
</template>

<script setup lang="ts">
import FullSizeContent from '@/components/common/FullSizeContent.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import KrakenStaking from '@/components/staking/kraken/KrakenStaking.vue';
import { useSectionLoading } from '@/composables/common';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useKrakenStakingStore } from '@/store/staking/kraken';
import { SupportedExchange } from '@/types/exchanges';
import { Section } from '@/types/status';

const { shouldShowLoadingScreen } = useSectionLoading();
const { load } = useKrakenStakingStore();

const { connectedExchanges } = storeToRefs(useExchangeBalancesStore());
const isKrakenConnected = computed(() => {
  const exchanges = get(connectedExchanges);
  return !!exchanges.find(
    ({ location }) => location === SupportedExchange.KRAKEN
  );
});

onMounted(async () => {
  if (get(isKrakenConnected)) {
    await load(false);
  }
});

watch(isKrakenConnected, async isKrakenConnected => {
  if (isKrakenConnected) {
    await load(false);
  }
});

const loading = shouldShowLoadingScreen(Section.STAKING_KRAKEN);

const { t } = useI18n();
</script>

<style lang="scss" module>
.description {
  text-align: center;
  max-width: 600px;
}
</style>
