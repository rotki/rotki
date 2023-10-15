<script setup lang="ts">
import { Section } from '@/types/status';

const store = useDefiStore();
const overviewStore = useDefiOverviewStore();
const { overview: currentOverview } = storeToRefs(overviewStore);
const section = Section.DEFI_OVERVIEW;

const { t } = useI18n();

const refresh = async () => {
  await store.fetchAllDefi(true);
};

onMounted(async () => {
  await store.fetchAllDefi(false);
});

const { shouldShowLoadingScreen, isLoading } = useStatusStore();

const loading = shouldShowLoadingScreen(section);
const refreshing = isLoading(section);
</script>

<template>
  <div>
    <RefreshHeader
      :loading="refreshing"
      :title="t('decentralized_overview.title')"
      @refresh="refresh()"
    />
    <ProgressScreen v-if="loading">
      <template #message>{{ t('decentralized_overview.loading') }}</template>
    </ProgressScreen>
    <NoDataScreen
      v-else-if="currentOverview.length === 0"
      :full="false"
      class="mt-16"
    >
      <template #title>
        {{ t('decentralized_overview.empty_title') }}
      </template>
      <span class="text-subtitle-2 text--secondary">
        {{ t('decentralized_overview.empty_subtitle') }}
      </span>
    </NoDataScreen>
    <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <Overview
        v-for="summary in currentOverview"
        :key="summary.protocol"
        :summary="summary"
      />
    </div>
  </div>
</template>
