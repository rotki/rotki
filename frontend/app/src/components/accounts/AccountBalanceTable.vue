<template>
  <v-sheet rounded outlined>
    <data-table
      v-bind="rootAttrs"
      :headers="tableHeaders"
      :items="visibleBalances"
      :loading="accountOperation || loading || detectingTokens(null).value"
      :loading-text="tc('account_balances.data_table.loading')"
      single-expand
      item-key="index"
      :expanded.sync="expanded"
      sort-by="balance.usdValue"
      :custom-group="groupBy"
      class="account-balances-list"
      :group-by="isBtcNetwork ? ['xpub', 'derivationPath'] : undefined"
      v-on="rootListeners"
    >
      <template #header.accountSelection>
        <v-simple-checkbox
          :disabled="nonExpandedBalances.length === 0"
          :ripple="false"
          :value="allSelected"
          color="primary"
          @input="setSelected($event)"
        />
      </template>
      <template #item.accountSelection="{ item }">
        <v-simple-checkbox
          :ripple="false"
          data-cy="account-balances-item-checkbox"
          color="primary"
          :value="selected.includes(item.address)"
          @input="selectionChanged(item.address, $event)"
        />
      </template>
      <template #item.label="{ item }">
        <v-row class="pt-3 pb-2">
          <v-col cols="12" class="account-balance-table__account">
            <labeled-address-display :account="item" />
            <tag-display :tags="item.tags" />
          </v-col>
        </v-row>
      </template>
      <template #item.balance.amount="{ item }">
        <amount-display :value="item.balance.amount" :loading="loading" />
      </template>
      <template #item.balance.usdValue="{ item }">
        <amount-display
          fiat-currency="USD"
          :value="item.balance.usdValue"
          show-currency="symbol"
          :loading="loading"
        />
      </template>
      <template v-if="isEth2" #item.ownershipPercentage="{ item }">
        <percentage-display :value="item.ownershipPercentage" />
      </template>
      <template v-if="isEth && !loopring" #item.numOfDetectedTokens="{ item }">
        <div class="d-flex align-center justify-end">
          <div class="mr-2">
            {{ getEthDetectedTokensInfo(item.address).value.total }}
          </div>
          <div>
            <v-tooltip top>
              <template #activator="{ on }">
                <v-btn
                  text
                  icon
                  :disabled="detectingTokens(item.address).value || loading"
                  v-on="on"
                  @click="fetchDetectedTokensAndQueryBalance(item.address)"
                >
                  <v-progress-circular
                    v-if="detectingTokens(item.address).value"
                    indeterminate
                    color="primary"
                    width="2"
                    size="20"
                  />
                  <v-icon v-else small>mdi-refresh</v-icon>
                </v-btn>
              </template>
              <div class="text-center">
                <div>
                  {{ tc('account_balances.detect_tokens.tooltip.redetect') }}
                </div>
                <div
                  v-if="getEthDetectedTokensInfo(item.address).value.timestamp"
                >
                  <i18n
                    path="account_balances.detect_tokens.tooltip.last_detected"
                  >
                    <template #time>
                      <date-display
                        :timestamp="
                          getEthDetectedTokensInfo(item.address).value.timestamp
                        "
                      />
                    </template>
                  </i18n>
                </div>
              </div>
            </v-tooltip>
          </div>
        </div>
      </template>
      <template v-if="!loopring" #item.actions="{ item }">
        <row-actions
          class="account-balance-table__actions"
          :no-delete="true"
          :edit-tooltip="tc('account_balances.edit_tooltip')"
          :disabled="accountOperation || loading"
          @edit-click="editClick(item)"
        />
      </template>
      <template v-if="balances.length > 0" #body.append="{ isMobile }">
        <row-append
          :label="tc('common.total')"
          :class-name="{ 'flex-column': isMobile }"
          :left-patch-colspan="1"
          :is-mobile="isMobile"
        >
          <template #custom-columns>
            <td class="text-end" :class="mobileClass">
              <amount-display
                :loading="loading"
                :value="total.amount"
                :asset="$vuetify.breakpoint.xsOnly ? blockchain : null"
              />
            </td>
            <td class="text-end" :class="mobileClass">
              <amount-display
                :loading="loading"
                fiat-currency="USD"
                show-currency="symbol"
                :value="total.usdValue"
              />
            </td>
          </template>
        </row-append>
      </template>
      <template #expanded-item="{ headers, item }">
        <table-expand-container visible :colspan="headers.length">
          <account-balance-details
            :loopring="loopring"
            :assets="assets(item.address)"
            :liabilities="liabilities(item.address)"
            :loopring-balances="loopringBalances(item.address)"
          />
        </table-expand-container>
      </template>
      <template #item.expand="{ item }">
        <row-expander
          v-if="isEth && (accountHasDetails(item.address).value || loopring)"
          :expanded="expanded.includes(item)"
          @click="expanded = expanded.includes(item) ? [] : [item]"
        />
      </template>
      <template #group.header="{ group, isOpen, toggle }">
        <account-group-header
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
        <eth2-validator-limit-row :colspan="headers.length" />
      </template>
    </data-table>
  </v-sheet>
