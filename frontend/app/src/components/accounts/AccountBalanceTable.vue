<template>
  <v-sheet rounded outlined>
    <data-table
      v-bind="$attrs"
      :headers="headers"
      :items="visibleBalances"
      :loading="accountOperation || refreshing"
      :loading-text="$t('account_balances.data_table.loading')"
      single-expand
      item-key="address"
      :expanded.sync="expanded"
      sort-by="balance.usdValue"
      :custom-group="groupBy"
      :group-by="isBtc ? ['xpub', 'derivationPath'] : undefined"
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
          color="primary"
          :value="selected.includes(item.address)"
          @input="selectionChanged(item.address, $event)"
        />
      </template>
      <template v-if="blockchain === 'ETH'" #header.balance.usdValue>
        {{
          $t('account_balances.headers.usd_value_eth', {
            symbol: currency.ticker_symbol
          })
        }}
      </template>
      <template v-else #header.balance.usdValue>
        {{
          $t('account_balances.headers.usd_value', {
            symbol: currency.ticker_symbol
          })
        }}
      </template>
      <template #item.label="{ item }">
        <v-row class="pt-3 pb-2">
          <v-col cols="12" class="account-balance-table__account">
            <labeled-address-display :account="item" />
            <span class="mt-2 flex-row d-flex align-center">
              <span v-if="loopringBalances(item.address).length > 0">
                <v-tooltip open-delay="400" top>
                  <template #activator="{ on, attrs }">
                    <v-chip
                      label
                      v-bind="attrs"
                      class="account-balance-table__tag"
                      v-on="on"
                    >
                      <v-img
                        contain
                        height="20px"
                        width="20px"
                        :src="require('@/assets/images/modules/loopring.svg')"
                      />
                    </v-chip>
                  </template>
                  <span>
                    {{ $t('account_balance_table.loopring_tooltip') }}
                  </span>
                </v-tooltip>
              </span>
              <span v-if="item.tags.length > 0">
                <tag-icon
                  v-for="tag in item.tags"
                  :key="tag"
                  class="account-balance-table__tag"
                  :tag="tags[tag]"
                />
              </span>
            </span>
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
      <template #item.actions="{ item }">
        <row-actions
          class="account-balance-table__actions"
          :no-delete="true"
          :edit-tooltip="$t('account_balances.edit_tooltip')"
          :disabled="accountOperation || refreshing"
          @edit-click="editClick(item)"
        />
      </template>
      <template v-if="balances.length > 0" #body.append>
        <tr class="account-balance-table__total">
          <td :class="mobileClass" />
          <td :class="mobileClass">{{ $t('account_balances.total') }}</td>
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
        </tr>
      </template>
      <template #expanded-item="{ headers, item }">
        <table-expand-container visible :colspan="headers.length">
          <account-asset-balances
            :title="$t('account_balance_table.assets')"
            :assets="accountAssets(item.address)"
          />
          <account-asset-balances
            v-if="accountLiabilities(item.address).length > 0"
            :title="$t('account_balance_table.liabilities')"
            :assets="accountLiabilities(item.address)"
          />
          <account-asset-balances
            v-if="
              blockchain === 'ETH' && loopringBalances(item.address).length > 0
            "
            :title="$t('account_balance_table.loopring')"
            :assets="loopringBalances(item.address)"
          />
        </table-expand-container>
      </template>
      <template #item.expand="{ item }">
        <row-expander
          v-if="expandable && hasDetails(item.address)"
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
    </data-table>
  </v-sheet>
</template>

<script lang="ts">
import isEqual from 'lodash/isEqual';
import sortBy from 'lodash/sortBy';
import { Component, Emit, Mixins, Prop } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapGetters, mapState } from 'vuex';

