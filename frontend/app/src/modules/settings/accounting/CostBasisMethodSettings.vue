<script setup lang="ts">
import type { RuiMenuSelect } from '@rotki/ui-library';
import type { ForwardedProps } from '@/modules/core/common/forwarded-props';
import type { CostBasisMethod } from '@/modules/settings/types/user-settings';

import { useCostBasisMethod } from '@/modules/reports/use-reports';
import ListItem from '@/modules/shell/components/ListItem.vue';

interface Props {
  label: string;
  successMessages: string[];
  errorMessages: string[];
}

defineOptions({
  inheritAttrs: false,
});

const modelValue = defineModel<CostBasisMethod>({ required: true });

defineProps<Props & /* @vue-ignore */ ForwardedProps<typeof RuiMenuSelect, Props>>();

const { costBasisMethodData } = useCostBasisMethod();
</script>

<template>
  <RuiMenuSelect
    v-bind="$attrs"
    v-model="modelValue"
    :label="label"
    :success-messages="successMessages"
    :error-messages="errorMessages"
    :options="costBasisMethodData"
    key-attr="identifier"
  >
    <template #selection="{ item }">
      <span class="font-medium uppercase">{{ item.identifier }}</span>
    </template>
    <template #item="{ item }">
      <ListItem
        no-padding
        no-hover
        :title="item.identifier.toUpperCase()"
        :subtitle="item.label"
      />
    </template>
  </RuiMenuSelect>
</template>
