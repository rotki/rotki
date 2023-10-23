<script setup lang="ts">
import { SupportedExchange } from '@/types/exchanges';
import { Section } from '@/types/status';
import { Routes } from '@/router/routes';

const { shouldShowLoadingScreen, isLoading } = useStatusStore();
const { load, $reset } = useKrakenStakingStore();

const { connectedExchanges } = storeToRefs(useExchangesStore());
const isKrakenConnected = computed(() => {
  const exchanges = get(connectedExchanges);
  return exchanges.some(
    ({ location }) => location === SupportedExchange.KRAKEN
  );
});

onMounted(async () => {
  if (get(isKrakenConnected)) {
    await load(false);
  }
});

onUnmounted(() => {
  $reset();
});

watch(isKrakenConnected, async isKrakenConnected => {
  if (isKrakenConnected) {
    await load(false);
  }
});

const loading = shouldShowLoadingScreen(Section.STAKING_KRAKEN);
const refreshing = isLoading(Section.STAKING_KRAKEN);

const { t } = useI18n();

const refresh = () => load(true);
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.staking'), t('staking.kraken')]"
    child
  >
    <template #buttons>
      <RuiTooltip open-delay="400">
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            :loading="refreshing || loading"
            @click="refresh()"
          >
            <template #prepend>
              <RuiIcon name="refresh-line" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('kraken_staking_events.refresh_tooltip') }}
      </RuiTooltip>
    </template>

    <FullSizeContent v-if="!isKrakenConnected">
      <VRow align="center" justify="center">
        <VCol>
          <VRow align="center" justify="center">
            <VCol cols="auto">
              <span class="font-bold text-h5">
                {{ t('kraken_page.page.title') }}
              </span>
            </VCol>
          </VRow>
          <VRow justify="center" class="mt-md-12 mt-4">
            <VCol cols="auto" class="mx-4">
              <InternalLink :to="Routes.API_KEYS_EXCHANGES">
                <VImg
                  width="64px"
                  contain
                  src="/assets/images/protocols/kraken.svg"
                />
              </InternalLink>
            </VCol>
          </VRow>

          <VRow class="mt-md-10 mt-2" justify="center">
            <VCol cols="auto">
              <div class="font-light text-h6" :class="$style.description">
                <i18n path="kraken_page.page.description">
                  <template #link>
                    <InternalLink :to="Routes.API_KEYS_EXCHANGES">
                      {{ t('kraken_page.page.api_key') }}
                    </InternalLink>
                  </template>
                </i18n>
              </div>
            </VCol>
          </VRow>
        </VCol>
      </VRow>
    </FullSizeContent>
    <ProgressScreen v-else-if="loading">
      <template #message>
        {{ t('kraken_page.loading') }}
      </template>
    </ProgressScreen>
    <KrakenStaking v-else />
  </TablePageLayout>
</template>

<style lang="scss" module>
.description {
  text-align: center;
  max-width: 600px;
}
</style>
