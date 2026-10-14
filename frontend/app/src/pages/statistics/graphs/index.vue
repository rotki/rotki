<script setup lang="ts">
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import { PremiumStatistics } from '@/modules/premium/premium';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import StatisticPlaceholder from '@/modules/statistics/StatisticPlaceholder.vue';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.statistics_sub.graphs'), icon: 'lu-chart-line', parent: '/statistics/', order: 10, drawer: 'statistics-graph' },
    noteLocation: NoteLocation.STATISTICS,
  },
});

const { t } = useI18n({ useScope: 'global' });

const refreshing = ref<boolean>(false);

const { allowed } = useFeatureAccess(PremiumFeature.GRAPHS_VIEW);
const { fetchNetValue } = useStatisticsDataFetching();

async function refresh(): Promise<void> {
  set(refreshing, true);
  try {
    await fetchNetValue();
  }
  finally {
    set(refreshing, false);
  }
}
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.statistics'), t('navigation_menu.statistics_sub.graphs')]">
    <template
      v-if="allowed"
      #buttons
    >
      <RuiButton
        variant="outlined"
        color="primary"
        :loading="refreshing"
        data-testid="refresh-graphs"
        @click="refresh()"
      >
        <template #prepend>
          <RuiIcon name="lu-refresh-cw" />
        </template>
        {{ t('common.refresh') }}
      </RuiButton>
    </template>
    <PremiumStatistics v-if="allowed" />
    <StatisticPlaceholder v-else />
  </TablePageLayout>
</template>
