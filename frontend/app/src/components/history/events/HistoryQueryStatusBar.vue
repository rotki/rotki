<script setup lang="ts">
defineProps<{
  colspan: number;
  finished: boolean;
  decoding: boolean;
  total: number;
}>();

const emit = defineEmits<{ (e: 'reset'): void }>();
</script>

<template>
  <tr
    v-if="total > 0 || decoding"
    class="!bg-black/[0.04] dark:!bg-white/[0.04]"
  >
    <td :colspan="colspan">
      <div class="flex items-start gap-3">
        <div class="py-2 flex items-center gap-3">
          <div class="flex">
            <RuiProgress
              v-if="!finished"
              size="20"
              thickness="2"
              variant="indeterminate"
              circular
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
          class="mt-0.5"
          size="sm"
          icon
          variant="text"
          @click="emit('reset')"
        >
          <RuiIcon name="close-line" />
        </RuiButton>
      </div>
    </td>
  </tr>
</template>
