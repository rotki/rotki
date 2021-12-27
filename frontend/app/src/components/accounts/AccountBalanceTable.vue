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
      class="account-balances-list"
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
          <template v-if="!loopring">
            <account-asset-balances
              :title="$t('account_balance_table.assets')"
              :assets="accountAssets(item.address)"
            />
            <account-asset-balances
              v-if="accountLiabilities(item.address).length > 0"
              :title="$t('account_balance_table.liabilities')"
              :assets="accountLiabilities(item.address)"
            />
          </template>
          <account-asset-balances
            v-if="
              blockchain === 'ETH' && loopringBalances(item.address).length > 0
            "
            :title="loopring ? '' : $t('account_balance_table.loopring')"
            :assets="loopringBalances(item.address)"
          />
        </table-expand-container>
      </template>
      <template #item.expand="{ item }">
        <row-expander
          v-if="expandable && (hasDetails(item.address) || loopring)"
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
import { AssetBalance, Balance } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Ref } from '@vue/composition-api';
import isEqual from 'lodash/isEqual';
import sortBy from 'lodash/sortBy';
import { mapState as mapPiniaState } from 'pinia';
import { Component, Emit, Mixins, Prop } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapGetters } from 'vuex';
import AccountGroupHeader from '@/components/accounts/AccountGroupHeader.vue';
import Eth2ValidatorLimitRow from '@/components/accounts/blockchain/eth2/Eth2ValidatorLimitRow.vue';
import LabeledAddressDisplay from '@/components/display/LabeledAddressDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import RowActions from '@/components/helper/RowActions.vue';
import RowExpander from '@/components/helper/RowExpander.vue';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import AccountAssetBalances from '@/components/settings/AccountAssetBalances.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import { balanceSum } from '@/filters';
import StatusMixin from '@/mixins/status-mixin';
import { chainSection } from '@/store/balances/const';
import {
  BlockchainAccountWithBalance,
  XpubAccountWithBalance,
  XpubPayload
} from '@/store/balances/types';
import { Section } from '@/store/const';
import { useTasks } from '@/store/tasks';
import { Properties } from '@/types';
import { Currency } from '@/types/currency';
import { TaskType } from '@/types/task-type';
import { Zero } from '@/utils/bignumbers';

@Component({
  components: {
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
  computed: {
    ...mapPiniaState(useTasks, ['isTaskRunning']),
    ...mapGetters('session', ['currency']),
    ...mapGetters('balances', [
      'hasDetails',
      'accountAssets',
      'accountLiabilities',
      'loopringBalances'
    ])
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
  @Prop({ required: false, type: Boolean, default: false })
  loopring!: boolean;

  @Emit()
  editClick(_account: BlockchainAccountWithBalance) {}

  @Emit()
  deleteXpub(_payload: XpubPayload) {}

  @Emit()
  addressesSelected(_selected: string[]) {}

  section = !this.loopring
    ? chainSection[this.blockchain]
    : Section.L2_LOOPRING_BALANCES;
  currency!: Currency;
  isTaskRunning!: (type: TaskType) => Ref<boolean>;
  accountAssets!: (account: string) => AssetBalance[];
  accountLiabilities!: (account: string) => AssetBalance[];
  loopringBalances!: (account: string) => AssetBalance[];
  hasDetails!: (account: string) => boolean;

  expanded = [];

  collapsedXpubs: XpubAccountWithBalance[] = [];

  get isEth2() {
    return this.blockchain === Blockchain.ETH2;
  }

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
    const currency = { symbol: this.currency.tickerSymbol };
    const currencyHeader =
      this.blockchain === 'ETH'
        ? this.$t('account_balances.headers.usd_value_eth', currency)
        : this.$t('account_balances.headers.usd_value', currency);

    const accountHeader =
      this.blockchain === 'ETH2'
        ? this.$t('account_balances.headers.validator')
        : this.$t('account_balances.headers.account');

    const headers: DataTableHeader[] = [
      { text: '', value: 'accountSelection', width: '34px', sortable: false },
      { text: accountHeader.toString(), value: 'label' },
      { text: this.blockchain, value: 'balance.amount', align: 'end' },
      {
        text: currencyHeader.toString(),
        value: 'balance.usdValue',
        align: 'end'
      }
    ];

    if (this.isEth2) {
      headers.push({
        text: this.$t('account_balances.headers.ownership').toString(),
        value: 'ownershipPercentage',
        align: 'end',
        width: '28'
      });
    }

    headers.push({
      text: this.$tc('account_balances.headers.actions'),
      value: 'actions',
      align: 'center',
      sortable: false,
      width: '28'
    });

    if (this.blockchain !== Blockchain.BTC) {
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
      this.isTaskRunning(TaskType.ADD_ACCOUNT).value ||
      this.isTaskRunning(TaskType.REMOVE_ACCOUNT).value
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
              chain: Blockchain.BTC
            }
          );
        })
      );
  }

  private withL2(
    balances: BlockchainAccountWithBalance[]
  ): BlockchainAccountWithBalance[] {
    if (this.blockchain !== Blockchain.ETH || this.loopring) {
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
    return this.blockchain === Blockchain.BTC;
  }

  get expandable(): boolean {
    return this.blockchain === Blockchain.ETH;
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