</template>

<script setup lang="ts">
import { Balance } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import isEqual from 'lodash/isEqual';
import sortBy from 'lodash/sortBy';
import { PropType, useListeners } from 'vue';
import { DataTableHeader } from 'vuetify';
import AccountGroupHeader from '@/components/accounts/AccountGroupHeader.vue';
import AccountBalanceDetails from '@/components/accounts/balances/AccountBalanceDetails.vue';
import Eth2ValidatorLimitRow from '@/components/accounts/blockchain/eth2/Eth2ValidatorLimitRow.vue';
import LabeledAddressDisplay from '@/components/display/LabeledAddressDisplay.vue';
import RowActions from '@/components/helper/RowActions.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import RowExpander from '@/components/helper/RowExpander.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import { useTheme } from '@/composables/common';
import { useStatusUpdater } from '@/composables/status';
import { bigNumberSum } from '@/filters';
import {
  BlockchainAccountWithBalance,
  XpubAccountWithBalance,
  XpubPayload
} from '@/store/balances/types';
import { useBlockchainBalancesStore } from '@/store/blockchain/balances';
import { useEthBalancesStore } from '@/store/blockchain/balances/eth';
import { useBlockchainTokensStore } from '@/store/blockchain/tokens';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTasks } from '@/store/tasks';
import { Properties } from '@/types';
import { chainSection } from '@/types/blockchain';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { assert } from '@/utils/assertions';
import { Zero, zeroBalance } from '@/utils/bignumbers';

const props = defineProps({
  balances: {
    required: true,
    type: Array as PropType<BlockchainAccountWithBalance[]>
  },
  blockchain: { required: true, type: String as PropType<Blockchain> },
  visibleTags: { required: true, type: Array as PropType<string[]> },
  selected: { required: true, type: Array as PropType<string[]> },
  loopring: { required: false, type: Boolean, default: false }
});

const emit = defineEmits<{
  (e: 'edit-click', account: BlockchainAccountWithBalance): void;
  (e: 'delete-xpub', payload: XpubPayload): void;
  (e: 'addresses-selected', selected: string[]): void;
}>();

const { balances, blockchain, visibleTags, selected, loopring } = toRefs(props);

const rootAttrs = useAttrs();
const rootListeners = useListeners();

const { isTaskRunning } = useTasks();
const { currencySymbol, treatEth2AsEth } = storeToRefs(
  useGeneralSettingsStore()
);
const {
  accountHasDetails,
  accountAssets,
  accountLiabilities,
  getLoopringBalances
} = useEthBalancesStore();

const { tc } = useI18n();

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

const { currentBreakpoint } = useTheme();
const xsOnly = computed(() => get(currentBreakpoint).xsOnly);
const mobileClass = computed<string | null>(() => {
  return get(xsOnly) ? 'v-data-table__mobile-row' : null;
});

const section = computed<Section>(() => {
  return get(loopring)
    ? Section.L2_LOOPRING_BALANCES
    : chainSection[get(blockchain)];
});

const loading = computed<boolean>(() => {
  return useStatusUpdater(get(section)).loading();
});

const expanded = ref<BlockchainAccountWithBalance[]>([]);
const collapsedXpubs = ref<XpubAccountWithBalance[]>([]);

const isEth = computed<boolean>(() => get(blockchain) === Blockchain.ETH);
const isEth2 = computed<boolean>(() => get(blockchain) === Blockchain.ETH2);
const isBtcNetwork = computed<boolean>(() =>
  [Blockchain.BTC, Blockchain.BCH].includes(get(blockchain))
);

