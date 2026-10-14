<script setup lang="ts">
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import WrappedContainer from '@/modules/statistics/wrapped/components/WrappedContainer.vue';
import WrappedContainerPlaceholder from '@/modules/statistics/WrappedContainerPlaceholder.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.statistics_sub.history_events'), icon: 'lu-chart-bar', parent: '/statistics/', order: 20, drawer: 'statistics-history-events' },
    noteLocation: NoteLocation.STATISTICS_HISTORY_EVENTS,
  },
});

const { t } = useI18n({ useScope: 'global' });

const { allowed } = useFeatureAccess(PremiumFeature.EVENT_ANALYSIS_VIEW);
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.statistics'), t('navigation_menu.statistics_sub.history_events')]">
    <WrappedContainer v-if="allowed" />
    <RuiCard
      v-else
      class="max-w-[920px] mx-auto"
    >
      <WrappedContainerPlaceholder />
    </RuiCard>
  </TablePageLayout>
</template>
