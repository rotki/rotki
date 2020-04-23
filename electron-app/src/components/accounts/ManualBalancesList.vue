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
            <span class="manual-balances-list__amount">
              {{ item.amount | formatPrice(floatingPrecision) }}
            </span>
          </template>
          <template #item.usdValue="{ item }">
            {{
              item.usdValue
                | calculatePrice(exchangeRate(currency.ticker_symbol))
                | formatPrice(floatingPrecision)
            }}
          </template>
          <template #item.location="{ item }">
            <span class="manual-balances-list__location">
              {{ item.location }}
            </span>
          </template>
          <template #item.actions="{ item }">
            <span>
              <v-icon
                small
                class="mr-2 manual-balances-list__actions__edit"
                @click="edited = item"
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
              <td>
                {{
                  visibleBalances.map(val => val.usdValue)
                    | balanceSum
                    | calculatePrice(exchangeRate(currency.ticker_symbol))
                    | formatPrice(floatingPrecision)
                }}
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
    <v-dialog
      max-width="600"
      persistent
      :value="!!edited"
      @input="edited = null"
    >
      <v-card class="manual-balances-list__edit-form">
        <v-card-title>
          Edit Manual Balance
        </v-card-title>
        <v-card-subtitle>
          Modify tags and amount of the balance
        </v-card-subtitle>
        <v-card-text>
          <manual-balances-form
            :edit="edited"
            @clear="edited = null"
          ></manual-balances-form>
        </v-card-text>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import ManualBalancesForm from '@/components/accounts/ManualBalancesForm.vue';
import CryptoIcon from '@/components/CryptoIcon.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import TagFilter from '@/components/inputs/TagFilter.vue';
import TagIcon from '@/components/tags/TagIcon.vue';
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
    ManualBalancesForm,
    AssetDetails,
    ConfirmDialog,
    TagIcon,
    CryptoIcon,
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
    { text: 'Amount', value: 'amount' },
    { text: 'USD Value', value: 'usdValue' },
    { text: 'Location', value: 'location' },
    { text: 'Actions', value: 'actions', sortable: false, width: '50' }
  ];

  manualBalances!: ManualBalance[];
  tags!: Tags;
  currency!: Currency;
  floatingPrecision!: number;
  exchangeRate!: (currency: string) => number;

  get visibleBalances(): ManualBalance[] {
    return this.manualBalances.filter(balances => {
      return this.onlyTags.every(tag => balances.tags.includes(tag));
    });
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
