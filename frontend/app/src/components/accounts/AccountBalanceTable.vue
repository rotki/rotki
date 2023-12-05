<script setup lang="ts">
import { type Balance } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { isEqual, some, sortBy } from 'lodash-es';
import { type ComputedRef, type Ref, useListeners } from 'vue';
import { type DataTableHeader } from '@/types/vuetify';
import { type Properties } from '@/types';
import { chainSection } from '@/types/blockchain';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import {
  type BlockchainAccountWithBalance,
  type XpubAccountWithBalance,
  type XpubPayload
} from '@/types/blockchain/accounts';

const props = withDefaults(
  defineProps<{
    balances: BlockchainAccountWithBalance[];
    blockchain: Blockchain;
    visibleTags: string[];
    selected: string[];
    loopring?: boolean;
  }>(),
  {
    loopring: false
  }
);

const emit = defineEmits<{
  (e: 'edit-click', account: BlockchainAccountWithBalance): void;
  (e: 'delete-xpub', payload: XpubPayload): void;
  (e: 'addresses-selected', selected: string[]): void;
}>();

const { t } = useI18n();

type IndexedBlockchainAccountWithBalance = BlockchainAccountWithBalance & {
  index?: number;
};

const { balances, blockchain, visibleTags, selected, loopring } = toRefs(props);

const rootAttrs = useAttrs();
const rootListeners = useListeners();

const { isTaskRunning } = useTaskStore();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { hasDetails, getLoopringBalances } = useAccountDetails(blockchain);
const { getEthDetectedTokensInfo, detectingTokens } =
  useTokenDetection(blockchain);
const { getNativeAsset, supportsTransactions } = useSupportedChains();
const { assetSymbol } = useAssetInfoRetrieval();

const editClick = (account: BlockchainAccountWithBalance) => {
  emit('edit-click', account);
};

const deleteXpub = (payload: XpubPayload) => {
  const chain = get(blockchain);
  assert(chain === Blockchain.BTC || chain === Blockchain.BCH);
  emit('delete-xpub', {
    ...payload,
    blockchain: chain
  });
};

const addressesSelected = (selected: string[]) => {
  emit('addresses-selected', selected);
};

const { xs } = useDisplay();

const mobileClass = computed<string | null>(() =>
  get(xs) ? 'v-data-table__mobile-row' : null
);

const section = computed<Section>(() =>
  get(loopring) ? Section.L2_LOOPRING_BALANCES : chainSection[get(blockchain)]
);

const { isLoading } = useStatusStore();
const loading = isLoading(get(section));

const expanded: Ref<BlockchainAccountWithBalance[]> = ref([]);
const collapsedXpubs: Ref<XpubAccountWithBalance[]> = ref([]);

const isEth = computed<boolean>(() => get(blockchain) === Blockchain.ETH);
const isEth2 = computed<boolean>(() => get(blockchain) === Blockchain.ETH2);
const isBtcNetwork = computed<boolean>(() =>
  [Blockchain.BTC, Blockchain.BCH].includes(get(blockchain))
);

const hasTokenDetection: ComputedRef<boolean> = computed(() =>
  supportsTransactions(get(blockchain))
);

const withL2 = (
  balances: BlockchainAccountWithBalance[]
): IndexedBlockchainAccountWithBalance[] => {
  if (!get(isEth) || get(loopring)) {
    return balances.map((balance, index) => ({ ...balance, index }));
  }

  return balances.map((value, index) => {
    const address = value.address;
    const assetBalances = get(getLoopringBalances(address));
    if (assetBalances.length === 0) {
      return { ...value, index };
    }
    const chainBalance = value.balance;
    const loopringEth =
      assetBalances.find(({ asset }) => asset === Blockchain.ETH.toUpperCase())
        ?.amount ?? Zero;

    return {
      ...value,
      index,
      balance: {
        usdValue: bigNumberSum(
          assetBalances.map(({ usdValue }) => usdValue)
        ).plus(chainBalance.usdValue),
        amount: chainBalance.amount.plus(loopringEth)
      }
    };
  });
};

