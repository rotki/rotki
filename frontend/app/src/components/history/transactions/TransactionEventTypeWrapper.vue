<template>
  <div class="d-flex align-center">
    <v-badge v-if="counterparty" avatar overlap color="white" @click="copy">
      <template #badge>
        <v-tooltip top>
          <template #activator="{ on }">
            <div v-on="on">
              <v-avatar>
                <v-icon v-if="counterparty.icon" :color="counterparty.color">
                  {{ counterparty.icon }}
                </v-icon>
                <v-img v-else :src="counterparty.image" />
              </v-avatar>
            </div>
          </template>
          <div>{{ counterparty.label }}</div>
        </v-tooltip>
      </template>
      <v-avatar
        class="text--darken-4"
        :color="dark ? 'white' : 'grey lighten-3'"
        :size="36"
      >
        <v-icon :size="20" :color="attrs.color || 'grey darken-2'">
          {{ attrs.icon }}
        </v-icon>
      </v-avatar>
    </v-badge>
    <v-avatar
      v-else
      class="text--darken-4"
      :color="dark ? 'white' : 'grey lighten-3'"
      :size="36"
    >
      <v-icon :size="20" :color="attrs.color || 'grey darken-2'">
        {{ attrs.icon }}
      </v-icon>
    </v-avatar>
    <div class="ml-4">
      <div class="font-weight-bold text-uppercase">{{ attrs.label }}</div>
      <slot />
    </div>
  </div>
</template>
<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  toRefs,
  unref
} from '@vue/composition-api';
import { setupThemeCheck } from '@/composables/common';
import { ActionDataEntry } from '@/store/history/consts';
import { EthTransactionEventEntry } from '@/store/history/types';
import { getEventCounterpartyData, getEventTypeData } from '@/utils/history';

export default defineComponent({
  name: 'TransactionEventTypeWrapper',
  props: {
    event: {
      required: true,
      type: Object as PropType<EthTransactionEventEntry>
    }
  },
  setup(props) {
    const { event } = toRefs(props);

    const { dark } = setupThemeCheck();

    const attrs = computed<ActionDataEntry>(() => {
      return getEventTypeData(unref(event));
    });

    const counterparty = computed<ActionDataEntry | null>(() => {
      return getEventCounterpartyData(unref(event));
    });

    const copy = () => {
      navigator.clipboard.writeText(unref(event).counterparty || '');
    };

    return {
      dark,
      attrs,
      counterparty,
      copy
    };
  }
});
</script>
