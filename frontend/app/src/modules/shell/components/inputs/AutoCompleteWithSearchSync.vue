<script setup lang="ts">
import type { ForwardedProps } from '@/modules/core/common/forwarded-props';
import { RuiAutoComplete } from '@rotki/ui-library';
import { set } from '@vueuse/shared';
import { ref, watch } from 'vue';

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
