<script setup lang="ts">
import {
  type AccountManageState,
  createNewBlockchainAccount,
} from '@/composables/accounts/blockchain/use-account-manage';
import AccountBalances from '@/components/accounts/AccountBalances.vue';
import EthStakingValidators from '@/components/accounts/EthStakingValidators.vue';
import { Module } from '@/types/modules';
import { NoteLocation } from '@/types/notes';
import type { RouteLocationRaw } from 'vue-router';
import type { ComponentExposed } from 'vue-component-type-helpers';

const props = defineProps<{
  tab: string;
}>();

const { tab } = toRefs(props);

definePage({
  name: 'accounts-balances-blockchain',
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.ACCOUNTS_BALANCES_BLOCKCHAIN,
  },
  props: true,
});

const account = ref<AccountManageState>();
const balances = ref<ComponentExposed<typeof AccountBalances>>();

const { t } = useI18n();

const router = useRouter();
const route = useRoute('accounts-balances-blockchain');

const { blockchainAssets } = useBlockchainAggregatedBalances();
const { isBlockchainLoading } = useAccountLoading();
const { isModuleEnabled } = useModules();

const isEth2Enabled = isModuleEnabled(Module.ETH2);

const { unifyAccountsTable } = storeToRefs(useFrontendSettingsStore());
const { supportedChains } = useSupportedChains();
const { groups } = storeToRefs(useBlockchainStore());

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
        v-blur
        data-cy="add-blockchain-balance"
        color="primary"
        @click="account = createNewBlockchainAccount()"
      >
        <template #prepend>
          <RuiIcon name="add-line" />
        </template>
        {{ t('blockchain_balances.add_account') }}
      </RuiButton>
    </template>

    <div class="flex flex-col gap-8">
      <RuiCard>
        <template #header>
          <CardTitle>{{ t('blockchain_balances.title') }}</CardTitle>
        </template>

        <AccountDialog
          v-model="account"
          @complete="refresh()"
        />
        <AssetBalances
          data-cy="blockchain-asset-balances"
          :loading="isBlockchainLoading"
          :title="t('blockchain_balances.per_asset.title')"
          :balances="blockchainAssets"
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
