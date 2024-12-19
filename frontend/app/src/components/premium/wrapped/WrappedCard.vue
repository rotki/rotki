<script setup lang="ts">
import WrappedItem from '@/components/premium/wrapped/WrappedItem.vue';

defineProps<{
  items: any[];
}>();
</script>

<template>
  <RuiCard
    no-padding
    variant="outlined"
    class="overflow-hidden"
    content-class="divide-y divide-rui-grey-300 dark:divide-rui-grey-800 bg-rui-grey-50 dark:bg-rui-grey-900"
  >
    <div class="flex px-4 py-3 gap-2 items-center bg-gradient-to-b from-transparent to-rui-primary/[0.05]">
      <div class="flex items-center justify-center size-6 shrink-0 bg-rui-primary-lighter/[0.2] dark:bg-rui-primary-darker/[0.2] rounded-full overflow-hidden">
        <slot name="header-icon" />
      </div>
      <h3 class="text-sm font-medium ">
        <slot name="header" />
      </h3>
    </div>
    <WrappedItem
      v-for="(item, index) in items"
      :key="index"
    >
      <template #label>
        <slot
          name="label"
          v-bind="{ item, index }"
        >
          {{ item.label }}
        </slot>
      </template>
      <template #value>
        <slot
          name="value"
          v-bind="{ item, index }"
        >
          {{ item.value }}
        </slot>
      </template>
    </WrappedItem>
  </RuiCard>
</template>
