<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { isEmpty } from 'lodash-es';
import { isBtcChain } from '@/types/blockchain/chains';
import { TaskType } from '@/types/task-type';
import { Section } from '@/types/status';
import { getAccountAddress } from '@/utils/blockchain/accounts';
import type { BlockchainAccountWithBalance, XpubData } from '@/types/blockchain/accounts';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { Balance } from '@rotki/common';

const props = withDefaults(
  defineProps<{
    balances: BlockchainAccountWithBalance[];
    blockchain: string;
    visibleTags: string[];
    loopring?: boolean;
  }>(),
  {
    loopring: false,
  },
);

const emit = defineEmits<{
  (e: 'edit-click', account: BlockchainAccountWithBalance): void;
  (e: 'delete-xpub', payload: BlockchainAccountWithBalance<XpubData>): void;
}>();

const selected = defineModel<string[]>('selected', { required: true });

const { t } = useI18n();

type Account = BlockchainAccountWithBalance & {
  identifier: string;
};

const { balances, blockchain, visibleTags, loopring } = toRefs(props);

const rootAttrs = useAttrs();

const { isTaskRunning } = useTaskStore();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { getEthDetectedTokensInfo, detectingTokens } = useTokenDetection(blockchain);
const { getNativeAsset, supportsTransactions } = useSupportedChains();
const { assetSymbol } = useAssetInfoRetrieval();
const { addressNameSelector } = useAddressesNamesStore();
const { getAddressBalances } = useBlockchainStore();

const { isLoading } = useStatusStore();
const loading = computed<boolean>(() => {
  const section = get(loopring) ? 'loopring' : get(blockchain);
  return get(isLoading(Section.BLOCKCHAIN, section));
});

const expanded = ref<Account[]>([]);

const sort = ref<DataTableSortData<Account>>({
  column: 'usdValue',
  direction: 'desc' as const,
});

const isEth = computed<boolean>(() => get(blockchain) === Blockchain.ETH);
const isEth2 = computed<boolean>(() => get(blockchain) === Blockchain.ETH2);
const isBtcNetwork = computed<boolean>(() => isBtcChain(get(blockchain)));

const hasTokenDetection = computed<boolean>(() => supportsTransactions(get(blockchain)));

const rows = computed<Account[]>(() =>
  get(balances)
    .filter(({ groupHeader, tags }) => {
      const selectedTags = get(visibleTags);
      return !groupHeader && selectedTags.every(tag => tags?.includes(tag));
    })
    .map((item) => {
      const address = getAccountAddress(item);
      const display = get(addressNameSelector(address, item.chain)) || item.label || '';

      const group = item.groupId === address ? '' : item.groupId;

      const row = {
        ...item,
        display,
        groupId: group,
        identifier: getAccountId(item),
      };

      if (!get(hasTokenDetection))
        return row;

      const { amount, usdValue } = row;

      const { total } = get(getEthDetectedTokensInfo(blockchain, address));

      const rowWithTokens = {
        ...row,
        numOfDetectedTokens: total,
      };

      if (!get(isEth) || get(loopring))
        return rowWithTokens;

      const loopringBalances = getAddressBalances('loopring', address);

      if (isEmpty(loopringBalances.assets))
        return rowWithTokens;

      const loopringEth = loopringBalances.assets[Blockchain.ETH.toUpperCase()]?.amount ?? Zero;

      const loopringValue = bigNumberSum(Object.values(loopringBalances.assets).map(x => x.usdValue));

      return {
        ...rowWithTokens,
        usdValue: usdValue.plus(loopringValue),
        amount: amount.plus(loopringEth),
      };
    }),
);

const emptyGroups = computed<Account[]>(() => {
  const data = get(balances);
  const groupIds = data
    .filter(item => !item.groupHeader)
    .map(item => item.groupId)
    .filter(uniqueStrings);
  return data
    .filter(item => item.groupHeader && !groupIds.includes(item.groupId))
    .map(item => ({
      ...item,
      identifier: getAccountId(item),
    }));
});

const total = computed<Balance>(() => {
  const rowsVal = get(rows);
  const amount = bigNumberSum(rowsVal.map(({ amount }) => amount));
  const usdValue = balanceUsdValueSum(rowsVal);

  return {
    amount,
    usdValue,
  };
});

const asset = computed<string>(() => {
  const chain = get(blockchain);
  const nativeAsset = getNativeAsset(chain);
  if (get(isEth2))
    return Blockchain.ETH.toUpperCase();

  if (nativeAsset === chain)
    return chain.toUpperCase();

  return get(assetSymbol(nativeAsset));
});

const tableHeaders = computed<DataTableColumn<Account>[]>(() => {
  const currency = { symbol: get(currencySymbol) };

  const currencyHeader = get(hasTokenDetection)
    ? t('account_balances.headers.usd_value_eth', currency)
    : t('account_balances.headers.usd_value', currency);

  const accountHeader = get(isEth2) ? t('account_balances.headers.validator') : t('common.account');

  const headers: DataTableColumn<Account>[] = [
    {
      label: accountHeader,
      key: 'display',
      cellClass: 'py-0',
      sortable: true,
    },
    {
      label: get(asset).toUpperCase(),
      key: 'amount',
      sortable: true,
      cellClass: 'py-0',
      align: 'end',
    },
    {
      label: currencyHeader.toString(),
      key: 'usdValue',
      sortable: true,
      cellClass: 'py-0',
      align: 'end',
    },
  ];

  if (get(isEth2)) {
    headers.push({
      label: t('account_balances.headers.ownership'),
      key: 'ownershipPercentage',
      align: 'end',
      cellClass: 'py-0',
      sortable: true,
    });
  }

  if (!get(loopring)) {
    if (get(hasTokenDetection)) {
      headers.push({
        label: t('account_balances.headers.num_of_detected_tokens'),
        key: 'numOfDetectedTokens',
        cellClass: 'py-0',
        sortable: true,
        align: 'end',
      });
    }

    headers.push({
      label: t('common.actions_text'),
      key: 'actions',
      cellClass: '!p-0',
      align: 'start',
    });
  }

  return headers;
});

