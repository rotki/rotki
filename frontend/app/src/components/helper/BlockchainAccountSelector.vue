<template>
  <v-card v-bind="$attrs">
    <div class="mx-4 pt-2">
      <v-autocomplete
        :value="value"
        :items="displayedAccounts"
        :filter="filter"
        :search-input.sync="search"
        :multiple="multiple"
        :loading="loading"
        :disabled="loading"
        hide-details
        hide-selected
        hide-no-data
        return-object
        chips
        clearable
        :open-on-clear="false"
        :label="label ? label : $t('blockchain_account_selector.default_label')"
        item-text="address"
        item-value="address"
        class="blockchain-account-selector"
        @input="input($event)"
      >
        <template #selection="data">
          <v-chip
            v-if="multiple"
            :key="data.item.chain + data.item.address"
            v-bind="data.attrs"
            :input-value="data.selected"
            :click="data.select"
            filter
            close
            @click:close="data.parent.selectItem(data.item)"
          >
            <account-display :account="data.item" />
          </v-chip>
          <div v-else>
            <account-display :account="data.item" class="pr-2" />
          </div>
        </template>
        <template #item="data">
          <div
            class="blockchain-account-selector__list__item d-flex justify-space-between flex-grow-1"
          >
            <div class="blockchain-account-selector__list__item__address-label">
              <v-chip color="grey lighten-3" filter>
                <account-display :account="data.item" />
              </v-chip>
            </div>
            <div class="blockchain-account-selector__list__item__tags">
              <tag-icon
                v-for="tag in data.item.tags"
                :key="tag"
                class="mr-1"
                :tag="tags[tag]"
              />
            </div>
          </div>
        </template>
      </v-autocomplete>
    </div>
    <v-card-text v-if="hint">
      {{ $t('blockchain_account_selector.hint', { hintText }) }}
      <slot />
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { mapGetters, mapState } from 'vuex';
import AccountDisplay from '@/components/display/AccountDisplay.vue';
import TagIcon from '@/components/tags/TagIcon.vue';

import { Blockchain, GeneralAccount, Tags } from '@/typing/types';

@Component({
  components: { AccountDisplay, TagIcon },
  computed: {
    ...mapState('session', ['tags']),
    ...mapGetters('balances', ['accounts'])
  }
})
export default class BlockchainAccountSelector extends Vue {
  @Prop({ required: false, type: String })
  label!: string;
  @Prop({ required: false, type: Boolean, default: false })
  hint!: boolean;
  @Prop({ required: false, type: Boolean, default: false })
  loading!: boolean;
  @Prop({ required: false, type: Array, default: () => [] })
  usableAddresses!: string[];
  @Prop({ required: false, type: Boolean, default: false })
  multiple!: boolean;
  @Prop({ required: true })
  value!: GeneralAccount[] | GeneralAccount | null;
  @Prop({ required: false, type: Array, default: () => [] })
  chains!: Blockchain[];

  accounts!: GeneralAccount[];
  tags!: Tags;
  search: string = '';

  get selectableAccounts(): GeneralAccount[] {
    if (this.chains.length === 0) {
      return this.accounts;
    }
    return this.accounts.filter(({ chain }) => this.chains.includes(chain));
  }

  get hintText(): string {
    const all = this.$t('blockchain_account_selector.all').toString();
    if (Array.isArray(this.value)) {
      return this.value.length > 0 ? this.value.length.toString() : all;
    }
    return this.value ? '1' : all;
  }

  @Emit()
  input(_value: string) {}

  get displayedAccounts(): GeneralAccount[] {
    if (this.usableAddresses.length > 0) {
      return this.selectableAccounts.filter(({ address }) =>
        this.usableAddresses.includes(address)
      );
    }
    return this.selectableAccounts;
  }

  filter(item: GeneralAccount, queryText: string) {
    const text = item.label.toLocaleLowerCase();
    const query = queryText.toLocaleLowerCase();
    const address = item.address.toLocaleLowerCase();

    const labelMatches = text.indexOf(query) > -1;
    const addressMatches = address.indexOf(query) > -1;

    const tagMatches =
      item.tags
        .map(tag => tag.toLocaleLowerCase())
        .join(' ')
        .indexOf(query) > -1;

    return labelMatches || tagMatches || addressMatches;
  }
}
</script>

<style scoped lang="scss"></style>
