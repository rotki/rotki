<template>
  <fragment>
    <v-row class="mb-0" align="center">
      <v-col>
        <v-autocomplete
          outlined
          :value="value"
          :label="$t('purge_selector.label')"
          :items="purgable"
          item-text="text"
          item-value="id"
          :disabled="pending"
          hide-details
          @input="input"
        />
      </v-col>
      <v-col cols="auto">
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
      </v-col>
    </v-row>

    <action-status-indicator :status="status" />
  </fragment>
</template>

<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import { SUPPORTED_MODULES } from '@/components/defi/wizard/consts';
import ActionStatusIndicator from '@/components/error/ActionStatusIndicator.vue';
import Fragment from '@/components/helper/Fragment';
import { tradeLocations } from '@/components/history/consts';
import i18n from '@/i18n';
import {
  ALL_CENTRALIZED_EXCHANGES,
  ALL_DECENTRALIZED_EXCHANGES,
  ALL_MODULES,
  ALL_TRANSACTIONS,
  PURGABLE
} from '@/services/session/consts';
import { Purgeable } from '@/services/session/types';
import { ActionStatus } from '@/store/types';

export type PurgeParams = { readonly source: Purgeable; readonly text: string };

export default defineComponent({
  name: 'PurgeSelector',
  components: { ActionStatusIndicator, Fragment },
  props: {
    value: { required: true, type: String as PropType<Purgeable> },
    status: {
      required: false,
      type: Object as PropType<ActionStatus>,
      default: null
    },
    pending: { required: false, type: Boolean, default: false }
  },
  emits: ['input', 'purge'],
  setup(_, { emit }) {
    const input = (value: Purgeable) => emit('input', value);
    const purge = (payload: PurgeParams) => emit('purge', payload);

    const text = (source: Purgeable) => {
      const location = tradeLocations.find(
        ({ identifier }) => identifier === source
      );
      if (location) {
        return i18n
          .t('purge_selector.exchange', {
            name: location.name
          })
          .toString();
      }

      const module = SUPPORTED_MODULES.find(
        ({ identifier }) => identifier === source
      );
      if (module) {
        return i18n
          .t('purge_selector.module', { name: module.name })
          .toString();
      }

      if (source === ALL_TRANSACTIONS) {
        return i18n.t('purge_selector.ethereum_transactions').toString();
      } else if (source === ALL_CENTRALIZED_EXCHANGES) {
        return i18n.t('purge_selector.all_exchanges').toString();
      } else if (source === ALL_MODULES) {
        return i18n.t('purge_selector.all_modules').toString();
      } else if (source === ALL_DECENTRALIZED_EXCHANGES) {
        return i18n.t('purge_selector.all_decentralized_exchanges').toString();
      }
      return source;
    };

    const purgable = PURGABLE.map(id => ({
      id,
      text: text(id)
    })).sort((a, b) => (a.text < b.text ? -1 : 1));

    return {
      input,
      purge,
      text,
      purgable
    };
  }
});
</script>
