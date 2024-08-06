<script setup lang="ts">
import { type TablePaginationData, useBreakpoint } from '@rotki/ui-library';
import { Section } from '@/types/status';

definePage({
  name: 'defi-overview',
});

const page = ref(1);
const itemsPerPage = ref(9);

const store = useDefiStore();
const overviewStore = useDefiOverviewStore();
const { overview: currentOverview } = storeToRefs(overviewStore);
const section = Section.DEFI_OVERVIEW;

const { t } = useI18n();

const { isMdAndDown, isMd, is2xl } = useBreakpoint();

const firstLimit = computed(() => {
  if (get(isMdAndDown))
    return 4;

  if (get(isMd))
    return 6;

  if (get(is2xl))
    return 12;

  return 9;
});

const { shouldShowLoadingScreen, isLoading } = useStatusStore();

const loading = shouldShowLoadingScreen(section);
const refreshing = isLoading(section);

const refreshTooltip = computed<string>(() =>
  t('helpers.refresh_header.tooltip', {
    title: t('decentralized_overview.title').toLocaleLowerCase(),
  }),
);

const visibleData = computed(() => {
  const perPage = get(itemsPerPage);
  const start = (get(page) - 1) * perPage;
  return get(currentOverview).slice(start, start + perPage);
});

const limits = computed(() => {
  const first = get(firstLimit);
  return [first, first * 2, first * 4];
});

const paginationData = computed({
  get() {
    return {
      page: get(page),
      total: get(currentOverview).length,
      limit: get(itemsPerPage),
      limits: get(limits),
    };
  },
  set(value: TablePaginationData) {
    set(page, value.page);
    set(itemsPerPage, value.limit);
  },
});

async function refresh() {
  await store.fetchAllDefi(true);
}

watchImmediate(firstLimit, () => {
  set(itemsPerPage, get(firstLimit));
});

onMounted(async () => {
  await store.fetchAllDefi(false);
});
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.defi'), t('decentralized_overview.title')]">
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
      <template #message>
        {{ t('decentralized_overview.loading') }}
      </template>
    </ProgressScreen>
    <template v-else>
      <div>
        <RuiAlert
          type="warning"
          :title="t('common.important_notice')"
          class="mb-6"
        >
          {{ t('decentralized_overview.deprecated_warning') }}
        </RuiAlert>
        <NoDataScreen v-if="currentOverview.length === 0">
          <template #title>
            {{ t('decentralized_overview.empty_title') }}
          </template>
          {{ t('decentralized_overview.empty_subtitle') }}
        </NoDataScreen>
        <template v-else>
          <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
            <Overview
              v-for="summary in visibleData"
              :key="summary.protocol"
              :summary="summary"
            />
          </div>

          <RuiCard v-if="currentOverview.length > visibleData.length">
            <RuiTablePagination v-model="paginationData" />
          </RuiCard>
        </template>
      </div>
    </template>
  </TablePageLayout>
</template>
