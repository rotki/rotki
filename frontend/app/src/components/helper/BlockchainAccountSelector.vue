<template>
  <v-card>
    <div class="mx-4 pt-2">
      <v-autocomplete
        v-model="selectedAccounts"
        :items="filteredBlockchainAccounts"
        :filter="filter"
        :search-input.sync="search"
        :multiple="multiple"
        return-object
        hide-details
        hide-selected
        hide-no-data
        chips
        clearable
        :open-on-clear="false"
        label="Filter account(s)"
        item-text="address"
        item-value="address"
        class="blockchain-account-selector"
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
                <crypto-icon
                  width="24px"
                  :symbol="data.item.chain"
                ></crypto-icon>
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
    <v-card-text>
      Showing results across
      {{
        selectedAccountsArray && selectedAccountsArray.length > 0
          ? selectedAccountsArray.length
          : 'all'
      }}
      accounts.
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import CryptoIcon from '@/components/CryptoIcon.vue';
import TagIcon from '@/components/tags/TagIcon.vue';

import { Account, AccountDataMap, GeneralAccount, Tags } from '@/typing/types';

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

  selectedAccountsArray: GeneralAccount[] = [];
  search: string = '';

  private unselectAll() {
    for (let i = 0; i < this.selectedAccountsArray.length; i++) {
      this.selectedAccountsArray.pop();
    }
  }

  set selectedAccounts(value: GeneralAccount[] | GeneralAccount | null) {
    if (!value) {
      this.unselectAll();
    } else if (Array.isArray(value)) {
      this.selectedAccountsArray.push(...value);
    } else {
      if (!this.multiple) {
        this.unselectAll();
      }
      this.selectedAccountsArray.push(value);
    }
    this.$emit('selected-accounts-change', this.selectedAccountsArray);
    if (this.search) {
      this.search = '';
    }
  }

  get selectedAccounts(): GeneralAccount[] | GeneralAccount | null {
    if (this.selectedAccountsArray.length === 0) {
      return null;
    } else if (this.selectedAccountsArray.length === 1) {
      const [first] = this.selectedAccountsArray;
      return first;
    }
    return this.selectedAccountsArray;
  }

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

  filter(item: GeneralAccount, queryText: string) {
    const text = item.label.toLocaleLowerCase();
    const query = queryText.toLocaleLowerCase();

    const labelMatches = text.indexOf(query) > -1;

    const tagMatches =
      item.tags
        .map(tag => tag.toLocaleLowerCase())
        .join(' ')
        .indexOf(query) > -1;

    return labelMatches || tagMatches;
  }
}
</script>

<style scoped lang="scss"></style>
