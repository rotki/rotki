<script setup lang="ts">
import type { EthereumValidator } from '@/modules/accounts/blockchain-accounts';
import type { StakingValidatorManage } from '@/modules/accounts/blockchain/use-account-manage';
import Eth2ValidatorLimitRow from '@/modules/accounts/blockchain/eth2/Eth2ValidatorLimitRow.vue';
import { AssetAmountDisplay, FiatDisplay } from '@/modules/assets/amount-display/components';
import { SavedFilterLocation } from '@/modules/core/table/filtering';
import TableFilter from '@/modules/core/table/TableFilter.vue';
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

// Use composables
const {
  cols,
  ethStakingValidators,
  filters,
  matchers,
  pagination,
  rows,
  selected,
  sort,
} = useEthValidatorData();

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
  deleteSelected(get(rows).data, get(selected));
}

defineExpose({
  refresh,
});
</script>

<template>
  <RuiCard>
    <div class="flex flex-row flex-wrap items-center gap-2">
      <div class="flex flex-row gap-3">
        <RuiButton
          :disabled="selected.length === 0"
          class="h-10"
          variant="outlined"
          color="error"
          :loading="accountOperation"
          @click="deleteSelectedValidators()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-trash-2"
              size="16"
            />
          </template>
          {{ t('common.actions.delete') }}
        </RuiButton>
        <div
          v-if="selected.length > 0"
          class="flex gap-2 items-center text-sm"
        >
          {{ t('blockchain_balances.validators.selected', { count: selected.length }) }}
          <RuiButton
            size="sm"
            class="!py-0 !px-1.5 !gap-0.5 dark:!bg-opacity-30 dark:!text-white"
            @click="selected = []"
          >
            <template #prepend>
              <RuiIcon
                name="lu-x"
                size="14"
              />
            </template>
            {{ t('common.actions.clear_selection') }}
          </RuiButton>
        </div>
      </div>
      <TableFilter
        v-model:matches="filters"
        :matchers="matchers"
        class="ml-auto max-w-[calc(100vw-11rem)] w-[25rem] lg:max-w-[30rem]"
        :location="SavedFilterLocation.ETH_VALIDATORS"
      />
    </div>
    <RuiDataTable
      v-model="selected"
      v-model:sort.external="sort"
      v-model:pagination.external="pagination"
      class="mt-4"
      dense
      row-attr="index"
      outlined
      :cols="cols"
      :rows="rows.data"
      sticky-header
      show-select
      return-object
      :empty="{
        label: t('data_table.no_data'),
      }"
    >
      <template #empty-description>
        <p class="max-w-prose mx-auto">
          {{ t('blockchain_balances.validators.auto_detection_info') }}
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
  </RuiCard>
</template>
