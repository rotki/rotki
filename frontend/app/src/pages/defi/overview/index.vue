<script setup lang="ts">
import { Section } from '@/types/status';

const store = useDefiStore();
const { overview: currentOverview } = storeToRefs(store);
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
    <VRow class="mt-6">
      <VCol>
        <RefreshHeader
          :loading="refreshing"
          :title="t('decentralized_overview.title')"
          @refresh="refresh()"
        />
      </VCol>
    </VRow>
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
    <VRow class="mt-4">
      <VCol
        v-for="summary in currentOverview"
        :key="summary.protocol.name"
        lg="6"
        xl="3"
      >
        <Overview :summary="summary" />
      </VCol>
    </VRow>
  </div>
</template>
