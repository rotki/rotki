<template>
  <v-data-table
    v-bind="$attrs"
    :headers="headers"
    :items="visibleBalances"
    :loading="accountOperation || loading"
    :loading-text="$t('account_balances.data_table.loading')"
    single-expand
    item-key="address"
    :expanded.sync="expanded"
    sort-by="balance.usdValue"
    :footer-props="footerProps"
    :custom-group="groupBy"
    :group-by="isBtc ? ['xpub', 'derivationPath'] : undefined"
    sort-desc
    v-on="$listeners"
  >
    <template v-if="blockchain === 'ETH'" #header.balance.usdValue>
      {{
        $t('account_balances.headers.usd-value-eth', {
          symbol: currency.ticker_symbol
        })
      }}
    </template>
    <template v-else #header.balance.usdValue>
      {{
        $t('account_balances.headers.usd-value', {
          symbol: currency.ticker_symbol
        })
      }}
    </template>
    <template #item.address="{ item }">
      <v-row>
        <v-col cols="12" class="account-balance-table__account">
          <labeled-address-display :account="item" />
          <span v-if="item.tags.length > 0" class="mt-2">
            <tag-icon
              v-for="tag in item.tags"
              :key="tag"
              class="account-balance-table__tag"
              :tag="tags[tag]"
            />
          </span>
        </v-col>
      </v-row>
    </template>
    <template #item.balance.amount="{ item }">
      <amount-display :value="item.balance.amount" />
    </template>
    <template #item.balance.usdValue="{ item }">
      <amount-display
        fiat-currency="USD"
        :value="item.balance.usdValue"
        show-currency="symbol"
      />
    </template>
    <template #item.actions="{ item }">
      <row-actions
        class="account-balance-table__actions"
        :edit-tooltip="$t('account_balances.edit_tooltip')"
        :delete-tooltip="$t('account_balances.delete_tooltip')"
        :disabled="accountOperation || loading"
        @delete-click="deleteClick(item.address)"
        @edit-click="editClick(item)"
      />
    </template>
    <template v-if="balances.length > 0" #body.append>
      <tr class="account-balance-table__total">
        <td>{{ $t('account_balances.total') }}</td>
        <td class="text-end">
          <amount-display
            :value="visibleBalances.map(val => val.balance.amount) | balanceSum"
          />
        </td>
        <td class="text-end">
          <amount-display
            fiat-currency="USD"
            show-currency="symbol"
            :value="
              visibleBalances.map(val => val.balance.usdValue) | balanceSum
            "
          />
        </td>
      </tr>
    </template>
    <template #expanded-item="{ headers, item }">
      <td :colspan="headers.length" class="account-balance-table__expanded">
        <account-asset-balances :account="item.address" />
      </td>
    </template>
    <template #item.expand="{ item }">
      <row-expander
        v-if="expandable && hasTokens(item.address)"
        :expanded="expanded.includes(item)"
        @click="expanded = expanded.includes(item) ? [] : [item]"
      />
    </template>
    <template #group.header="{ group, headers, items, isOpen, toggle }">
      <account-group-header
        :group="group ? group : ''"
        :items="getItems(items[0].xpub, items[0].derivationPath)"
        :xpub="{
          xpub: items[0].xpub,
          derivationPath: items[0].derivationPath
        }"
        :expanded="isOpen"
        @expand-clicked="toggle"
        @delete-clicked="deleteXpub($event)"
      />
    </template>
  </v-data-table>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapGetters, mapState } from 'vuex';

import AccountGroupHeader from '@/components/accounts/AccountGroupHeader.vue';
import LabeledAddressDisplay from '@/components/display/LabeledAddressDisplay.vue';
import RowActions from '@/components/helper/RowActions.vue';
import RowExpander from '@/components/helper/RowExpander.vue';
import AccountAssetBalances from '@/components/settings/AccountAssetBalances.vue';
import TagIcon from '@/components/tags/TagIcon.vue';
import { footerProps } from '@/config/datatable.common';
import { Currency } from '@/model/currency';
import { TaskType } from '@/model/task-type';
import {
  BlockchainAccount,
  BlockchainAccountWithBalance,
  XpubPayload
} from '@/store/balances/types';
import { Properties } from '@/types';
import { Blockchain, BTC, ETH, Tags } from '@/typing/types';

@Component({
  components: {
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
    ...mapGetters('balances', ['hasTokens']),
    ...mapState('session', ['tags'])
  }
})
export default class AccountBalanceTable extends Vue {
  @Prop({ required: true })
  balances!: BlockchainAccountWithBalance[];
  @Prop({ required: true })
  blockchain!: Blockchain;
  @Prop({ required: true, type: Boolean })
  loading!: boolean;
  @Prop({ required: true, type: Array })
  visibleTags!: string[];

  @Emit()
  deleteClick(_account: string) {}
  @Emit()
  editClick(_account: BlockchainAccount) {}
  @Emit()
  deleteXpub(_payload: XpubPayload) {}

  currency!: Currency;
  isTaskRunning!: (type: TaskType) => boolean;
  hasTokens!: (account: string) => boolean;
  tags!: Tags;

  expanded = [];

  groupBy(
    items: BlockchainAccountWithBalance[],
    groupBy: Properties<BlockchainAccountWithBalance, any>[]
  ) {
    const record = {} as Record<string, BlockchainAccountWithBalance[]>;

    for (let item of items) {
      const key =
        'xpub' in item ? groupBy.map(value => item[value]).join('/') : '';
      if (record[key]) {
        record[key].push(item);
      } else {
        record[key] = [item];
      }
    }

    return Object.keys(record).map(name => ({
      name,
      items: record[name]
    }));
  }

  readonly footerProps = footerProps;
  readonly headers: DataTableHeader[] = [
    { text: this.$tc('account_balances.headers.account'), value: 'address' },
    { text: this.blockchain, value: 'balance.amount', align: 'end' },
    {
      text: this.$tc('account_balances.headers.usd-value-default'),
      value: 'balance.usdValue',
      align: 'end'
    },
    {
      text: this.$tc('account_balances.headers.actions'),
      value: 'actions',
      sortable: false,
      width: '50'
    },
    { text: '', value: 'expand', align: 'end', sortable: false }
  ];

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

  get visibleBalances(): BlockchainAccountWithBalance[] {
    if (this.visibleTags.length === 0) {
      return this.balances;
    }

    return this.balances.filter(({ tags }) =>
      this.visibleTags.every(tag => tags.includes(tag))
    );
  }

  get isBtc(): boolean {
    return this.blockchain === BTC;
  }

  get expandable(): boolean {
    return this.blockchain === ETH;
  }
}
</script>

<style scoped lang="scss">
.account-balance-table {
  &__account {
    display: flex;
    flex-direction: column;
  }

  &__actions {
    display: flex;
    flex-direction: row;
  }

  &__total {
    font-weight: 500;
  }

  &__expanded {
    padding: 0 !important;
  }

  &__tag {
    margin-right: 8px;
    margin-bottom: 2px;
  }
}
</style>
