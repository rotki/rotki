<script lang="ts" setup>
const props = withDefaults(
  defineProps<{
    value?: string | null;
    dense?: boolean;
    showWithKeyOnly?: boolean;
  }>(),
  {
    value: null,
    showWithKeyOnly: false,
  },
);

const emit = defineEmits<{
  (e: 'input', value: string): void;
}>();

const vModel = useSimpleVModel(props, emit);

const { allExchanges, exchangesWithKey } = storeToRefs(useLocationStore());

const rootAttrs = useAttrs();
</script>

<template>
  <RuiAutoComplete
    v-model="vModel"
    variant="outlined"
    v-bind="rootAttrs"
    :options="showWithKeyOnly ? exchangesWithKey : allExchanges"
    :dense="dense"
    :item-height="52"
    auto-select-first
    v-on="
      // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
      $listeners
    "
  >
    <template #selection="{ item }">
      <ExchangeDisplay
        :exchange="item"
        :class="`exchange__${item}`"
      />
    </template>
    <template #item="{ item }">
      <ExchangeDisplay
        :exchange="item"
        :class="[`exchange__${item}`, dense && 'py-2']"
      />
    </template>
  </RuiAutoComplete>
</template>
