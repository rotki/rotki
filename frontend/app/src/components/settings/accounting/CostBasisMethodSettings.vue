<script setup lang="ts">
import { useCostBasisMethod } from '@/composables/reports';
import ListItem from '@/components/common/ListItem.vue';
import type { CostBasisMethod } from '@/types/user';

defineOptions({
  inheritAttrs: false,
});

const modelValue = defineModel<CostBasisMethod>({ required: true });

defineProps<{
  label: string;
  successMessages: string[];
  errorMessages: string[];
}>();

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
    variant="outlined"
    key-attr="identifier"
  >
    <template #selection="{ item }">
      <span class="font-medium uppercase">{{ item.identifier }}</span>
    </template>
    <template #item="{ item }">
      <ListItem
        no-padding
        no-hover
        class="!py-0"
        :title="item.identifier.toUpperCase()"
        :subtitle="item.label"
      />
    </template>
  </RuiMenuSelect>
</template>
