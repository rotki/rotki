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

const refreshTooltip: ComputedRef<string> = computed(() =>
  t('helpers.refresh_header.tooltip', {
    title: t('decentralized_overview.title').toLocaleLowerCase()
  })
);
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.defi'), t('decentralized_overview.title')]"
  >
    <template #buttons>
      <RuiTooltip :open-delay="400">
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
        {{ refreshTooltip }}
      </RuiTooltip>
    </template>

    <ProgressScreen v-if="loading">
      <template #message>{{ t('decentralized_overview.loading') }}</template>
    </ProgressScreen>
    <NoDataScreen v-else-if="currentOverview.length === 0">
      <template #title>
        {{ t('decentralized_overview.empty_title') }}
      </template>
      {{ t('decentralized_overview.empty_subtitle') }}
    </NoDataScreen>
    <div v-else class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <Overview
        v-for="summary in currentOverview"
        :key="summary.protocol"
        :summary="summary"
      />
    </div>
  </TablePageLayout>
</template>
