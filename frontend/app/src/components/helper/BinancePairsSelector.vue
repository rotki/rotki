<template>
  <v-card v-bind="$attrs">
    <div class="mx-4 pt-2">
      <v-autocomplete
        :items="allMakerts"
        :filter="filter"
        :search-input.sync="search"
        multiple
        :loading="loading"
        :disabled="loading"
        hide-details
        hide-selected
        hide-no-data
        return-object
        chips
        clearable
        :outlined="outlined"
        :open-on-clear="false"
        :label="label ? label : $t('binance_market_selector.default_label')"
        :class="outlined ? 'binance-market-selector--outlined' : null"
        item-text="address"
        item-value="address"
        class="binance-market-selector"
        :value="selection"
        @input="input($event)"
        @change="search = ''"
      >
        <template #selection="data">
          <v-chip
            v-bind="data.attrs"
            :input-value="data.selected"
            :click="data.select"
            filter
            close
            @click:close="data.parent.selectItem(data.item)"
          >
            {{ data.item }}
          </v-chip>
        </template>
        <template #item="data">
          <div
            class="binance-market-selector__list__item d-flex justify-space-between flex-grow-1"
          >
            <div class="binance-market-selector__list__item__address-label">
              <v-chip :color="dark ? null : 'grey lighten-3'" filter>
                {{ data.item }}
              </v-chip>
            </div>
          </div>
        </template>
      </v-autocomplete>
    </div>
  </v-card>
</template>

<script lang="ts">
import { Component, Emit, Mixins, Prop } from 'vue-property-decorator';
import AccountDisplay from '@/components/display/AccountDisplay.vue';
import TagIcon from '@/components/tags/TagIcon.vue';
import ThemeMixin from '@/mixins/theme-mixin';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';

@Component({
  components: { AccountDisplay, TagIcon }
})
export default class BinancePairsSelector extends Mixins(ThemeMixin) {
  @Prop({ required: false, type: String })
  label!: string;
  @Prop({ required: false, type: Boolean, default: false })
  outlined!: boolean;
  @Prop({ required: true, type: Array })
  value!: string[];
  @Prop({ required: true, type: String })
  name!: string;
  @Prop({ required: true, type: String })
  location!: string;
  @Emit()
  input(_value: string[]) {}

  search: string = '';
  queriedMarkets: string[] = [];
  selection: string[] = [];
  allMakerts: string[] = [];
  multiple: boolean = true;
  loading: boolean = false;

  async mounted() {
    this.loading = true;
    try {
      this.queriedMarkets = await this.$api.queryBinanceUserMarkets(
        this.name,
        this.location
      );
    } catch (e) {
      const title = this.$t(
        'binance_market_selector.query_user.title'
      ).toString();
      const description = this.$t('binance_market_selector.query_user.error', {
        message: e.message
      }).toString();
      notify(description, title, Severity.ERROR, true);
    }

    try {
      this.allMakerts = await this.$api.queryBinanceMarkets();
    } catch (e) {
      const title = this.$t(
        'binance_market_selector.query_all.title'
      ).toString();
      const description = this.$t('binance_market_selector.query_all.error', {
        message: e.message
      }).toString();
      notify(description, title, Severity.ERROR, true);
    }

    this.loading = false;
    this.selection = this.queriedMarkets;
  }

  get displayedPairs(): String[] {
    if (this.queriedMarkets.length > 0) {
      return this.allMakerts.filter(pair => this.queriedMarkets.includes(pair));
    }
    return this.queriedMarkets;
  }

  filter(item: String, queryText: string) {
    const query = queryText.toLocaleLowerCase();
    const pair = item.toLocaleLowerCase();

    return pair.indexOf(query) > -1;
  }
}
</script>

<style scoped lang="scss">
.binance-market-selector {
  &--outlined {
    ::v-deep {
      /* stylelint-disable */
      .v-label:not(.v-label--active) {
        /* stylelint-enable */
        top: 24px;
      }

      .v-input {
        &__icon {
          &--append {
            margin-top: 6px;
          }
        }
      }
    }
  }
}
</style>
