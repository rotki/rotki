<template>
  <v-sheet rounded outlined>
    <data-table
      v-bind="$attrs"
      :headers="tableHeaders"
      :items="visibleBalances"
      :loading="accountOperation || loading"
      :loading-text="$t('account_balances.data_table.loading')"
      single-expand
      item-key="address"
      :expanded.sync="expanded"
      sort-by="balance.usdValue"
      :custom-group="groupBy"
      class="account-balances-list"
      :group-by="isBtcNetwork ? ['xpub', 'derivationPath'] : undefined"
      v-on="$listeners"
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
      <template v-if="!loopring" #item.actions="{ item }">
        <row-actions
          class="account-balance-table__actions"
          :no-delete="true"
          :edit-tooltip="$t('account_balances.edit_tooltip')"
          :disabled="accountOperation || loading"
          @edit-click="editClick(item)"
        />
      </template>
      <template v-if="balances.length > 0" #body.append="{ isMobile }">
        <row-append
          :label="$t('account_balances.total')"
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
          <template v-if="!loopring">
            <account-asset-balances
              :title="$t('account_balance_table.assets')"
              :assets="get(accountAssets(item.address))"
            />
            <account-asset-balances
              v-if="get(accountLiabilities(item.address)).length > 0"
              :title="$t('account_balance_table.liabilities')"
              :assets="get(accountLiabilities(item.address))"
            />
          </template>
          <account-asset-balances
            v-if="isEth && get(loopringBalances(item.address)).length > 0"
            :title="loopring ? '' : $t('account_balance_table.loopring')"
            :assets="get(loopringBalances(item.address))"
          />
        </table-expand-container>
      </template>
      <template #item.expand="{ item }">
        <row-expander
          v-if="isEth && (get(hasDetails(item.address)) || loopring)"
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

<script lang="ts">
import { Balance } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  computed,
  defineComponent,
  PropType,
  ref,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import isEqual from 'lodash/isEqual';
import sortBy from 'lodash/sortBy';
import { DataTableHeader } from 'vuetify';
import AccountGroupHeader from '@/components/accounts/AccountGroupHeader.vue';
import Eth2ValidatorLimitRow from '@/components/accounts/blockchain/eth2/Eth2ValidatorLimitRow.vue';
import LabeledAddressDisplay from '@/components/display/LabeledAddressDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import RowActions from '@/components/helper/RowActions.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import RowExpander from '@/components/helper/RowExpander.vue';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import AccountAssetBalances from '@/components/settings/AccountAssetBalances.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import { setupGeneralBalances } from '@/composables/balances';
import { setupThemeCheck } from '@/composables/common';
import { setupGeneralSettings } from '@/composables/session';
import { balanceSum } from '@/filters';
import i18n from '@/i18n';
import { chainSection } from '@/store/balances/const';
import {
  BlockchainAccountWithBalance,
  XpubAccountWithBalance,
  XpubPayload
} from '@/store/balances/types';
import { Section } from '@/store/const';
import { useTasks } from '@/store/tasks';
import { getStatusUpdater } from '@/store/utils';
import { Properties } from '@/types';
import { TaskType } from '@/types/task-type';
import { Zero } from '@/utils/bignumbers';