const withL2 = (
  balances: BlockchainAccountWithBalance[]
): BlockchainAccountWithBalance[] => {
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
      assetBalances.find(({ asset }) => asset === Blockchain.ETH)?.amount ??
      Zero;

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

const collapsedKeys = computed<string[]>(() => {
  return get(collapsedXpubs).map(
    ({ derivationPath, xpub }) => `${xpub}::${derivationPath}`
  );
});

const nonExpandedBalances = computed<BlockchainAccountWithBalance[]>(() => {
  return get(balances)
    .filter(balance => {
      return (
        !('xpub' in balance) ||
        ('xpub' in balance &&
          !get(collapsedKeys).includes(
            `${balance.xpub}::${balance.derivationPath}`
          ))
      );
    })
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
            xpub: xpub,
            derivationPath: derivationPath,
            address: '',
            label: '',
            tags: [],
            balance: zeroBalance(),
            chain: get(blockchain)
          }
        );
      })
    );
});

const visibleBalances = computed<BlockchainAccountWithBalance[]>(() => {
  const balances = get(nonExpandedBalances).map(item => {
    if (!get(isEth) || get(loopring)) return item;
    return {
      ...item,
      numOfDetectedTokens: get(getEthDetectedTokensInfo(item.address)).total
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
      (previousValue, currentValue) => ({
        amount: previousValue.amount.plus(currentValue.balance.amount),
        usdValue: previousValue.usdValue.plus(currentValue.balance.usdValue)
      }),
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
  const record = {} as Record<string, BlockchainAccountWithBalance[]>;

  for (let item of items) {
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

const tableHeaders = computed<DataTableHeader[]>(() => {
  const currency = { symbol: get(currencySymbol) };

  const currencyHeader = get(isEth)
    ? tc('account_balances.headers.usd_value_eth', 0, currency)
    : tc('account_balances.headers.usd_value', 0, currency);

  const accountHeader = get(isEth2)
    ? tc('account_balances.headers.validator')
    : tc('common.account');

  const headers: DataTableHeader[] = [
    { text: '', value: 'accountSelection', width: '34px', sortable: false },
    { text: accountHeader, value: 'label' },
    {
      text: get(isEth2) && get(treatEth2AsEth) ? 'ETH' : get(blockchain),
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
      text: tc('account_balances.headers.ownership'),
      value: 'ownershipPercentage',
      align: 'end',
      width: '28'
    });
  }

  if (get(isEth) && !get(loopring)) {
    headers.push({
      text: tc('account_balances.headers.num_of_detected_tokens'),
      value: 'numOfDetectedTokens',
      align: 'end'
    });
  }

  if (!get(loopring)) {
    headers.push({
      text: tc('account_balances.headers.actions'),
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

const accountOperation = computed<boolean>(() => {
  return (
    get(isTaskRunning(TaskType.ADD_ACCOUNT)) ||
    get(isTaskRunning(TaskType.REMOVE_ACCOUNT))
  );
});

const { getEthDetectedTokensInfo, fetchDetectedTokens } =
  useBlockchainTokensStore();
const { fetchBlockchainBalances } = useBlockchainBalancesStore();

const detectingTokens = (address: string | null = null) =>
  isTaskRunning(TaskType.FETCH_DETECTED_TOKENS, address ? { address } : {});

const detectingAllTokens = detectingTokens();

const fetchDetectedTokensAndQueryBalance = async (address: string) => {
  await fetchDetectedTokens(address);
  await fetchBlockchainBalances({
    blockchain: Blockchain.ETH,
    ignoreCache: true
  });
};

const fetchAllDetectedTokensAndQueryBalance = async () => {
  const promises = get(visibleBalances).map(async balance => {
    const address = balance.address;
    await fetchDetectedTokensAndQueryBalance(address);
  });

  await Promise.allSettled(promises);
};

const assets = (address: string) => {
  return get(accountAssets(address));
};

const liabilities = (address: string) => {
  return get(accountLiabilities(address));
};

const loopringBalances = (address: string) => get(getLoopringBalances(address));

const removeCollapsed = ({ derivationPath, xpub }: XpubPayload) => {
  const index = get(collapsedXpubs).findIndex(
    collapsed =>
      collapsed.derivationPath === derivationPath && collapsed.xpub === xpub
  );

  if (index >= 0) {
    get(collapsedXpubs).splice(index, 1);
  }
};

defineExpose({
  removeCollapsed,
  fetchAllDetectedTokensAndQueryBalance,
  detectingAllTokens
});
</script>

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
