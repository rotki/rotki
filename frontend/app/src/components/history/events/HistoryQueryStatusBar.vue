<script setup lang="ts">
defineProps<{
  colspan: number;
  finished: boolean;
  total: number;
}>();

const emit = defineEmits<{ (e: 'reset'): void }>();

const css = useCssModule();
</script>

<template>
  <tr
    v-if="total > 0"
    :class="css.tr"
    class="bg-[#d0d5dd] dark:bg-white/[0.09]"
  >
    <td :colspan="colspan">
      <div class="flex items-start gap-3">
        <div
          v-if="finished || (total > 1)"
          class="py-2 flex items-center gap-3"
        >
          <div class="flex">
            <RuiProgress
              v-if="!finished"
              color="secondary"
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

          <slot name="current" />
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

<style module lang="scss">
.tr {
  @apply bg-[#d0d5dd] dark:bg-white/[0.02];
}

.row {
  display: flex;
}
</style>
