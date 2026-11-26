<script setup lang="ts">
import { RuiTab, RuiTabs } from '@rotki/ui-library';
import { watchImmediate } from '@vueuse/core';
import { get } from '@vueuse/shared';
import { onBeforeMount } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import { definePage } from 'vue-router/experimental';
import { msg } from '@/message-key';
import ManualBalancesDialog from '@/modules/accounts/manual-balances/ManualBalancesDialog.vue';
import ManualBalancesPageButtons from '@/modules/accounts/manual-balances/ManualBalancesPageButtons.vue';
import ManualBalanceTable from '@/modules/accounts/manual-balances/ManualBalanceTable.vue';
import { useManualBalanceDraft } from '@/modules/balances/manual/use-manual-balance-draft';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { NoteLocation } from '@/modules/core/common/notes';
import { useHistoryDataFetching } from '@/modules/history/use-history-data-fetching';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.balances_sub.manual_balances'), icon: 'lu-notebook-pen', parent: '/balances/', order: 30, drawer: 'balances-manual', addAction: { labelKey: msg.$t('manual_balances.dialog.add.title') } },
    noteLocation: NoteLocation.BALANCES_MANUAL,
  },
  props: true,
});

const { tab } = defineProps<{
  tab: string;
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute('/balances/manual/[[tab]]');

const { fetchManualBalances } = useManualBalances();
const { fetchAssociatedLocations } = useHistoryDataFetching();

function goToTab(tab: string | number) {
  const currentRoute = get(route);
  if (currentRoute.params.tab === tab)
    return;
  router.push(`/balances/manual/${tab}`);
}

watchImmediate(route, (route) => {
  const { params } = route;

  if (!params.tab || params.tab === '0')
    router.replace('/balances/manual/assets');
}, { deep: true });

const { add, consumeAddQuery, modelBalance } = useManualBalanceDraft(() => tab);

onBeforeMount(async () => {
  await consumeAddQuery();
  await fetchManualBalances();
  await fetchAssociatedLocations();
});
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.balances'),
      t('navigation_menu.balances_sub.manual_balances'),
    ]"
  >
    <template #buttons>
      <ManualBalancesPageButtons @add="add()" />
    </template>

    <ManualBalanceTable
      :key="tab"
      :data-testid="tab === 'liabilities' ? 'manual-liabilities' : 'manual-balances'"
      :type="tab === 'liabilities' ? 'liabilities' : 'balances'"
      @edit="modelBalance = $event"
      @add="add()"
    >
      <template #toolbar>
        <RuiTabs
          :model-value="tab"
          variant="segmented"
          color="primary"
          @update:model-value="goToTab($event)"
        >
          <RuiTab value="assets">
            {{ t('common.assets') }}
          </RuiTab>
          <RuiTab value="liabilities">
            {{ t('common.liabilities') }}
          </RuiTab>
        </RuiTabs>
      </template>
    </ManualBalanceTable>

    <ManualBalancesDialog
      v-model="modelBalance"
      @update-tab="goToTab($event)"
    />
  </TablePageLayout>
</template>
