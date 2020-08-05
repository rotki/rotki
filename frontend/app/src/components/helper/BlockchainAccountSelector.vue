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
        chips
        clearable
        :open-on-clear="false"
        :label="label ? label : 'Filter account(s)'"
        item-text="address"
        item-value="address"
        class="blockchain-account-selector"
        @input="input($event)"
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
              ></tag-icon>
            </div>
          </div>
        </template>
      </v-autocomplete>
    </div>
    <v-card-text v-if="hint">
      Showing results across {{ hintText }} accounts.
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { mapGetters, mapState } from 'vuex';
import AccountDisplay from '@/components/display/AccountDisplay.vue';
import TagIcon from '@/components/tags/TagIcon.vue';

import { GeneralAccount, Tags } from '@/typing/types';

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
  value!: string[] | string | null;

  accounts!: GeneralAccount[];
  tags!: Tags;
  search: string = '';

  get hintText(): string {
    if (typeof this.value === 'string') {
      return '1';
    } else if (Array.isArray(this.value)) {
      return `${this.value.length}`;
    }
    return 'all';
  }

  @Emit()
  input(_value: string) {}

  get displayedAccounts(): GeneralAccount[] {
    if (this.usableAddresses.length > 0) {
      return this.accounts.filter(({ address }) =>
        this.usableAddresses.includes(address)
      );
    }
    return this.accounts;
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