export default defineComponent({
  name: 'AccountBalanceTable',
  components: {
    RowAppend,
    Eth2ValidatorLimitRow,
    DataTable,
    TableExpandContainer,
    LabeledAddressDisplay,
    TagDisplay,
    RowActions,
    AccountGroupHeader,
    RowExpander,
    AccountAssetBalances
  },
  props: {
    balances: {
      required: true,
      type: Array as PropType<BlockchainAccountWithBalance[]>
    },
    blockchain: { required: true, type: String as PropType<Blockchain> },
    visibleTags: { required: true, type: Array as PropType<string[]> },
    selected: { required: true, type: Array as PropType<string[]> },
    loopring: { required: false, type: Boolean, default: false }
  },
  emits: ['edit-click', 'delete-xpub', 'addresses-selected'],
  setup(props, { emit }) {
    const { balances, blockchain, visibleTags, selected, loopring } =
      toRefs(props);

    const { isTaskRunning } = useTasks();
    const { currencySymbol, treatEth2AsEth } = setupGeneralSettings();
    const { hasDetails, accountAssets, accountLiabilities, loopringBalances } =
      setupGeneralBalances();

    const editClick = (account: BlockchainAccountWithBalance) => {
      emit('edit-click', account);
    };

    const deleteXpub = (payload: XpubPayload) => {
      emit('delete-xpub', {
        ...payload,
        blockchain: get(blockchain)
      });
    };

    const addressesSelected = (selected: string[]) => {
      emit('addresses-selected', selected);
    };

    const { currentBreakpoint } = setupThemeCheck();
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
      return getStatusUpdater(get(section)).loading();
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
        return balances;
      }

      return balances.map(value => {
        const address = value.address;
        const assetBalances = get(loopringBalances(address));
        if (assetBalances.length === 0) {
          return value;
        }
        const chainBalance = value.balance;
        const loopringEth =
          assetBalances.find(({ asset }) => asset === Blockchain.ETH)?.amount ??
          Zero;

        return {
          ...value,
          balance: {
            usdValue: balanceSum(
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
                balance: { amount: Zero, usdValue: Zero },
                chain: get(blockchain)
              }
            );
          })
        );
    });

    const visibleBalances = computed<BlockchainAccountWithBalance[]>(() => {
      if (get(visibleTags).length === 0) {
        return withL2(get(nonExpandedBalances));
      }

      return withL2(
        get(nonExpandedBalances).filter(({ tags }) =>
          get(visibleTags).every(tag => tags.includes(tag))
        )
      );
    });

    const collapsedXpubBalances = computed<Balance>(() => {
      const balance: Balance = {
        amount: Zero,
        usdValue: Zero
      };

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
      const amount = balanceSum(
        balances.map(({ balance }) => balance.amount)
      ).plus(collapsedAmount);
      const usdValue = balanceSum(
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
      return (
        strings.length > 0 && isEqual(sortBy(strings), sortBy(get(selected)))
      );
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
        ? i18n.t('account_balances.headers.usd_value_eth', currency)
        : i18n.t('account_balances.headers.usd_value', currency);

      const accountHeader = get(isEth2)
        ? i18n.t('account_balances.headers.validator')
        : i18n.t('account_balances.headers.account');

      const headers: DataTableHeader[] = [
        { text: '', value: 'accountSelection', width: '34px', sortable: false },
        { text: accountHeader.toString(), value: 'label' },
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
          text: i18n.t('account_balances.headers.ownership').toString(),
          value: 'ownershipPercentage',
          align: 'end',
          width: '28'
        });
      }

      headers.push({
        text: i18n.tc('account_balances.headers.actions'),
        value: 'actions',
        align: 'center',
        sortable: false,
        width: '28'
      });

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
      return get(balances).filter(
        value =>
          'xpub' in value &&
          xpub === value.xpub &&
          derivationPath === value?.derivationPath
      );
    };

    const accountOperation = computed<boolean>(() => {
      return (
        get(isTaskRunning(TaskType.ADD_ACCOUNT)) ||
        get(isTaskRunning(TaskType.REMOVE_ACCOUNT))
      );
    });

    const removeCollapsed = ({ derivationPath, xpub }: XpubPayload) => {
      const index = get(collapsedXpubs).findIndex(
        collapsed =>
          collapsed.derivationPath === derivationPath && collapsed.xpub === xpub
      );

      if (index >= 0) {
        collapsedXpubs.value.splice(index, 1);
      }
    };

    return {
      mobileClass,
      tableHeaders,
      isEth2,
      isEth,
      isBtcNetwork,
      visibleBalances,
      accountOperation,
      loading,
      expanded,
      nonExpandedBalances,
      allSelected,
      total,
      accountAssets,
      accountLiabilities,
      loopringBalances,
      hasDetails,
      setSelected,
      groupBy,
      selectionChanged,
      editClick,
      getItems,
      expandXpub,
      deleteXpub,
      removeCollapsed,
      get
    };
  }
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
