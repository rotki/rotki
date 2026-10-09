<script setup lang="ts">
import type { EthereumValidator } from '@/modules/accounts/blockchain-accounts';
import type { StakingValidatorManage } from '@/modules/accounts/blockchain/use-account-manage';
import Eth2ValidatorLimitRow from '@/modules/accounts/blockchain/eth2/Eth2ValidatorLimitRow.vue';
import EthStakingValidatorsToolbar from '@/modules/accounts/EthStakingValidatorsToolbar.vue';
import { AssetAmountDisplay, FiatDisplay } from '@/modules/assets/amount-display/components';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';
import RowAppend from '@/modules/shell/components/RowAppend.vue';
import { useEthValidatorData } from '@/modules/staking/eth/use-eth-validator-data';
import { useEthValidatorOperations } from '@/modules/staking/eth/use-eth-validator-operations';
import { useEthValidatorUtils } from '@/modules/staking/eth/use-eth-validator-utils';
import ValidatorStatus from '@/modules/staking/eth/ValidatorStatus.vue';

const emit = defineEmits<{
  edit: [value: StakingValidatorManage];
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  cols,
  error,
  ethStakingValidators,
  fields,
  filters,
  pagination,
  rows,
  modelSelected,
  sort,
} = useEthValidatorData();

const emptyState = useTableEmptyState({ error, fallback: () => ({ label: t('data_table.no_data') }) });

const {
  accountOperation,
  confirmDelete,
  deleteSelected,
  edit: editValidator,
  refresh,
} = useEthValidatorOperations();

const { getOwnershipPercentage, useTotal, useTotalAmount } = useEthValidatorUtils();
const totalValue = useTotal(rows);
const totalAmount = useTotalAmount(rows);

function edit(account: EthereumValidator) {
  emit('edit', editValidator(account));
}

function deleteSelectedValidators() {
  deleteSelected(get(rows).data, get(modelSelected));
}

defineExpose({
  refresh,
});
</script>

<template>
  <TableFrame>
    <template #toolbar>
      <EthStakingValidatorsToolbar
        v-model:filters="filters"
        v-model:selected="modelSelected"
        :fields="fields"
        :deleting="accountOperation"
        @delete="deleteSelectedValidators()"
      />
    </template>
    <RuiDataTable
      v-model="modelSelected"
      v-model:sort.external="sort"
      v-model:pagination.external="pagination"
      dense
      row-attr="index"
      :cols="cols"
      :rows="rows.data"
      sticky-header
      show-select
      return-object
      :empty="emptyState"
    >
      <template #empty-description>
        <p class="max-w-prose mx-auto">
          {{ emptyState.description ?? t('blockchain_balances.validators.auto_detection_info') }}
        </p>
      </template>
      <template #item.index="{ row }">
        <HashLink
          class="my-2"
          location="eth2"
          :text="row.index.toString()"
        />
      </template>
      <template #item.publicKey="{ row }">
        <HashLink
          class="my-2"
          location="eth2"
          :show-icon="false"
          :text="row.publicKey.toString()"
        />
      </template>
      <template #item.status="{ row }">
        <ValidatorStatus :validator="row" />
      </template>
      <template #item.amount="{ row }">
        <AssetAmountDisplay
          asset="ETH"
          :amount="row.amount"
        />
      </template>
      <template #item.value="{ row }">
        <FiatDisplay :value="row.value" />
      </template>
      <template #item.ownershipPercentage="{ row }">
        <PercentageDisplay
          :value="getOwnershipPercentage(row)"
          :asset-padding="0.1"
        />
      </template>
      <template #item.actions="{ row }">
        <div class="flex justify-end mr-2">
          <RowActions
            :edit-tooltip="t('account_balances.edit_tooltip')"
            :disabled="accountOperation"
            @edit-click="edit(row)"
            @delete-click="confirmDelete(row)"
          />
        </div>
      </template>
      <template #body.prepend="{ colspan }">
        <Eth2ValidatorLimitRow :colspan="colspan" />
      </template>
      <template
        v-if="ethStakingValidators.length > 0"
        #body.append
      >
        <RowAppend
          label-colspan="4"
          :label="t('common.total')"
          :right-patch-colspan="cols.length - 2"
          class-name="[&>td]:p-4 text-sm"
        >
          <template #custom-columns>
            <td class="text-end">
              <AssetAmountDisplay
                asset="ETH"
                :amount="totalAmount"
              />
            </td>
          </template>
          <FiatDisplay :value="totalValue" />
        </RowAppend>
      </template>
    </RuiDataTable>
  </TableFrame>
</template>
