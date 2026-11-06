<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { DataTableColumn } from '@rotki/ui-library';
import type { LidoCsmNodeOperator } from '@/modules/staking/staking-types';
import { AssetAmountDisplay } from '@/modules/assets/amount-display/components';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';
import BalanceDisplay from '@/modules/shell/components/display/BalanceDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';
import { useLidoCsmApi } from '@/modules/staking/api/use-lido-csm-api';
import { STETH_IDENTIFIER } from '@/modules/staking/lido-csm/constants';
import { useLidoCsmStakingModules } from '@/modules/staking/lido-csm/use-lido-csm-staking-modules';

defineOptions({
  name: 'LidoCsmTable',
});

const { rows, loading } = defineProps<{
  rows: LidoCsmNodeOperator[];
  loading: boolean;
}>();

const emit = defineEmits<{
  add: [];
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { show } = useConfirmStore();
const api = useLidoCsmApi();
const { setMessage } = useMessageStore();
const { stakingModuleLabel } = useLidoCsmStakingModules();

const removingEntryKey = ref<string>('');

interface LidoCsmTableRow {
  key: string;
  address: string;
  nodeOperatorId: number;
  stakingModuleId: number;
  operatorTypeLabel?: string;
  operatorTypeId?: number;
  bondCurrent?: BigNumber;
  bondRequired?: BigNumber;
  bondClaimable?: BigNumber;
  /** How far the bond falls below what is required, set only when it does. */
  bondShortfall?: BigNumber;
  totalDeposited?: number;
  rewardsPending?: BigNumber;
}

type LidoCsmMetrics = LidoCsmNodeOperator['metrics'];

/**
 * The bond figures, plus the shortfall of an under-bonded operator: in CSM such an operator cannot
 * add validators and has the difference taken from its rewards, so it is flagged on the row.
 */
function bondFields(bond: NonNullable<LidoCsmMetrics>['bond'] | undefined): Pick<LidoCsmTableRow, 'bondClaimable' | 'bondCurrent' | 'bondRequired' | 'bondShortfall'> {
  const shortfall = bond ? bond.required.minus(bond.current) : undefined;
  return {
    bondClaimable: bond?.claimable,
    bondCurrent: bond?.current,
    bondRequired: bond?.required,
    bondShortfall: shortfall?.gt(0) ? shortfall : undefined,
  };
}

/** Flattens the optional metric groups onto the row; a group the backend omitted leaves them unset. */
function metricFields(metrics: LidoCsmMetrics): Omit<LidoCsmTableRow, 'address' | 'key' | 'nodeOperatorId' | 'stakingModuleId'> {
  const { bond, keys, operatorType, rewards } = metrics ?? {};

  return {
    ...bondFields(bond),
    operatorTypeId: operatorType?.id,
    operatorTypeLabel: operatorType?.label,
    rewardsPending: rewards?.pending,
    totalDeposited: keys?.totalDeposited,
  };
}

function rowKey(address: string, stakingModuleId: number, nodeOperatorId: number): string {
  return `${address}-${stakingModuleId}-${nodeOperatorId}`;
}

const tableRows = computed<LidoCsmTableRow[]>(() => rows.map(entry => ({
  address: entry.address,
  key: rowKey(entry.address, entry.stakingModuleId, entry.nodeOperatorId),
  nodeOperatorId: entry.nodeOperatorId,
  stakingModuleId: entry.stakingModuleId,
  ...metricFields(entry.metrics),
})));

const tableColumns = computed<DataTableColumn<LidoCsmTableRow>[]>(() => [{
  key: 'address',
  label: t('staking_page.lido_csm.table.address'),
}, {
  key: 'nodeOperatorId',
  label: t('staking_page.lido_csm.table.node_operator'),
}, {
  // figures align at the end, under headers that do too
  align: 'end',
  key: 'bondCurrent',
  label: t('staking_page.lido_csm.table.bond_current'),
}, {
  align: 'end',
  key: 'bondRequired',
  label: t('staking_page.lido_csm.table.bond_required'),
}, {
  align: 'end',
  key: 'bondClaimable',
  label: t('staking_page.lido_csm.table.bond_claimable'),
}, {
  align: 'end',
  key: 'totalDeposited',
  label: t('staking_page.lido_csm.table.keys_total'),
}, {
  align: 'end',
  key: 'rewardsPending',
  label: t('staking_page.lido_csm.table.rewards_pending'),
}, {
  // one delete button needs no header, and its label was what pushed the table past the page
  align: 'end',
  key: 'actions',
  label: '',
}]);

function handleRemove({ address, nodeOperatorId, stakingModuleId }: LidoCsmTableRow): void {
  show(
    {
      message: t('staking_page.lido_csm.messages.confirm_delete_message', {
        address,
        module: stakingModuleLabel(stakingModuleId),
        nodeOperatorId,
      }),
      title: t('staking_page.lido_csm.messages.confirm_delete_title'),
    },
    async () => {
      set(removingEntryKey, rowKey(address, stakingModuleId, nodeOperatorId));
      try {
        await api.deleteNodeOperator({
          address,
          nodeOperatorId,
          stakingModuleId,
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
  <div class="overflow-x-auto">
    <RuiDataTable
      dense
      outlined
      class="min-w-full"
      item-class="h-14.25"
      row-attr="key"
      :cols="tableColumns"
      :rows="tableRows"
      :loading="loading"
    >
      <template #no-data>
        <TableEmptyNotice
          icon="lu-server"
          :title="t('staking_page.lido_csm.table.empty')"
          :description="t('staking_page.lido_csm.description')"
        >
          <RuiButton
            color="primary"
            data-testid="lido-csm-empty-add"
            @click="emit('add')"
          >
            <template #prepend>
              <RuiIcon name="lu-plus" />
            </template>
            {{ t('staking_page.lido_csm.form.submit') }}
          </RuiButton>
        </TableEmptyNotice>
      </template>
      <template #item.address="{ row }">
        <HashLink
          :text="row.address"
          location="ethereum"
        />
      </template>
      <template #item.nodeOperatorId="{ row }">
        <div class="flex flex-col">
          <span
            class="text-sm"
            data-testid="lido-csm-node-operator-id"
          >
            {{ stakingModuleLabel(row.stakingModuleId) }} #{{ row.nodeOperatorId }}
          </span>
          <span
            v-if="row.operatorTypeLabel"
            class="text-caption text-rui-text-secondary"
            data-testid="lido-csm-operator-type"
          >
            {{ row.operatorTypeLabel }}
          </span>
        </div>
      </template>
      <template #item.bondCurrent="{ row }">
        <div
          v-if="row.bondCurrent"
          class="flex items-center justify-end gap-2"
        >
          <RuiTooltip
            v-if="row.bondShortfall"
            :open-delay="200"
            :class-names="{ tooltip: 'max-w-64' }"
          >
            <template #activator>
              <RuiIcon
                name="lu-triangle-alert"
                size="16"
                class="text-rui-warning"
                data-testid="lido-csm-bond-short"
              />
            </template>
            <i18n-t
              scope="global"
              keypath="staking_page.lido_csm.table.bond_short"
              tag="span"
            >
              <template #amount>
                <AssetAmountDisplay
                  :asset="STETH_IDENTIFIER"
                  :amount="row.bondShortfall"
                />
              </template>
            </i18n-t>
          </RuiTooltip>
          <BalanceDisplay
            :asset="STETH_IDENTIFIER"
            :value="{ amount: row.bondCurrent }"
            calculate-value
            no-icon
          />
        </div>
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
          no-icon
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
          no-icon
        />
        <span
          v-else
          class="text-sm text-rui-text-secondary"
        >
          {{ t('staking_page.lido_csm.table.not_available') }}
        </span>
      </template>
      <template #item.totalDeposited="{ row }">
        <span
          v-if="row.totalDeposited !== undefined"
          class="text-sm"
        >
          {{ row.totalDeposited }}
        </span>
        <span
          v-else
          class="text-sm text-rui-text-secondary"
        >
          {{ t('staking_page.lido_csm.table.not_available') }}
        </span>
      </template>
      <template #item.rewardsPending="{ row }">
        <BalanceDisplay
          v-if="row.rewardsPending"
          :asset="STETH_IDENTIFIER"
          :value="{ amount: row.rewardsPending }"
          calculate-value
          no-icon
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
          @delete-click="handleRemove(row)"
        />
      </template>
    </RuiDataTable>
  </div>
</template>
