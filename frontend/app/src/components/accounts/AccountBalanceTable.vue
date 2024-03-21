<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { some } from 'lodash-es';
import { isBtcChain } from '@/types/blockchain/chains';
import { TaskType } from '@/types/task-type';
import { Section } from '@/types/status';
import type {
  BlockchainAccountWithBalance,
  XpubAccountWithBalance,
  XpubPayload,
} from '@/types/blockchain/accounts';
import type { ComputedRef, Ref } from 'vue';
import type {
  DataTableColumn,
  DataTableSortData,
} from '@rotki/ui-library-compat';
import type { Balance } from '@rotki/common';

const props = withDefaults(
  defineProps<{
    balances: BlockchainAccountWithBalance[];
    blockchain: string;
    visibleTags: string[];
    selected: string[];
    loopring?: boolean;
  }>(),
  {
    loopring: false,
  },
);

const emit = defineEmits<{
  (e: 'edit-click', account: BlockchainAccountWithBalance): void;
  (e: 'delete-xpub', payload: XpubPayload): void;
  (e: 'update:selected', selected: string[]): void;
}>();

const { t } = useI18n();

type IndexedBlockchainAccountWithBalance = BlockchainAccountWithBalance & {
  index?: number;
};

const { balances, blockchain, visibleTags, selected, loopring } = toRefs(props);

const rootAttrs = useAttrs();

const { isTaskRunning } = useTaskStore();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { hasDetails, getLoopringBalances } = useAccountDetails(blockchain);
const { getEthDetectedTokensInfo, detectingTokens }
  = useTokenDetection(blockchain);
const { getNativeAsset, supportsTransactions } = useSupportedChains();
const { assetSymbol } = useAssetInfoRetrieval();
const { addressNameSelector } = useAddressesNamesStore();

const { isLoading } = useStatusStore();
const loading = computed<boolean>(() => {
  if (get(loopring))
    return get(isLoading(Section.L2_LOOPRING_BALANCES));
  return get(isLoading(Section.BLOCKCHAIN, get(blockchain)));
});

const expanded: Ref<BlockchainAccountWithBalance[]> = ref([]);
const collapsedXpubs: Ref<XpubAccountWithBalance[]> = ref([]);

const sort: Ref<DataTableSortData> = ref({
  column: 'usdValue',
  direction: 'desc' as const,
});

const isEth = computed<boolean>(() => get(blockchain) === Blockchain.ETH);
const isEth2 = computed<boolean>(() => get(blockchain) === Blockchain.ETH2);
const isBtcNetwork = computed<boolean>(() => isBtcChain(get(blockchain)));

const hasTokenDetection: ComputedRef<boolean> = computed(() =>
  supportsTransactions(get(blockchain)),
);

const collapsedKeys = computed<string[]>(() =>
  get(collapsedXpubs).map(
    ({ derivationPath, xpub }) => `${xpub}::${derivationPath}`,
  ),
);

const rows = computed<IndexedBlockchainAccountWithBalance[]>(() =>
  get(balances)
    .filter(({ address, tags }) => {
      const selectedTags = get(visibleTags);

      return !!address && selectedTags.every(tag => tags.includes(tag));
    })
    .map((item, index) => {
      const display = get(addressNameSelector(item.address, item.chain)) || item.label || item.address;

      const row = {
        ...item,
        ...item.balance,
        display,
        index,
      };

      if (!get(hasTokenDetection))
        return row;

      const { address, balance: chainBalance } = row;

      const { total } = get(getEthDetectedTokensInfo(blockchain, address));

      const rowWithTokens = {
        ...row,
        numOfDetectedTokens: total,
      };

      if (!get(isEth))
        return rowWithTokens;

      const loopringBalances = get(getLoopringBalances(address));

      if (loopringBalances.length === 0)
        return rowWithTokens;

      const loopringEth
        = loopringBalances.find(
          ({ asset }) => asset === Blockchain.ETH.toUpperCase(),
        )?.amount ?? Zero;

      const amount = chainBalance.amount.plus(loopringEth);

      const usdValue = bigNumberSum(
        loopringBalances.map(({ usdValue }) => usdValue),
      ).plus(chainBalance.usdValue);

      return {
        ...rowWithTokens,
        balance: { usdValue, amount },
        usdValue,
        amount,
      };
    }),
);

const nonExpandedBalances = computed<BlockchainAccountWithBalance[]>(() =>
  get(rows)
    .filter(
      balance =>
        !('xpub' in balance)
        || ('xpub' in balance
        && !get(collapsedKeys).includes(
            `${balance.xpub}::${balance.derivationPath}`,
        )),
    )
    .concat(
      get(collapsedXpubs).map(({ derivationPath, xpub }) => {
        const xpubEntry = get(balances).find(
          balance =>
            !balance.address
            && 'xpub' in balance
            && balance.xpub === xpub
            && balance.derivationPath === derivationPath,
        );
        return (
          xpubEntry ?? {
            xpub,
            derivationPath,
            address: '',
            label: '',
            tags: [],
            balance: zeroBalance(),
            chain: get(blockchain),
          }
        );
      }),
    ),
);

