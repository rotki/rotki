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
import { SUPPORTED_MODULES } from '@/components/defi/wizard/consts';
import ActionStatusIndicator from '@/components/error/ActionStatusIndicator.vue';
import Fragment from '@/components/helper/Fragment';
import { tradeLocations } from '@/components/history/consts';
import {
  ALL_DECENTRALIZED_EXCHANGES,
  ALL_CENTRALIZED_EXCHANGES,
  ALL_MODULES,
  ALL_TRANSACTIONS,
  PURGABLE
} from '@/services/session/consts';
import { Purgeable } from '@/services/session/types';
import { ActionStatus } from '@/store/types';

export type PurgeParams = { readonly source: Purgeable; readonly text: string };

@Component({
  components: { ActionStatusIndicator, Fragment }
})
export default class PurgeSelector extends Vue {
  readonly purgable = PURGABLE.map(id => ({
    id: id,
    text: this.text(id)
  })).sort((a, b) => (a.text < b.text ? -1 : 1));

  @Prop({ required: true })
  value!: Purgeable;

  @Prop({ required: false })
  status!: ActionStatus | null;

  @Prop({ required: false, type: Boolean, default: false })
  pending!: boolean;

  @Emit()
  input(_value: Purgeable) {}

  @Emit()
  purge(_payload: PurgeParams) {}

  text(source: Purgeable) {
    const location = tradeLocations.find(
      ({ identifier }) => identifier === source
    );
    if (location) {
      return this.$t('purge_selector.exchange', {
        name: location.name
      }).toString();
    }

    const module = SUPPORTED_MODULES.find(
      ({ identifier }) => identifier === source
    );
    if (module) {
      return this.$t('purge_selector.module', { name: module.name }).toString();
    }

    if (source === ALL_TRANSACTIONS) {
      return this.$t('purge_selector.ethereum_transactions').toString();
    } else if (source === ALL_CENTRALIZED_EXCHANGES) {
      return this.$t('purge_selector.all_exchanges').toString();
    } else if (source === ALL_MODULES) {
      return this.$t('purge_selector.all_modules').toString();
    } else if (source === ALL_DECENTRALIZED_EXCHANGES) {
      return this.$t('purge_selector.all_decentralized_exchanges').toString();
    }
    return source;
  }
}
</script>

<style scoped lang="scss"></style>
