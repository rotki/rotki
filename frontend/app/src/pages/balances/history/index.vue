<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { definePage } from 'vue-router/experimental';
import { msg } from '@/message-key';
import AccountHistoryView from '@/modules/balances/account-history/components/AccountHistoryView.vue';
import { usePremium } from '@/modules/premium/use-premium';
import GetPremiumPlaceholder from '@/modules/shell/components/GetPremiumPlaceholder.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.balances_sub.account_history'), icon: 'lu-chart-line', parent: '/balances/', order: 50, drawer: 'balances-history' },
  },
});

const { t } = useI18n({ useScope: 'global' });

const premium = usePremium();
</script>

<template>
  <AccountHistoryView v-if="premium" />
  <TablePageLayout
    v-else
    :title="[t('navigation_menu.balances'), t('navigation_menu.balances_sub.account_history')]"
  >
    <GetPremiumPlaceholder
      :title="t('navigation_menu.balances_sub.account_history')"
      :description="t('account_history.premium_description')"
    />
  </TablePageLayout>
</template>
