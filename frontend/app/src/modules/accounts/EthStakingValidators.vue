<script setup lang="ts">
import type { EthereumValidator } from '@/modules/accounts/blockchain-accounts';
import type { StakingValidatorManage } from '@/modules/accounts/blockchain/use-account-manage';
import type { SavedViewState } from '@/modules/core/table/pill/composables/use-saved-views';
import type { SavedView } from '@/modules/core/table/pill/core/saved-view';
import Eth2ValidatorLimitRow from '@/modules/accounts/blockchain/eth2/Eth2ValidatorLimitRow.vue';
import { AssetAmountDisplay, FiatDisplay } from '@/modules/assets/amount-display/components';
import { SavedFilterLocations } from '@/modules/core/table/filtering';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import PillViewsMenu from '@/modules/core/table/pill/PillViewsMenu.vue';
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
  ethStakingValidators,
  fields,
  filters,
  pagination,
  rows,
  modelSelected,
  sort,
} = useEthValidatorData();

const pillLabels = usePillBarLabels();

/**
 * The saved-view state for this table's bar.
 *
 * @remarks
 * Every pill here is filter-bound, so a saved view is its `matches` alone. `params` stays in the
 * shape the store expects, since that shape is shared with the param-bound bars.
 */
const pillState = computed<SavedViewState>(() => ({
  matches: get(filters),
  params: {},
}));

function applyView(view: SavedView): void {
  set(filters, view.matches);
}

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
  <RuiCard>
    <div class="flex flex-wrap items-center gap-2">
      <div class="flex gap-3">
        <RuiButton
          :disabled="modelSelected.length === 0"
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
          v-if="modelSelected.length > 0"
          class="flex gap-2 items-center text-sm"
        >
          {{ t('blockchain_balances.validators.selected', { count: modelSelected.length }) }}
          <RuiButton
            size="sm"
            class="!py-0 !px-1.5 !gap-0.5 dark:!bg-opacity-30 dark:!text-white"
            @click="modelSelected = []"
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
      <PillFilterBar
        v-model:matches="filters"
        class="flex-1 min-w-[16rem] bg-white dark:bg-rui-grey-900"
        :fields="fields"
        :labels="pillLabels"
      >
        <template #views="{ disabled }">
          <PillViewsMenu
            :fields="fields"
            :location="SavedFilterLocations.ETH_VALIDATORS"
            :state="pillState"
            :disabled="disabled"
            @apply="applyView($event)"
          />
        </template>
      </PillFilterBar>
    </div>
    <RuiDataTable
      v-model="modelSelected"
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
