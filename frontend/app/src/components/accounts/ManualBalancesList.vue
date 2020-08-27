<template>
  <v-container>
    <v-row>
      <v-col cols="6" offset="6">
        <tag-filter v-model="onlyTags"></tag-filter>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <v-data-table
          :headers="headers"
          :items="visibleBalances"
          class="manual-balances-list"
          sort-by="usdValue"
          :footer-props="footerProps"
          sort-desc
        >
          <template #item.label="{ item }">
            <v-row>
              <v-col
                cols="12"
                class="font-weight-medium manual-balances-list__label"
              >
                {{ item.label }}
              </v-col>
            </v-row>
            <v-row v-if="item.tags">
              <v-col cols="12">
                <tag-icon
                  v-for="tag in item.tags"
                  :key="tag"
                  class="manual-balances-list__tag"
                  :tag="tags[tag]"
                ></tag-icon>
              </v-col>
            </v-row>
          </template>
          <template #header.usdValue>
            {{ currency.ticker_symbol }} Value
          </template>
          <template #item.asset="{ item }">
            <asset-details :asset="item.asset"></asset-details>
          </template>
          <template #item.amount="{ item }">
            <amount-display
              class="manual-balances-list__amount"
              :value="item.amount"
            ></amount-display>
          </template>
          <template #item.usdValue="{ item }">
            <amount-display
              :amount="item.amount"
              :fiat-currency="item.asset"
              :value="item.usdValue"
            >
            </amount-display>
          </template>
          <template #item.location="{ item }">
            <span class="manual-balances-list__location">
              {{ item.location | capitalize }}
            </span>
          </template>
          <template #item.actions="{ item }">
            <span>
              <v-icon
                small
                class="mr-2 manual-balances-list__actions__edit"
                @click="editBalance(item)"
              >
                fa-edit
              </v-icon>
              <v-icon
                small
                class="manual-balances-list__actions__delete"
                @click="labelToDelete = item.label"
              >
                fa-trash
              </v-icon>
            </span>
          </template>
          <template v-if="visibleBalances.length > 0" #body.append>
            <tr class="manual-balances-list__total">
              <td>Total</td>
              <td></td>
              <td></td>
              <td class="text-end">
                <amount-display
                  class="manual-balances-list__amount"
                  :fiat-currency="currency.ticker_symbol"
                  :value="
                    visibleBalances
                      | aggregateTotal(
                        currency.ticker_symbol,
                        exchangeRate(currency.ticker_symbol),
                        floatingPrecision
                      )
                  "
                ></amount-display>
              </td>
            </tr>
          </template>
        </v-data-table>
      </v-col>
    </v-row>
    <confirm-dialog
      v-if="labelToDelete"
      :display="!!labelToDelete"
      title="Delete manually tracked balance"
      message="Are you sure you want to delete this entry?"
      @cancel="labelToDelete = ''"
      @confirm="deleteLabel()"
    ></confirm-dialog>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import TagFilter from '@/components/inputs/TagFilter.vue';
import TagIcon from '@/components/tags/TagIcon.vue';
import { footerProps } from '@/config/datatable.common';
import { Currency } from '@/model/currency';
import { ManualBalance } from '@/services/types-model';
import { Tags } from '@/typing/types';

const {
  mapState: mapSessionState,
  mapGetters: mapSessionGetters
} = createNamespacedHelpers('session');
const {
  mapState: mapBalanceState,
  mapGetters: mapBalanceGetters
} = createNamespacedHelpers('balances');

@Component({
  components: {
    AmountDisplay,
    AssetDetails,
    ConfirmDialog,
    TagIcon,
    TagFilter
  },
  computed: {
    ...mapBalanceState(['manualBalances']),
    ...mapSessionState(['tags']),
    ...mapSessionGetters(['floatingPrecision', 'currency']),
    ...mapBalanceGetters(['exchangeRate'])
  }
})
export default class ManualBalancesList extends Vue {
  labelToDelete = '';
  onlyTags: string[] = [];
  edited: ManualBalance | null = null;

  headers = [
    { text: 'Label', value: 'label' },
    { text: 'Asset', value: 'asset', width: '200' },
    { text: 'Amount', value: 'amount', align: 'end' },
    { text: 'USD Value', value: 'usdValue', align: 'end' },
    { text: 'Location', value: 'location' },
    { text: 'Actions', value: 'actions', sortable: false, width: '50' }
  ];

  manualBalances!: ManualBalance[];
  tags!: Tags;
  currency!: Currency;
  floatingPrecision!: number;
  exchangeRate!: (currency: string) => number;

  footerProps = footerProps;

  get visibleBalances(): ManualBalance[] {
    if (this.onlyTags.length === 0) {
      return this.manualBalances;
    }

    return this.manualBalances.filter(balance => {
      if (balance.tags) {
        return this.onlyTags.every(tag => balance.tags.includes(tag));
      }
    });
  }

  editBalance(balance: ManualBalance) {
    this.$emit('editBalance', balance);
  }

  async deleteLabel() {
    this.edited = null;
    await this.$store.dispatch(
      'balances/deleteManualBalance',
      this.labelToDelete
    );
    this.labelToDelete = '';
  }
}
</script>

<style scoped lang="scss">
.manual-balances-list {
  &__tag {
    margin-right: 8px;
  }

  &__total {
    font-weight: 500;
  }

  &__label {
    padding-bottom: 0 !important;
  }
}
</style>