const collapsedXpubBalances = computed<Balance>(() => {
  const balance = zeroBalance();

  return get(collapsedXpubs)
    .filter(({ tags }) => get(visibleTags).every(tag => tags.includes(tag)))
    .reduce(
      (previousValue, currentValue) =>
        balanceSum(previousValue, currentValue.balance),
      balance,
    );
});

const total = computed<Balance>(() => {
  const balances = get(nonExpandedBalances);
  const collapsedAmount = get(collapsedXpubBalances).amount;
  const collapsedUsd = get(collapsedXpubBalances).usdValue;
  const amount = bigNumberSum(
    balances.map(({ balance }) => balance.amount),
  ).plus(collapsedAmount);
  const usdValue = bigNumberSum(
    balances.map(({ balance }) => balance.usdValue),
  ).plus(collapsedUsd);

  return {
    amount,
    usdValue,
  };
});

const asset: ComputedRef<string> = computed(() => {
  const chain = get(blockchain);
  const nativeAsset = getNativeAsset(chain);
  if (get(isEth2))
    return Blockchain.ETH.toUpperCase();

  if (nativeAsset === chain)
    return chain.toUpperCase();

  return get(assetSymbol(nativeAsset));
});

const tableHeaders = computed<DataTableColumn[]>(() => {
  const currency = { symbol: get(currencySymbol) };

  const currencyHeader = get(hasTokenDetection)
    ? t('account_balances.headers.usd_value_eth', currency)
    : t('account_balances.headers.usd_value', currency);

  const accountHeader = get(isEth2)
    ? t('account_balances.headers.validator')
    : t('common.account');

  const headers: DataTableColumn[] = [
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

const accountOperation = logicOr(
  isTaskRunning(TaskType.ADD_ACCOUNT),
  isTaskRunning(TaskType.REMOVE_ACCOUNT),
  loading,
);

const isAnyLoading = logicOr(accountOperation, detectingTokens);

function editClick(account: BlockchainAccountWithBalance) {
  emit('edit-click', account);
}

function deleteXpub(payload: XpubPayload) {
  const chain = get(blockchain);
  assert(chain === Blockchain.BTC || chain === Blockchain.BCH);
  emit('delete-xpub', {
    ...payload,
    blockchain: chain,
  });
}

function addressesSelected(selected: string[]) {
  emit('update:selected', selected);
}

function getItems(xpub: string, derivationPath?: string) {
  const isXpub = (
    value: BlockchainAccountWithBalance,
  ): value is XpubAccountWithBalance =>
    'xpub' in value
    && xpub === value.xpub
    && derivationPath === value.derivationPath;

  return get(balances).filter(isXpub);
}

function removeCollapsed({ derivationPath, xpub }: XpubPayload) {
  const index = get(collapsedXpubs).findIndex(
    row => row.derivationPath === derivationPath && row.xpub === xpub,
  );

  if (index >= 0)
    get(collapsedXpubs).splice(index, 1);
}

const isExpanded = (address: string) => some(get(expanded), { address });

function expand(item: BlockchainAccountWithBalance) {
  set(expanded, isExpanded(item.address) ? [] : [item]);
}

defineExpose({
  removeCollapsed,
});
</script>

<template>
  <RuiDataTable
    :value="selected"
    v-bind="rootAttrs"
    :cols="tableHeaders"
    :rows="rows"
    :loading="isAnyLoading"
    row-attr="address"
    :expanded.sync="expanded"
    :sort.sync="sort"
    :empty="{ description: t('data_table.no_data') }"
    :loading-text="t('account_balances.data_table.loading')"
    class="account-balances-list"
    data-cy="account-table"
    :data-location="blockchain"
    :group="isBtcNetwork ? ['xpub', 'derivationPath'] : undefined"
    :collapsed.sync="collapsedXpubs"
    single-expand
    outlined
    sticky-header
    v-on="
      // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
      $listeners
    "
    @input="addressesSelected($event ?? [])"
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
      <PercentageDisplay :value="row.ownershipPercentage ?? '100'" />
    </template>
    <template
      v-if="hasTokenDetection && !loopring"
      #item.numOfDetectedTokens="{ row }"
    >
      <TokenDetection
        :address="row.address"
        :loading="loading"
        :blockchain="blockchain"
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
        :blockchain="blockchain"
        :loopring="loopring"
        :address="row.address"
      />
    </template>
    <template
      v-if="!isBtcNetwork"
      #item.expand="{ row }"
    >
      <RuiTableRowExpander
        v-if="hasTokenDetection && (hasDetails(row.address) || loopring)"
        :expanded="isExpanded(row.address)"
        @click="expand(row)"
      />
    </template>
    <template #group.header="{ header, isOpen, toggle }">
      <AccountGroupHeader
        :group="header.identifier"
        :items="getItems(header.group.xpub, header.group.derivationPath)"
        :expanded="isOpen"
        :loading="loading"
        @expand-clicked="toggle()"
        @delete-clicked="deleteXpub($event)"
        @edit-clicked="editClick($event)"
      />
    </template>
    <template
      v-if="isEth2"
      #body.prepend="{ colspan }"
    >
      <Eth2ValidatorLimitRow :colspan="colspan" />
    </template>
  </RuiDataTable>
</template>
