<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-data-table
          :headers="headers"
          :items="manualBalances"
          class="manual-balances-list"
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
          <template #item.asset="{ item }">
            <span class="manual-balances-list__asset">
              <crypto-icon
                width="26px"
                class="manual-balances-list__asset__icon"
                :symbol="item.asset"
              ></crypto-icon>
              {{ item.asset }}
            </span>
          </template>
          <template #item.amount="{ item }">
            {{ item.amount | formatPrice(floatingPrecision) }}
          </template>
          <template #item.usdValue="{ item }">
            {{
              item.usdValue
                | calculatePrice(exchangeRate(currency.ticker_symbol))
                | formatPrice(floatingPrecision)
            }}
          </template>
          <template #item.actions="{ item }">
            <span>
              <v-icon small class="mr-2" @click="edit(item)">
                fa-edit
              </v-icon>
              <v-icon small @click="labelToDelete = item.label">
                fa-trash
              </v-icon>
            </span>
          </template>
        </v-data-table>
      </v-col>
    </v-row>
    <confirm-dialog
      :display="!!labelToDelete"
      title="Delete manually tracked balance"
      message="Are you sure you want to delete this entry?"
      @cancel="labelToDelete = ''"
      @confirm="deleteLabel()"
    ></confirm-dialog>
  </v-container>
</template>

<script lang="ts">
import { Component, Emit, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import CryptoIcon from '@/components/CryptoIcon.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
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
  components: { ConfirmDialog, TagIcon, CryptoIcon },
  computed: {
    ...mapBalanceState(['manualBalances']),
    ...mapSessionState(['tags']),
    ...mapSessionGetters(['floatingPrecision', 'currency']),
    ...mapBalanceGetters(['exchangeRate'])
  }
})
export default class ManuallyTrackedBalanceList extends Vue {
  labelToDelete = '';

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

  @Emit()
  edit(_item: ManualBalance | null) {}

  async deleteLabel() {
    this.edit(null);
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

  &__label {
    padding-bottom: 0 !important;
  }

  &__asset {
    display: flex;
    flex-direction: row;
    align-items: center;
    &__icon {
      margin-right: 8px;
    }
  }
}
</style>
