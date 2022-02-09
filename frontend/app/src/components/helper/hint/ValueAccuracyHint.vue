<template>
  <v-tooltip v-if="notUsd" open-delay="400" top>
    <template #activator="{ on, attrs }">
      <v-icon v-bind="attrs" small class="mx-2" v-on="on">
        mdi-information
      </v-icon>
    </template>
    <span>{{ $t('price_accuracy_hint.tooltip') }}</span>
  </v-tooltip>
</template>

<script lang="ts">
import { computed, defineComponent, unref } from '@vue/composition-api';
import { setupGeneralSettings } from '@/composables/session';

export default defineComponent({
  name: 'ValueAccuracyHint',
  setup() {
    const { currencySymbol } = setupGeneralSettings();

    const notUsd = computed(() => {
      return unref(currencySymbol) !== 'USD';
    });

    return { notUsd };
  }
});
</script>