const accountOperation = logicOr(isTaskRunning(TaskType.ADD_ACCOUNT), isTaskRunning(TaskType.REMOVE_ACCOUNT), loading);

const isAnyLoading = logicOr(accountOperation, detectingTokens);

function editClick(account: BlockchainAccountWithBalance) {
  emit('edit-click', account);
}

function getItems(groupId?: string) {
  return get(balances).filter(account => account.groupId === groupId);
}

function isExpanded(row: Account) {
  return get(expanded).some(expanded => getAccountId(expanded) === getAccountId(row));
}

function expand(row: Account) {
  set(expanded, isExpanded(row) ? [] : [row]);
}
</script>

<template>
  <RuiDataTable
    v-model="selected"
    v-bind="rootAttrs"
    v-model:expanded="expanded"
    v-model:sort="sort"
    :cols="tableHeaders"
    :rows="rows"
    :loading="isAnyLoading"
    row-attr="identifier"
    :empty="{ description: t('data_table.no_data') }"
    :loading-text="t('account_balances.data_table.loading')"
    class="account-balances-list"
    data-cy="account-table"
    :data-location="blockchain"
    :group="isBtcNetwork ? ['groupId'] : undefined"
    single-expand
    outlined
    dense
    sticky-header
  >
    <template #item.display="{ row }">
      <div class="py-2 account-balance-table__account">
        <LabeledAddressDisplay :account="row" />
        <TagDisplay
          :tags="row.tags"
          small
        />
      </div>
    </template>
    <template #item.amount="{ row }">
      <AmountDisplay
        :value="row.amount"
        :loading="loading"
      />
    </template>
    <template #item.usdValue="{ row }">
      <AmountDisplay
        fiat-currency="USD"
        :value="row.usdValue"
        show-currency="symbol"
        :loading="loading"
      />
    </template>
    <template
      v-if="isEth2"
      #item.ownershipPercentage="{ row }"
    >
      <PercentageDisplay
        v-if="'ownershipPercentage' in row.data"
        :value="row.data.ownershipPercentage ?? '100'"
      />
    </template>
    <template
      v-if="hasTokenDetection && !loopring"
      #item.numOfDetectedTokens="{ row }"
    >
      <TokenDetection
        v-if="supportsTransactions(blockchain)"
        :address="getAccountAddress(row)"
        :loading="loading"
        :chain="blockchain"
      />
    </template>
    <template
      v-if="!loopring"
      #item.actions="{ row }"
    >
      <RowActions
        class="account-balance-table__actions"
        no-delete
        :edit-tooltip="t('account_balances.edit_tooltip')"
        :disabled="accountOperation"
        @edit-click="editClick(row)"
      />
    </template>
    <template
      v-if="balances.length > 0"
      #body.append
    >
      <RowAppend
        :label="t('common.total')"
        :left-patch-colspan="1"
        :right-patch-colspan="3"
        :is-mobile="false"
        class-name="[&>td]:p-4 text-sm"
      >
        <template #custom-columns>
          <td class="text-end">
            <AmountDisplay
              :loading="loading"
              :value="total.amount"
              :asset="blockchain"
            />
          </td>
          <td class="text-end">
            <AmountDisplay
              :loading="loading"
              fiat-currency="USD"
              show-currency="symbol"
              :value="total.usdValue"
            />
          </td>
        </template>
      </RowAppend>
    </template>
    <template
      v-if="!isBtcNetwork"
      #expanded-item="{ row }"
    >
      <AccountBalanceDetails
        :chain="blockchain"
        :loopring="loopring"
        :address="getAccountAddress(row)"
      />
    </template>
    <template
      v-if="!isBtcNetwork"
      #item.expand="{ row }"
    >
      <RuiTableRowExpander
        v-if="row.expandable || loopring"
        :expanded="isExpanded(row)"
        @click="expand(row)"
      />
    </template>
    <template #group.header="{ header, isOpen, toggle }">
      <AccountGroupHeader
        :group="header.identifier"
        :items="getItems(header.group?.groupId)"
        :expanded="isOpen"
        :loading="loading"
        @expand="toggle()"
        @delete="emit('delete-xpub', $event)"
        @edit="editClick($event)"
      />
    </template>
    <template
      v-if="emptyGroups.length > 0"
      #body.prepend
    >
      <tr
        v-for="group in emptyGroups"
        :key="group.identifier"
      >
        <AccountGroupHeader
          :group="group.identifier"
          :items="[group]"
          :expanded="false"
          :loading="loading"
          @delete="emit('delete-xpub', $event)"
          @edit="editClick($event)"
        />
      </tr>
    </template>
    <template
      v-else-if="isEth2"
      #body.prepend="{ colspan }"
    >
      <Eth2ValidatorLimitRow :colspan="colspan" />
    </template>
  </RuiDataTable>
</template>
