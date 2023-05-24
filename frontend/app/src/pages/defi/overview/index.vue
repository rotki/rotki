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
    <v-row class="mt-6">
      <v-col>
        <refresh-header
          :loading="refreshing"
          :title="t('decentralized_overview.title')"
          @refresh="refresh()"
        />
      </v-col>
    </v-row>
    <progress-screen v-if="loading">
      <template #message>{{ t('decentralized_overview.loading') }}</template>
    </progress-screen>
    <no-data-screen
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
    </no-data-screen>
    <v-row class="mt-4">
      <v-col
        v-for="summary in currentOverview"
        :key="summary.protocol.name"
        lg="6"
        xl="3"
      >
        <overview :summary="summary" />
      </v-col>
    </v-row>
  </div>
</template>
