<script setup lang="ts">
import type { EthereumValidator } from '@/modules/accounts/blockchain-accounts';
import type { StakingValidatorManage } from '@/modules/accounts/blockchain/use-account-manage';
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import Eth2ValidatorLimitRow from '@/modules/accounts/blockchain/eth2/Eth2ValidatorLimitRow.vue';
import EthStakingValidatorsToolbar from '@/modules/accounts/EthStakingValidatorsToolbar.vue';
import { AssetAmountDisplay, FiatDisplay } from '@/modules/assets/amount-display/components';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
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
  deleteConfirm,
  deleteFailure,
  deleteSelected,
  deleteSelectedConfirm,
  deleteValidator,
  edit: editValidator,
  refresh,
} = useEthValidatorOperations();

const { getOwnershipPercentage, useTotal, useTotalAmount } = useEthValidatorUtils();
const totalValue = useTotal(rows);
const totalAmount = useTotalAmount(rows);

const selectionMode = shallowRef<boolean>(false);

/** `undefined` outside selection mode, which is what makes the table drop its checkbox column. */
const tableSelection = computed<number[] | undefined>({
  get: () => (get(selectionMode) ? get(modelSelected) : undefined),
  set: (value?: number[]) => set(modelSelected, value ?? []),
});

function edit(account: EthereumValidator) {
  emit('edit', editValidator(account));
}

const selectedDeleteQuestion = computed<ConfirmQuestion | undefined>(
  () => deleteSelectedConfirm(get(rows).data, get(modelSelected)),
);

async function deleteSelectedValidators(): Promise<void> {
  await deleteSelected(get(rows).data, get(modelSelected));
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
        v-model:selection-mode="selectionMode"
        :fields="fields"
        :deleting="accountOperation"
        :delete-question="selectedDeleteQuestion"
        @delete="deleteSelectedValidators()"
      />
    </template>
    <FailureStrip
      v-if="deleteFailure"
      class="m-3"
      :title="deleteFailure.title"
      :failure="deleteFailure.failure"
      data-testid="eth-validators-delete-error"
    />
    <RuiDataTable
      v-model="tableSelection"
      v-model:sort.external="sort"
      v-model:pagination.external="pagination"
      dense
      row-attr="index"
      :cols="cols"
      :rows="rows.data"
      sticky-header
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
            :delete-confirm="deleteConfirm(row)"
            @edit-click="edit(row)"
            @delete-click="deleteValidator(row)"
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
          variant="fixed"
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
