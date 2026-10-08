<script setup lang="ts">
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import { usePremium } from '@/modules/premium/use-premium';
import GetPremiumPlaceholder from '@/modules/shell/components/GetPremiumPlaceholder.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import HistoricalBalancesView from '@/modules/statistics/historical-balances/components/HistoricalBalancesView.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.statistics_sub.historical_balances'), icon: 'lu-calendar-clock', parent: '/statistics/', order: 40, drawer: 'statistics-historical-balances' },
    noteLocation: NoteLocation.STATISTICS,
  },
});

const { t } = useI18n({ useScope: 'global' });

const premium = usePremium();
</script>

<template>
  <HistoricalBalancesView v-if="premium" />
  <TablePageLayout
    v-else
    :title="[t('navigation_menu.statistics_sub.historical_balances')]"
  >
    <GetPremiumPlaceholder
      :title="t('navigation_menu.statistics_sub.historical_balances')"
      :description="t('historical_balances.premium_description')"
    />
  </TablePageLayout>
</template>
