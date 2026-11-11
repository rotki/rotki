<script setup lang="ts">
import type { RuiAutoComplete } from '@rotki/ui-library';

import type { ForwardedProps } from '@/modules/core/common/forwarded-props';

interface Props {
  items: string[];
  /** Shows the clear button; clearing writes `''`, so the model stays a `string`. */
  clearable?: boolean;
}

defineOptions({
  inheritAttrs: false,
});

const model = defineModel<string, 'trim'>({ required: true });

const { clearable = false, items } = defineProps<Props & /* @vue-ignore */ ForwardedProps<typeof RuiAutoComplete<string, string>, Props>>();

const search = ref<string>('');

watch(search, (search) => {
  if (search === undefined)
    search = '';

  set(model, search);
});
</script>

<template>
  <RuiAutoComplete
    v-model="model"
    v-bind="$attrs"
    v-model:search-input="search"
    :options="items"
    :clearable="clearable"
    value-on-clear=""
    custom-value
  >
    <template
      v-for="(_, name, index) in ($slots as {})"
      #[name]="scope"
      :key="index"
    >
      <slot
        v-bind="{ scope }"
        :name="name"
      />
    </template>
  </RuiAutoComplete>
</template>
