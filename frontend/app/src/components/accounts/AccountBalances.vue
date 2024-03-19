<script setup lang="ts">
import { SavedFilterLocation } from '@/types/filtering';
import { AccountExternalFilterSchema, type Filters, type Matcher } from '@/composables/filters/blockchain-account';
import { getGroupId } from '@/utils/blockchain/accounts';
import AccountBalancesTable from '@/components/accounts/AccountBalancesTable.vue';
import type { Collection } from '@/types/collection';
import type {
  BlockchainAccountGroupWithBalance,
  BlockchainAccountRequestPayload,
} from '@/types/blockchain/accounts';

const { t } = useI18n();

const visibleTags = ref<string[]>([]);
const accountTable = ref<InstanceType<typeof AccountBalancesTable>>();
const selection = ref<boolean>(false);

const { fetchAccounts: fetchAccountsPage } = useBlockchainStore();
const { handleBlockchainRefresh } = useRefresh();
const { fetchAccounts } = useBlockchains();

const {
  options,
  filters,
  matchers,
  setFilter,
  state: accounts,
  fetchData,
  setTableOptions,
} = usePaginationFilters<
    BlockchainAccountGroupWithBalance,
    BlockchainAccountRequestPayload,
    BlockchainAccountGroupWithBalance,
    Collection<BlockchainAccountGroupWithBalance>,
    Filters,
    Matcher
>(
  null,
  true,
  () => useBlockchainAccountFilter(t),
  fetchAccountsPage,
  {
    extraParams: computed(() => ({
      tags: get(visibleTags),
    })),
    onUpdateFilters(query) {
      const externalFilterSchema = AccountExternalFilterSchema.parse(query);
      if (externalFilterSchema.tags)
        set(visibleTags, externalFilterSchema.tags);
    },
  },
);

const { refreshDisabled, deleteDisabled, isDetectingTokens } = useBlockchainAccountLoading(fetchData);

async function refreshClick() {
  await fetchAccounts(undefined, true);
  await handleBlockchainRefresh();
  await fetchData();
}

onMounted(async () => {
  await fetchData();
});
</script>

<template>
  <RuiCard data-cy="account-balances">
    <template #header>
      <div class="flex flex-row items-center gap-2">
        <SummaryCardRefreshMenu
          data-cy="account-balances-refresh-menu"
          :disabled="refreshDisabled"
          :loading="isDetectingTokens"
          :tooltip="t('account_balances.refresh_tooltip')"
          @refresh="refreshClick()"
        >
          <template
            #refreshMenu
          >
            <BlockchainBalanceRefreshBehaviourMenu />
          </template>
        </SummaryCardRefreshMenu>
        <CardTitle class="ml-2">
          {{ t('blockchain_balances.accounts') }}
        </CardTitle>
      </div>
    </template>

    <div class="flex flex-col md:flex-row md:items-center gap-2">
      <div class="grow flex items-center gap-2">
        <!-- disabled temporarily kept because it's easy to reactivate -->
        <RuiTooltip
          v-if="selection"
          :popper="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <RuiButton
              data-cy="account-balances__delete-button"
              color="error"
              variant="outlined"
              :disabled="deleteDisabled || !selection"
              @click="accountTable?.confirmDelete()"
            >
              <template #prepend>
                <RuiIcon name="delete-bin-line" />
              </template>
              {{ t('common.actions.delete') }}
            </RuiButton>
          </template>
          {{ t('account_balances.delete_tooltip') }}
        </RuiTooltip>

        <RuiTooltip
          :popper="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <RuiButton
              class="ml-2"
              variant="outlined"
              color="primary"
              :loading="isDetectingTokens"
              :disabled="refreshDisabled"
              @click="handleBlockchainRefresh(undefined, true)"
            >
              <template #prepend>
                <RuiIcon name="refresh-line" />
              </template>

              {{ t('account_balances.detect_tokens.tooltip.redetect') }}
            </RuiButton>
          </template>
          {{ t('account_balances.detect_tokens.tooltip.redetect_all') }}
        </RuiTooltip>
      </div>
      <div class="flex items-center gap-4">
        <TagFilter
          v-model="visibleTags"
          class="max-w-[360px]"
          hide-details
        />
        <TableFilter
          :matches="filters"
          :matchers="matchers"
          :location="SavedFilterLocation.BLOCKCHAIN_ACCOUNTS"
          @update:matches="setFilter($event)"
        />
      </div>
    </div>

    <AccountBalancesTable
      ref="accountTable"
      class="mt-4"
      group
      :accounts="accounts"
      :options="options"
      :selection.sync="selection"
      @update:options="setTableOptions($event)"
    >
      <template #details="{ row }">
        <AccountGroupDetails :group-id="getGroupId(row)" />
      </template>
    </AccountBalancesTable>
  </ruicard>
</template>