const collapsedKeys = computed<string[]>(() =>
  get(collapsedXpubs).map(
    ({ derivationPath, xpub }) => `${xpub}::${derivationPath}`
  )
);

const nonExpandedBalances = computed<BlockchainAccountWithBalance[]>(() =>
  get(balances)
    .filter(
      balance =>
        !('xpub' in balance) ||
        ('xpub' in balance &&
          !get(collapsedKeys).includes(
            `${balance.xpub}::${balance.derivationPath}`
          ))
    )
    .concat(
      get(collapsedXpubs).map(({ derivationPath, xpub }) => {
        const xpubEntry = get(balances).find(
          balance =>
            !balance.address &&
            'xpub' in balance &&
            balance.xpub === xpub &&
            balance.derivationPath === derivationPath
        );
        return (
          xpubEntry ?? {
            xpub,
            derivationPath,
            address: '',
            label: '',
            tags: [],
            balance: zeroBalance(),
            chain: get(blockchain)
          }
        );
      })
    )
);

const visibleBalances = computed<BlockchainAccountWithBalance[]>(() => {
  const balances = get(nonExpandedBalances).map(item => {
    if (!get(hasTokenDetection) || get(loopring)) {
      return item;
    }
    const detected = get(getEthDetectedTokensInfo(blockchain, item.address));
    return {
      ...item,
      numOfDetectedTokens: detected.total
    };
  });

  const selectedTags = get(visibleTags);
  if (selectedTags.length === 0) {
    return withL2(balances);
  }

  return withL2(
    balances.filter(({ tags }) => selectedTags.every(tag => tags.includes(tag)))
  );
});

const collapsedXpubBalances = computed<Balance>(() => {
  const balance = zeroBalance();

  return get(collapsedXpubs)
    .filter(({ tags }) => get(visibleTags).every(tag => tags.includes(tag)))
    .reduce(
      (previousValue, currentValue) =>
        balanceSum(previousValue, currentValue.balance),
      balance
    );
});

const total = computed<Balance>(() => {
  const balances = get(visibleBalances);
  const collapsedAmount = get(collapsedXpubBalances).amount;
  const collapsedUsd = get(collapsedXpubBalances).usdValue;
  const amount = bigNumberSum(
    balances.map(({ balance }) => balance.amount)
  ).plus(collapsedAmount);
  const usdValue = bigNumberSum(
    balances.map(({ balance }) => balance.usdValue)
  ).plus(collapsedUsd);

  return {
    amount,
    usdValue
  };
});

const setSelected = (isSelected: boolean) => {
  const selection = [...get(selected)];
  if (!isSelected) {
    const total = selection.length;
    for (let i = 0; i < total; i++) {
      selection.pop();
    }
  } else {
    for (const { address } of get(visibleBalances)) {
      if (!address || selection.includes(address)) {
        continue;
      }
      selection.push(address);
    }
  }

  addressesSelected(selection);
};

const selectionChanged = (address: string, isSelected: boolean) => {
  const selection = [...get(selected)];
  if (!isSelected) {
    const index = selection.indexOf(address);
    if (index >= 0) {
      selection.splice(index, 1);
    }
  } else if (address && !selection.includes(address)) {
    selection.push(address);
  }
  addressesSelected(selection);
};

const allSelected = computed<boolean>(() => {
  const strings = get(visibleBalances).map(value => value.address);
  return strings.length > 0 && isEqual(sortBy(strings), sortBy(get(selected)));
});

const expandXpub = (
  isOpen: boolean,
  toggle: () => void,
  xpub: XpubAccountWithBalance
) => {
  toggle();
  if (isOpen) {
    collapsedXpubs.value.push(xpub);
  } else {
    const index = get(collapsedXpubs).findIndex(
      key =>
        key.xpub === xpub.xpub && key.derivationPath === xpub.derivationPath
    );

    get(collapsedXpubs).splice(index, 1);
  }
};