import AccountGroupHeader from '@/components/accounts/AccountGroupHeader.vue';
import LabeledAddressDisplay from '@/components/display/LabeledAddressDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import RowActions from '@/components/helper/RowActions.vue';
import RowExpander from '@/components/helper/RowExpander.vue';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import AccountAssetBalances from '@/components/settings/AccountAssetBalances.vue';
import TagIcon from '@/components/tags/TagIcon.vue';
import { CURRENCY_USD } from '@/data/currencies';
import { balanceSum } from '@/filters';
import StatusMixin from '@/mixins/status-mixin';
import { Currency } from '@/model/currency';
import { TaskType } from '@/model/task-type';
import { Balance } from '@/services/types-api';
import { chainSection } from '@/store/balances/const';
import {
  AssetBalance,
  BlockchainAccountWithBalance,
  XpubAccountWithBalance,
  XpubPayload
} from '@/store/balances/types';
import { Properties } from '@/types';
import { Blockchain, BTC, ETH, Tags } from '@/typing/types';
import { Zero } from '@/utils/bignumbers';

@Component({
  components: {
    DataTable,
    TableExpandContainer,
    LabeledAddressDisplay,
    TagIcon,
    RowActions,
    AccountGroupHeader,
    RowExpander,
    AccountAssetBalances
  },
  computed: {
    ...mapGetters('tasks', ['isTaskRunning']),
    ...mapGetters('session', ['currency']),
    ...mapGetters('balances', [
      'hasDetails',
      'accountAssets',
      'accountLiabilities',
      'loopringBalances'
    ]),
    ...mapState('session', ['tags'])
  }
})
export default class AccountBalanceTable extends Mixins(StatusMixin) {
  @Prop({ required: true })
  balances!: BlockchainAccountWithBalance[];
  @Prop({ required: true })
  blockchain!: Blockchain;
  @Prop({ required: true, type: Array })
  visibleTags!: string[];
  @Prop({ required: true, type: Array })
  selected!: string[];

  @Emit()
  editClick(_account: BlockchainAccountWithBalance) {}

  @Emit()
  deleteXpub(_payload: XpubPayload) {}

  @Emit()
  addressesSelected(_selected: string[]) {}

  section = chainSection[this.blockchain];
  currency!: Currency;
  isTaskRunning!: (type: TaskType) => boolean;
  accountAssets!: (account: string) => AssetBalance[];
  accountLiabilities!: (account: string) => AssetBalance[];
  loopringBalances!: (account: string) => AssetBalance[];
  hasDetails!: (account: string) => boolean;
  tags!: Tags;

  expanded = [];

  collapsedXpubs: XpubAccountWithBalance[] = [];

  get total(): Balance {
    const balances = this.visibleBalances;
    const collapsedAmount = this.collapsedXpubBalances.amount;
    const collapsedUsd = this.collapsedXpubBalances.usdValue;
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
  }

  get collapsedXpubBalances(): Balance {
    const balance: Balance = {
      amount: Zero,
      usdValue: Zero
    };

    return this.collapsedXpubs
      .filter(({ tags }) => this.visibleTags.every(tag => tags.includes(tag)))
      .reduce(
        (previousValue, currentValue) => ({
          amount: previousValue.amount.plus(currentValue.balance.amount),
          usdValue: previousValue.usdValue.plus(currentValue.balance.usdValue)
        }),
        balance
      );
  }

  get mobileClass(): string | null {
    return this.$vuetify.breakpoint.xsOnly ? 'v-data-table__mobile-row' : null;
  }

  setSelected(selected: boolean) {
    const selection = [...this.selected];
    if (!selected) {
      const total = selection.length;
      for (let i = 0; i < total; i++) {
        selection.pop();
      }
    } else {
      for (const { address } of this.visibleBalances) {
        if (!address || selection.includes(address)) {
          continue;
        }
        selection.push(address);
      }
    }

    this.addressesSelected(selection);
  }

  selectionChanged(address: string, selected: boolean) {
    const selection = [...this.selected];
    if (!selected) {
      const index = selection.indexOf(address);
      if (index >= 0) {
        selection.splice(index, 1);
      }
    } else if (address && !selection.includes(address)) {
      selection.push(address);
    }
    this.addressesSelected(selection);
  }

  get allSelected(): boolean {
    const strings = this.visibleBalances.map(value => value.address);
    return (
      strings.length > 0 && isEqual(sortBy(strings), sortBy(this.selected))
    );
  }

