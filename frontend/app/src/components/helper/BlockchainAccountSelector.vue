<template>
  <div>
    <v-autocomplete
      v-model="selectedAccounts"
      :items="filteredBlockchainAccounts"
      :filter="filter"
      :search-input.sync="search"
      :multiple="multiple"
      solo
      return-object
      hide-selected
      hide-no-data
      chips
      clearable
      :open-on-clear="false"
      label="Select blockchain account(s)"
      item-text="address"
      item-value="address"
    >
      <template #selection="data">
        <v-chip
          v-if="multiple"
          :key="data.item.chain + data.item.label"
          v-bind="data.attrs"
          :input-value="data.selected"
          :click="data.select"
          filter
          close
          @click:close="data.parent.selectItem(data.item)"
        >
          <div class="pr-2">
            <v-avatar left>
              <crypto-icon :symbol="data.item.chain"></crypto-icon>
            </v-avatar>
            <span class="font-weight-bold mr-1">{{ data.item.label }}</span>
            <span>({{ data.item.address | truncateAddress }})</span>
          </div>
        </v-chip>
        <div v-else>
          <div class="pr-2">
            <v-avatar left>
              <crypto-icon width="24px" :symbol="data.item.chain"></crypto-icon>
            </v-avatar>
            <span class="font-weight-bold mr-1">{{ data.item.label }}</span>
            <span>({{ data.item.address | truncateAddress }})</span>
          </div>
        </div>
      </template>
      <template #item="data">
        <div
          class="blockchain-account-selector__list__item d-flex justify-space-between flex-grow-1"
        >
          <div class="blockchain-account-selector__list__item__address-label">
            <v-chip color="grey lighten-3" filter>
              <v-avatar left>
                <crypto-icon
                  width="24px"
                  :symbol="data.item.chain"
                ></crypto-icon>
              </v-avatar>
              <span class="font-weight-bold mr-1">{{ data.item.label }}</span>
              <span>({{ data.item.address | truncateAddress }})</span>
            </v-chip>
          </div>
          <div class="blockchain-account-selector__list__item__tags">
            <tag-icon
              v-for="tag in data.item.tags"
              :key="tag"
              class="mr-1"
              :tag="tags[tag]"
            ></tag-icon>
          </div>
        </div>
      </template>
    </v-autocomplete>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue, Watch } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import CryptoIcon from '@/components/CryptoIcon.vue';
import TagIcon from '@/components/tags/TagIcon.vue';

import {
  Account,
  AccountData,
  AccountDataMap,
  Tags,
  Blockchain
} from '@/typing/types';

export interface GeneralAccount extends AccountData {
  chain: Blockchain;
}

const { mapState } = createNamespacedHelpers('session');
const { mapState: mapBalanceState } = createNamespacedHelpers('balances');

@Component({
  components: { CryptoIcon, TagIcon },
  computed: {
    ...mapState(['tags']),
    ...mapBalanceState(['ethAccounts', 'btcAccounts'])
  }
})
export default class BlockchainAccountSelector extends Vue {
  @Prop({ required: true, type: Array, default: [] })
  addresses!: Account[];
  @Prop({ required: false, type: Boolean, default: false })
  multiple!: boolean;

  ethAccounts!: AccountDataMap;
  btcAccounts!: AccountDataMap;
  tags!: Tags;
  selectedAccounts: GeneralAccount[] | GeneralAccount | null = null;
  select = ['Vuetify', 'Programming'];
  items = ['Programming', 'Design', 'Vue', 'Vuetify'];
  search: string = '';

  get filteredBlockchainAccounts(): any[] {
    let filteredAccounts: GeneralAccount[] = [];

    // filter the addresses for each blockchain then group them into filteredAddresses
    for (let [key, value] of Object.entries(this.ethAccounts)) {
      if (this.addresses[this.addresses.findIndex(x => x.address === key)]) {
        filteredAccounts.push({ chain: 'ETH', ...value });
      }
    }
    for (let [key, value] of Object.entries(this.btcAccounts)) {
      if (this.addresses[this.addresses.findIndex(x => x.address === key)]) {
        filteredAccounts.push({ chain: 'BTC', ...value });
      }
    }

    return filteredAccounts;
  }

  @Watch('selectedAccounts')
  onSelectedAccountsChange() {
    this.$emit('selected-accounts-change', this.selectedAccounts);

    // Force clear the search value on change (e.g. after searching for an account
    // and then clicking enter)
    if (this.search) {
      this.search = '';
    }
  }

  filter(item: GeneralAccount, queryText: string) {
    const hasValue = (val: string | null) => (val != null ? val : '');

    const text = hasValue(item.label);
    const query = hasValue(queryText);

    const labelMatches =
      text.toString().toLowerCase().indexOf(query.toString().toLowerCase()) >
      -1;

    const tagMatches =
      item.tags
        .toString()
        .toLowerCase()
        .indexOf(query.toString().toLowerCase()) > -1;

    return labelMatches || tagMatches;
  }
}
</script>

<style scoped lang="scss"></style>
