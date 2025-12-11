<script setup lang="ts">
import SuccessDisplay from '@/components/display/SuccessDisplay.vue';

defineProps<{
  colspan: number;
  finished: boolean;
}>();

const emit = defineEmits<{ reset: [] }>();
</script>

<template>
  <tr class="!bg-black/[0.04] dark:!bg-white/[0.04]">
    <td
      :colspan="colspan"
      class="px-4"
    >
      <div class="flex items-start gap-3">
        <div class="py-2 flex items-center gap-3">
          <div class="flex">
            <RuiProgress
              v-if="!finished"
              size="20"
              thickness="2"
              variant="indeterminate"
              circular
              color="primary"
            />

            <SuccessDisplay
              v-else
              size="20"
              success
            />
          </div>

          <div class="font-medium">
            <slot name="current" />
          </div>
        </div>
        <div class="grow" />
        <slot name="dialog" />
        <RuiButton
          v-if="finished"
          class="mt-1"
          size="sm"
          icon
          variant="text"
          @click="emit('reset')"
        >
          <RuiIcon name="lu-x" />
        </RuiButton>
      </div>
    </td>
  </tr>
</template>