  get collapsedKeys(): string[] {
    return this.collapsedXpubs.map(
      ({ derivationPath, xpub }) => `${xpub}::${derivationPath}`
    );
  }

  expandXpub(
    isOpen: boolean,
    toggle: () => void,
    xpub: XpubAccountWithBalance
  ) {
    toggle();
    if (isOpen) {
      this.collapsedXpubs.push(xpub);
    } else {
      const index = this.collapsedXpubs.findIndex(
        key =>
          key.xpub === xpub.xpub && key.derivationPath === xpub.derivationPath
      );

      this.collapsedXpubs.splice(index, 1);
    }
  }

  groupBy(
    items: BlockchainAccountWithBalance[],
    groupBy: Properties<BlockchainAccountWithBalance, any>[]
  ) {
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
  }

  get headers(): DataTableHeader[] {
    const headers: DataTableHeader[] = [
      { text: '', value: 'accountSelection', width: '34px', sortable: false },
      { text: this.$tc('account_balances.headers.account'), value: 'label' },
      { text: this.blockchain, value: 'balance.amount', align: 'end' },
      {
        text: this.$t('account_balances.headers.usd_value', {
          symbol: this.currency.ticker_symbol ?? CURRENCY_USD
        }).toString(),
        value: 'balance.usdValue',
        align: 'end'
      },
      {
        text: this.$tc('account_balances.headers.actions'),
        value: 'actions',
        align: 'center',
        sortable: false,
        width: '28'
      }
    ];

    if (this.blockchain !== BTC) {
      headers.push({
        text: '',
        value: 'expand',
        align: 'end',
        sortable: false
      } as DataTableHeader);
    }
    return headers;
  }

  getItems(xpub: string, derivationPath?: string) {
    return this.balances.filter(
      value =>
        'xpub' in value &&
        xpub === value.xpub &&
        derivationPath === value?.derivationPath
    );
  }

  get accountOperation(): boolean {
    return (
      this.isTaskRunning(TaskType.ADD_ACCOUNT) ||
      this.isTaskRunning(TaskType.REMOVE_ACCOUNT)
    );
  }

  get nonExpandedBalances(): BlockchainAccountWithBalance[] {
    return this.balances
      .filter(balance => {
        return (
          !('xpub' in balance) ||
          ('xpub' in balance &&
            !this.collapsedKeys.includes(
              `${balance.xpub}::${balance.derivationPath}`
            ))
        );
      })
      .concat(
        this.collapsedXpubs.map(({ derivationPath, xpub }) => {
          const xpubEntry = this.balances.find(
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
              chain: BTC
            }
          );
        })
      );
  }

  private withL2(
    balances: BlockchainAccountWithBalance[]
  ): BlockchainAccountWithBalance[] {
    if (this.blockchain !== ETH) {
      return balances;
    }

    return balances.map(value => {
      const address = value.address;
      const assetBalances = this.loopringBalances(address);
      if (assetBalances.length === 0) {
        return value;
      }
      const chainBalance = value.balance;
      const loopringEth =
        assetBalances.find(({ asset }) => asset === ETH)?.amount ?? Zero;
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
  }

  get visibleBalances(): BlockchainAccountWithBalance[] {
    if (this.visibleTags.length === 0) {
      return this.withL2(this.nonExpandedBalances);
    }

    return this.withL2(
      this.nonExpandedBalances.filter(({ tags }) =>
        this.visibleTags.every(tag => tags.includes(tag))
      )
    );
  }

  get isBtc(): boolean {
    return this.blockchain === BTC;
  }

  get expandable(): boolean {
    return this.blockchain === ETH;
  }

  removeCollapsed({ derivationPath, xpub }: XpubPayload) {
    const index = this.collapsedXpubs.findIndex(
      collapsed =>
        collapsed.derivationPath === derivationPath && collapsed.xpub === xpub
    );

    if (index >= 0) {
      this.collapsedXpubs.splice(index, 1);
    }
  }
}
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
