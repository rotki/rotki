<script setup lang="ts">
import { Section } from '@/types/status';
import { Routes } from '@/router/routes';
import { useExchangesStore } from '@/store/exchanges';
import { useKrakenStakingStore } from '@/store/staking/kraken';
import { useStatusStore } from '@/store/status';
import KrakenStaking from '@/components/staking/kraken/KrakenStaking.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import InternalLink from '@/components/helper/InternalLink.vue';
import AppImage from '@/components/common/AppImage.vue';
import FullSizeContent from '@/components/common/FullSizeContent.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import type { RouteLocationRaw } from 'vue-router';

const { isLoading, shouldShowLoadingScreen } = useStatusStore();
const { $reset, load } = useKrakenStakingStore();

const { connectedExchanges } = storeToRefs(useExchangesStore());
const isKrakenConnected = computed(() => {
  const exchanges = get(connectedExchanges);
  return exchanges.some(({ location }) => location === 'kraken');
});

onMounted(async () => {
  if (get(isKrakenConnected))
    await load(false);
});

onUnmounted(() => {
  $reset();
});

watch(isKrakenConnected, async (isKrakenConnected) => {
  if (isKrakenConnected)
    await load(false);
});

const loading = shouldShowLoadingScreen(Section.STAKING_KRAKEN);
const refreshing = isLoading(Section.STAKING_KRAKEN);

const { t } = useI18n();

const refresh = () => load(true);

const addKrakenApiKeysLink: RouteLocationRaw = {
  path: `${Routes.API_KEYS_EXCHANGES}`,
  query: {
    add: 'true',
  },
};
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.staking'), t('staking.kraken')]"
    child
  >
    <template #buttons>
      <RuiTooltip
        v-if="isKrakenConnected"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            :loading="refreshing || loading"
            @click="refresh()"
          >
            <template #prepend>
              <RuiIcon name="lu-refresh-ccw" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('kraken_staking_events.refresh_tooltip') }}
      </RuiTooltip>
    </template>

    <FullSizeContent
      v-if="!isKrakenConnected"
      class="gap-4"
    >
      <span class="font-bold text-h5">
        {{ t('kraken_page.page.title') }}
      </span>

      <InternalLink :to="addKrakenApiKeysLink">
        <AppImage
          width="64px"
          contain
          src="/assets/images/protocols/kraken.svg"
        />
      </InternalLink>

      <i18n-t
        tag="h6"
        keypath="kraken_page.page.description"
        class="font-light text-h6 text-rui-text-secondary"
      >
        <template #link>
          <InternalLink :to="addKrakenApiKeysLink">
            {{ t('kraken_page.page.api_key') }}
          </InternalLink>
        </template>
      </i18n-t>
    </FullSizeContent>
    <ProgressScreen v-else-if="loading">
      <template #message>
        {{ t('kraken_page.loading') }}
      </template>
    </ProgressScreen>
    <KrakenStaking v-else />
  </TablePageLayout>
</template>