const groupBy = (
  items: BlockchainAccountWithBalance[],
  groupBy: Properties<BlockchainAccountWithBalance, any>[]
) => {
  const record: Record<string, BlockchainAccountWithBalance[]> = {};

  for (const item of items) {
    const key =
      'xpub' in item ? groupBy.map(value => item[value]).join(':') : '';
    if (record[key]) {
      if (!item.address) {
        continue;
      }
      record[key].push(item);
    } else {
      record[key] = !item.address ? [] : [item];
    }
  }

  return Object.keys(record).map(name => ({
    name,
    items: record[name]
  }));
};

const asset: ComputedRef<string> = computed(() => {
  const chain = get(blockchain);
  const nativeAsset = getNativeAsset(chain);
  if (get(isEth2)) {
    return Blockchain.ETH.toUpperCase();
  }
  if (nativeAsset === chain) {
    return chain.toUpperCase();
  }
  return get(assetSymbol(nativeAsset));
});

const tableHeaders = computed<DataTableHeader[]>(() => {
  const currency = { symbol: get(currencySymbol) };

  const currencyHeader = get(hasTokenDetection)
    ? t('account_balances.headers.usd_value_eth', currency)
    : t('account_balances.headers.usd_value', currency);

  const accountHeader = get(isEth2)
    ? t('account_balances.headers.validator')
    : t('common.account');

  const headers: DataTableHeader[] = [
    { text: '', value: 'accountSelection', width: '34px', sortable: false },
    { text: accountHeader, value: 'label', sortable: false },
    {
      text: get(asset).toUpperCase(),
      value: 'balance.amount',
      align: 'end'
    },
    {
      text: currencyHeader.toString(),
      value: 'balance.usdValue',
      align: 'end'
    }
  ];

  if (get(isEth2)) {
    headers.push({
      text: t('account_balances.headers.ownership'),
      value: 'ownershipPercentage',
      align: 'end',
      width: '28'
    });
  }

  if (get(hasTokenDetection) && !get(loopring)) {
    headers.push({
      text: t('account_balances.headers.num_of_detected_tokens'),
      value: 'numOfDetectedTokens',
      align: 'end'
    });
  }

  if (!get(loopring)) {
    headers.push({
      text: t('common.actions_text'),
      value: 'actions',
      align: 'center',
      sortable: false,
      width: '28'
    });
  }

  if (!get(isBtcNetwork)) {
    headers.push({
      text: '',
      value: 'expand',
      align: 'end',
      sortable: false
    });
  }

  return headers;
});

const getItems = (xpub: string, derivationPath?: string) => {
  const isXpub = (
    value: BlockchainAccountWithBalance
  ): value is XpubAccountWithBalance =>
    'xpub' in value &&
    xpub === value.xpub &&
    derivationPath === value?.derivationPath;

  return get(balances).filter(isXpub);
};

const accountOperation = computed<boolean>(
  () =>
    get(isTaskRunning(TaskType.ADD_ACCOUNT)) ||
    get(isTaskRunning(TaskType.REMOVE_ACCOUNT))
);

const removeCollapsed = ({ derivationPath, xpub }: XpubPayload) => {
  const index = get(collapsedXpubs).findIndex(
    collapsed =>
      collapsed.derivationPath === derivationPath && collapsed.xpub === xpub
  );

  if (index >= 0) {
    get(collapsedXpubs).splice(index, 1);
  }
};

const isExpanded = (address: string) => some(get(expanded), { address });

const expand = (item: BlockchainAccountWithBalance) => {
  set(expanded, isExpanded(item.address) ? [] : [item]);
};

defineExpose({
  removeCollapsed
});
</script>

