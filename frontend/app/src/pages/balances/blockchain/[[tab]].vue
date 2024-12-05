<script setup lang="ts">
import { startPromise } from '@shared/utils';
import {
  type AccountManageState,
  createNewBlockchainAccount,
} from '@/composables/accounts/blockchain/use-account-manage';
import AccountBalances from '@/components/accounts/AccountBalances.vue';
import EthStakingValidators from '@/components/accounts/EthStakingValidators.vue';
import { Module } from '@/types/modules';
import { NoteLocation } from '@/types/notes';
import { BalanceSource, DashboardTableType } from '@/types/settings/frontend-settings';
import { uniqueStrings } from '@/utils/data';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useBlockchainStore } from '@/store/blockchain';
import type { RouteLocationRaw } from 'vue-router';
import type { ComponentExposed } from 'vue-component-type-helpers';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.ACCOUNTS_BALANCES_BLOCKCHAIN,
  },
  name: 'accounts-balances-blockchain',
  props: true,
});

const props = defineProps<{
  tab: string;
}>();

const { tab } = toRefs(props);

const account = ref<AccountManageState>();
const balances = ref<ComponentExposed<typeof AccountBalances>>();
const search = ref('');
const chainsFilter = ref<string[]>([]);

const { t } = useI18n();
const router = useRouter();
const route = useRoute('accounts-balances-blockchain');

const { blockchainAssets } = useBlockchainAggregatedBalances();
const { isBlockchainLoading } = useAccountLoading();
const { isModuleEnabled } = useModules();
const { dashboardTablesVisibleColumns, unifyAccountsTable } = storeToRefs(useFrontendSettingsStore());
const { supportedChains } = useSupportedChains();
const { groups } = storeToRefs(useBlockchainStore());

const tableType = DashboardTableType.BLOCKCHAIN_ASSET_BALANCES;

const isEth2Enabled = isModuleEnabled(Module.ETH2);
const aggregatedBalances = blockchainAssets(chainsFilter);

const categories = computed(() => {
  if (get(unifyAccountsTable))
    return ['all'];

  const categoriesWithData = get(groups).map(item => item.category);

  return get(supportedChains)
    .map(item => item.type)
    .filter((value, index, array) => !['eth2', 'evmlike'].includes(value) && uniqueStrings(value, index, array))
    .filter(item => item === 'evm' || categoriesWithData.includes(item));
});

function goToFirstCategory() {
  router.replace(getTabLink(get(categories)[0]));
}

function refresh() {
  if (isDefined(balances))
    get(balances).refresh();
}

function getTabLink(category: string): RouteLocationRaw {
  return {
    name: 'accounts-balances-blockchain',
    params: {
      tab: category,
    },
    query: {
      keepScrollPosition: 'true',
    },
  };
}

watch([unifyAccountsTable, categories], () => {
  const tab = props.tab;
  if (tab && tab !== 'validators' && !get(categories).includes(tab))
    goToFirstCategory();
});

onMounted(() => {
  const { query } = get(route);

  if (query.add) {
    startPromise(nextTick(() => {
      set(account, createNewBlockchainAccount());
    }));
  }
});

watchImmediate(route, (route) => {
  const { params } = route;

  if (!params.tab)
    goToFirstCategory();
}, { deep: true });
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.accounts_balances'),
      t('navigation_menu.accounts_balances_sub.blockchain_balances'),
    ]"
  >
    <template #buttons>
      <PriceRefresh />
      <RuiButton
        data-cy="add-blockchain-balance"
        color="primary"
        @click="account = createNewBlockchainAccount()"
      >
        <template #prepend>
          <RuiIcon name="add-line" />
        </template>
        {{ t('blockchain_balances.add_account') }}
      </RuiButton>
      <HideSmallBalances :source="BalanceSource.BLOCKCHAIN" />
    </template>

    <div class="flex flex-col gap-8">
      <RuiCard>
        <div class="pb-6 flex flex-wrap lg:flex-nowrap justify-between gap-2 items-center">
          <CardTitle class="order-0 whitespace-nowrap">
            {{ t('blockchain_balances.title') }}
          </CardTitle>
          <div class="order-3 lg:order-1 flex flex-wrap md:flex-nowrap grow justify-end w-full lg:w-auto items-center gap-2 overflow-hidden pt-1.5 -mt-1 lg:pl-6">
            <ChainSelect
              v-model="chainsFilter"
              class="w-full lg:w-[30rem]"
              dense
              hide-details
              clearable
              chips
            />
            <RuiTextField
              v-model="search"
              variant="outlined"
              color="primary"
              dense
              prepend-icon="search-line"
              :label="t('common.actions.search')"
              hide-details
              clearable
              class="w-full lg:w-[16rem]"
              @click:clear="search = ''"
            />
          </div>
          <VisibleColumnsSelector
            class="order-2"
            :group="tableType"
            :group-label="t('blockchain_balances.group_label')"
          />
        </div>

        <AccountDialog
          v-model="account"
          @complete="refresh()"
        />
        <AssetBalances
          data-cy="blockchain-asset-balances"
          :loading="isBlockchainLoading"
          :balances="aggregatedBalances"
          :search="search"
          :details="{
            chains: chainsFilter,
          }"
          :visible-columns="dashboardTablesVisibleColumns[tableType]"
          sticky-header
        />
      </RuiCard>

      <div
        id="accounts-section"
        class="flex items-center -mb-4 justify-between gap-2"
      >
        <div class="flex-1 overflow-hidden">
          <RuiTabs
            color="primary"
            class="border border-default rounded bg-white dark:bg-rui-grey-900 flex max-w-min"
          >
            <template
              v-for="category in categories"
              :key="category"
            >
              <RuiTab
                link
                :to="getTabLink(category)"
                :data-cy="`${category}-tab`"
              >
                {{ t('account_balances.data_table.group', { type: category === 'evm' ? 'EVM' : toSentenceCase(category) }) }}
              </RuiTab>
            </template>
            <RuiTab
              v-if="isEth2Enabled"
              link
              :to="getTabLink('validators')"
            >
              {{ t('blockchain_balances.validators') }}
            </RuiTab>
          </RuiTabs>
        </div>

        <AccountBalancesSetting />
      </div>

      <Transition
        enter-from-class="opacity-0 translate-x-8"
        enter-active-class="w-full transform duration-300 transition"
        enter-to-class="opacity-100 translate-x-0"
        leave-active-class="hidden"
      >
        <AccountBalances
          v-if="tab !== 'validators'"
          :key="tab"
          ref="balances"
          :category="tab"
          @edit="account = $event"
        />

        <EthStakingValidators
          v-else
          @edit="account = $event"
        />
      </Transition>
    </div>
  </TablePageLayout>
</template>
