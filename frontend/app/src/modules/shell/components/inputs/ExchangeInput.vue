<script lang="ts" setup>
import type { RuiAutoComplete } from '@rotki/ui-library';
import type { ForwardedProps } from '@/modules/core/common/forwarded-props';

import { useLocationStore } from '@/modules/core/common/use-location-store';
import ExchangeDisplay from '@/modules/shell/components/display/ExchangeDisplay.vue';

interface Props {
  dense?: boolean;
  showWithKeyOnly?: boolean;
  excludes?: string[];
}

defineOptions({
  inheritAttrs: false,
});

const model = defineModel<string | undefined>({ required: true });

const { showWithKeyOnly, excludes = [] } = defineProps<Props & /* @vue-ignore */ ForwardedProps<typeof RuiAutoComplete, Props>>();

const { allExchanges, exchangesWithKey } = storeToRefs(useLocationStore());

const options = computed<string[]>(() => {
  const exchanges = get(showWithKeyOnly ? exchangesWithKey : allExchanges);
  return exchanges.filter(exchange => !excludes.includes(exchange));
});
</script>

<template>
  <RuiAutoComplete
    v-model="model"
    v-bind="$attrs"
    :options="options"
    :dense="dense"
    :item-height="52"
    auto-select-first
  >
    <template #selection="{ item }">
      <ExchangeDisplay :exchange="item" />
    </template>
    <template #item="{ item }">
      <ExchangeDisplay
        :exchange="item"
        :class="dense && 'py-2'"
      />
    </template>
  </RuiAutoComplete>
</template>
