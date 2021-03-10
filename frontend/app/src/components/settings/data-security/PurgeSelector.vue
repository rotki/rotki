<template>
  <fragment>
    <v-row align="center">
      <v-col>
        <v-autocomplete
          outlined
          :value="value"
          :label="$t('purge_selector.label')"
          :items="purgable"
          item-text="text"
          item-value="id"
          :disabled="pending"
          @input="input"
        />
      </v-col>
      <v-col cols="auto">
        <div class="pb-6">
          <v-tooltip open-delay="400" top>
            <template #activator="{ on, attrs }">
              <v-btn
                v-bind="attrs"
                icon
                :disabled="!value || pending"
                :loading="pending"
                v-on="on"
                @click="purge({ source: value, text: text(value) })"
              >
                <v-icon>mdi-delete</v-icon>
              </v-btn>
            </template>
            <span> {{ $t('purge_selector.tooltip') }} </span>
          </v-tooltip>
        </div>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col>
        <action-status-indicator :status="status" />
      </v-col>
    </v-row>
  </fragment>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { DEFI_MODULES } from '@/components/defi/wizard/consts';
import ActionStatusIndicator from '@/components/error/ActionStatusIndicator.vue';
import Fragment from '@/components/helper/Fragment';
import { tradeLocations } from '@/components/history/consts';
import { EXCHANGE_CRYPTOCOM, SUPPORTED_EXCHANGES } from '@/data/defaults';
import { MODULES } from '@/services/session/consts';
import { ActionStatus } from '@/store/types';

export const ALL_EXCHANGES = 'all_exchanges';
export const ALL_MODULES = 'all_modules';
export const ALL_TRANSACTIONS = 'ethereum_transactions';

const purgable = [
  ALL_EXCHANGES,
  ALL_MODULES,
  ALL_TRANSACTIONS,
  ...SUPPORTED_EXCHANGES,
  EXCHANGE_CRYPTOCOM,
  ...MODULES
];

export type Purgable = typeof purgable[number];
export type PurgeParams = { readonly source: Purgable; readonly text: string };

@Component({
  components: { ActionStatusIndicator, Fragment }
})
export default class PurgeSelector extends Vue {
  readonly purgable = purgable.map(id => ({
    id: id,
    text: this.text(id)
  }));

  @Prop({ required: true })
  value!: Purgable;

  @Prop({ required: false })
  status!: ActionStatus | null;

  @Prop({ required: false, type: Boolean, default: false })
  pending!: boolean;

  @Emit()
  input(_value: Purgable) {}

  @Emit()
  purge(_payload: PurgeParams) {}

  text(source: Purgable) {
    const location = tradeLocations.find(
      ({ identifier }) => identifier === source
    );
    if (location) {
      return this.$t('purge_selector.exchange', {
        name: location.name
      }).toString();
    }

    const module = DEFI_MODULES.find(({ identifier }) => identifier === source);
    if (module) {
      return this.$t('purge_selector.module', { name: module.name }).toString();
    }

    if (source === ALL_TRANSACTIONS) {
      return this.$t('purge_selector.ethereum_transactions').toString();
    } else if (source === ALL_EXCHANGES) {
      return this.$t('purge_selector.all_exchanges').toString();
    } else if (source === ALL_MODULES) {
      return this.$t('purge_selector.all_modules').toString();
    }
    return source;
  }
}
</script>

<style scoped lang="scss"></style>