<template>
  <DataTable
    v-bind="rootAttrs"
    :headers="tableHeaders"
    :items="visibleBalances"
    :loading="accountOperation || loading || detectingTokens"
    :loading-text="t('account_balances.data_table.loading')"
    single-expand
    item-key="address"
    :expanded.sync="expanded"
    sort-by="balance.usdValue"
    :custom-group="groupBy"
    class="account-balances-list"
    data-cy="account-table"
    :data-location="blockchain"
    :group-by="isBtcNetwork ? ['xpub', 'derivationPath'] : undefined"
    v-on="rootListeners"
  >
    <template #header.accountSelection>
      <VSimpleCheckbox
        :disabled="nonExpandedBalances.length === 0"
        :ripple="false"
        :value="allSelected"
        color="primary"
        @input="setSelected($event)"
      />
    </template>
    <template #item.accountSelection="{ item }">
      <VSimpleCheckbox
        :ripple="false"
        data-cy="account-balances-item-checkbox"
        color="primary"
        :value="selected.includes(item.address)"
        @input="selectionChanged(item.address, $event)"
      />
    </template>
    <template #item.label="{ item }">
      <div class="py-2 account-balance-table__account">
        <LabeledAddressDisplay :account="item" />
        <TagDisplay :tags="item.tags" />
      </div>
    </template>
    <template #item.balance.amount="{ item }">
      <AmountDisplay :value="item.balance.amount" :loading="loading" />
    </template>
    <template #item.balance.usdValue="{ item }">
      <AmountDisplay
        fiat-currency="USD"
        :value="item.balance.usdValue"
        show-currency="symbol"
        :loading="loading"
      />
    </template>
    <template v-if="isEth2" #item.ownershipPercentage="{ item }">
      <PercentageDisplay :value="item.ownershipPercentage" />
    </template>
    <template
      v-if="hasTokenDetection && !loopring"
      #item.numOfDetectedTokens="{ item }"
    >
      <TokenDetection
        :address="item.address"
        :loading="loading"
        :blockchain="blockchain"
      />
    </template>
    <template v-if="!loopring" #item.actions="{ item }">
      <RowActions
        class="account-balance-table__actions"
        :no-delete="true"
        :edit-tooltip="t('account_balances.edit_tooltip')"
        :disabled="accountOperation || loading"
        @edit-click="editClick(item)"
      />
    </template>
    <template v-if="balances.length > 0" #body.append="{ isMobile }">
      <RowAppend
        :label="t('common.total')"
        :class-name="{ 'flex-column': isMobile }"
        :left-patch-colspan="1"
        :right-patch-colspan="3"
        :is-mobile="isMobile"
      >
        <template #custom-columns>
          <td class="text-end" :class="mobileClass">
            <AmountDisplay
              :loading="loading"
              :value="total.amount"
              :asset="xs ? blockchain : undefined"
            />
          </td>
          <td class="text-end" :class="mobileClass">
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
    <template #expanded-item="{ headers, item }">
      <TableExpandContainer visible :colspan="headers.length">
        <AccountBalanceDetails
          :blockchain="blockchain"
          :loopring="loopring"
          :address="item.address"
        />
      </TableExpandContainer>
    </template>
    <template #item.expand="{ item }">
      <RowExpander
        v-if="hasTokenDetection && (hasDetails(item.address) || loopring)"
        :expanded="isExpanded(item.address)"
        @click="expand(item)"
      />
    </template>
    <template #group.header="{ group, isOpen, toggle }">
      <AccountGroupHeader
        :group="group ? group : ''"
        :items="getItems(group.split(':')[0], group.split(':')[1])"
        :expanded="isOpen"
        :loading="loading"
        @expand-clicked="expandXpub(isOpen, toggle, $event)"
        @delete-clicked="deleteXpub($event)"
        @edit-clicked="editClick($event)"
      />
    </template>
    <template v-if="isEth2" #body.prepend="{ headers }">
      <Eth2ValidatorLimitRow :colspan="headers.length" />
    </template>
  </DataTable>
</template>

<style scoped lang="scss">
.account-balance-table {
  &__account {
    display: flex;
    flex-direction: column;
  }

  &__total {
    font-weight: 500;
  }

  &__tag {
    margin-right: 8px;
    margin-bottom: 2px;
  }
}
</style>
