<script setup lang="ts">
import type { UnderlyingToken } from '@rotki/common';
import AssetConflictValue from '@/modules/shell/app/AssetConflictValue.vue';

defineProps<{
  field: string;
  value?: string | number | boolean | null | UnderlyingToken[];
  diff: boolean;
}>();
</script>

<template>
  <div class="my-2 flex">
    <div class="font-medium">
      {{ field }}:
    </div>
    <div
      class="ml-4"
      :class="diff ? 'font-bold text-rui-error' : null"
    >
      <AssetConflictValue
        :field="field"
        :value="value"
      />
    </div>
  </div>
</template>
