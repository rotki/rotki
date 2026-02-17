<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { LidoCsmNodeOperator } from '@/types/staking';
import BalanceDisplay from '@/components/display/BalanceDisplay.vue';
import RowActions from '@/components/helper/RowActions.vue';
import { useLidoCsmApi } from '@/composables/api/staking/lido-csm';
import HashLink from '@/modules/common/links/HashLink.vue';
import { STETH_IDENTIFIER } from '@/modules/staking/lido-csm/constants';
import { useConfirmStore } from '@/store/confirm';
import { useMessageStore } from '@/store/message';

defineOptions({
  name: 'LidoCsmTable',
});

const { rows, loading } = defineProps<{
  rows: LidoCsmNodeOperator[];
  loading: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { show } = useConfirmStore();
const api = useLidoCsmApi();
const { setMessage } = useMessageStore();

const removingEntryKey = ref<string>('');

interface LidoCsmTableRow {
  key: string;
  address: string;
  nodeOperatorId: number;
  operatorTypeLabel?: string;
  operatorTypeId?: number;
  bondCurrent?: BigNumber;
  bondRequired?: BigNumber;
  bondClaimable?: BigNumber;
  totalDeposited?: number;
  rewardsPending?: BigNumber;
}

const tableRows = computed<LidoCsmTableRow[]>(() => rows.map((entry) => {
  const metrics = entry.metrics;
  const operatorType = metrics?.operatorType;
  const bond = metrics?.bond;
  const keys = metrics?.keys;
  const rewards = metrics?.rewards;

  return {
    address: entry.address,
    bondClaimable: bond?.claimable,
    bondCurrent: bond?.current,
    bondRequired: bond?.required,
    key: `${entry.address}-${entry.nodeOperatorId}`,
    nodeOperatorId: entry.nodeOperatorId,
    operatorTypeId: operatorType?.id,
    operatorTypeLabel: operatorType?.label,
    rewardsPending: rewards?.pending,
    totalDeposited: keys?.totalDeposited,
  };
}));

const tableColumns = computed<DataTableColumn<LidoCsmTableRow>[]>(() => [{
  key: 'address',
  label: t('staking_page.lido_csm.table.address'),
}, {
  key: 'nodeOperatorId',
  label: t('staking_page.lido_csm.table.node_operator'),
}, {
  key: 'operatorTypeLabel',
  label: t('staking_page.lido_csm.table.operator_type'),
}, {
  key: 'bondCurrent',
  label: t('staking_page.lido_csm.table.bond_current'),
}, {
  key: 'bondRequired',
  label: t('staking_page.lido_csm.table.bond_required'),
}, {
  key: 'bondClaimable',
  label: t('staking_page.lido_csm.table.bond_claimable'),
}, {
  key: 'totalDeposited',
  label: t('staking_page.lido_csm.table.keys_total'),
}, {
  key: 'rewardsPending',
  label: t('staking_page.lido_csm.table.rewards_pending'),
}, {
  align: 'end',
  key: 'actions',
  label: t('staking_page.lido_csm.table.actions'),
}]);

function handleRemove(address: string, nodeOperatorIdValue: number): void {
  show(
    {
      message: t('staking_page.lido_csm.messages.confirm_delete_message', { address, nodeOperatorId: nodeOperatorIdValue }),
      title: t('staking_page.lido_csm.messages.confirm_delete_title'),
    },
    async () => {
      const key = `${address}-${nodeOperatorIdValue}`;
      set(removingEntryKey, key);
      try {
        await api.deleteNodeOperator({
          address,
          nodeOperatorId: nodeOperatorIdValue,
        });
        emit('refresh');
      }
      catch (error: unknown) {
        setMessage({
          description: t('staking_page.lido_csm.messages.delete_failed', { message: error instanceof Error ? error.message : String(error) }),
        });
      }
      finally {
        set(removingEntryKey, '');
      }
    },
  );
}
</script>

<template>
  <RuiCard>
    <div class="space-y-4 overflow-x-auto">
      <p class="text-sm text-rui-text-secondary">
        {{ t('staking_page.lido_csm.table.description') }}
      </p>
      <RuiDataTable
        dense
        outlined
        class="min-w-full"
        row-attr="key"
        :cols="tableColumns"
        :rows="tableRows"
        :loading="loading"
        :empty="{ label: t('staking_page.lido_csm.table.empty') }"
      >
        <template #item.address="{ row }">
          <HashLink
            :text="row.address"
            location="ethereum"
          />
        </template>
        <template #item.nodeOperatorId="{ row }">
          <span class="text-sm">
            #{{ row.nodeOperatorId }}
          </span>
        </template>
        <template #item.operatorTypeLabel="{ row }">
          <span class="font-medium text-sm">
            {{ row.operatorTypeLabel ?? t('staking_page.lido_csm.table.not_available') }}
          </span>
        </template>
        <template #item.bondCurrent="{ row }">
          <BalanceDisplay
            v-if="row.bondCurrent"
            :asset="STETH_IDENTIFIER"
            :value="{ amount: row.bondCurrent }"
            calculate-value
          />
          <span
            v-else
            class="text-sm text-rui-text-secondary"
          >
            {{ t('staking_page.lido_csm.table.not_available') }}
          </span>
        </template>
        <template #item.bondRequired="{ row }">
          <BalanceDisplay
            v-if="row.bondRequired"
            :asset="STETH_IDENTIFIER"
            :value="{ amount: row.bondRequired }"
            calculate-value
          />
          <span
            v-else
            class="text-sm text-rui-text-secondary"
          >
            {{ t('staking_page.lido_csm.table.not_available') }}
          </span>
        </template>
        <template #item.bondClaimable="{ row }">
          <BalanceDisplay
            v-if="row.bondClaimable"
            :asset="STETH_IDENTIFIER"
            :value="{ amount: row.bondClaimable }"
            calculate-value
          />
          <span
            v-else
            class="text-sm text-rui-text-secondary"
          >
            {{ t('staking_page.lido_csm.table.not_available') }}
          </span>
        </template>
        <template #item.totalDeposited="{ row }">
          <span class="text-sm">
            {{ row.totalDeposited ?? t('staking_page.lido_csm.table.not_available') }}
          </span>
        </template>
        <template #item.rewardsPending="{ row }">
          <BalanceDisplay
            v-if="row.rewardsPending"
            :asset="STETH_IDENTIFIER"
            :value="{ amount: row.rewardsPending }"
            calculate-value
          />
          <span
            v-else
            class="text-sm text-rui-text-secondary"
          >
            {{ t('staking_page.lido_csm.table.not_available') }}
          </span>
        </template>
        <template #item.actions="{ row }">
          <RowActions
            no-edit
            align="end"
            :disabled="removingEntryKey === row.key"
            :delete-tooltip="t('staking_page.lido_csm.table.remove')"
            @delete-click="handleRemove(row.address, row.nodeOperatorId)"
          />
        </template>
      </RuiDataTable>
    </div>
  </RuiCard>
</template>
