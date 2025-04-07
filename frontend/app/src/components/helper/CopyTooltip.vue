<script setup lang="ts">
defineProps<{
  copied: boolean;
  tooltip?: string | null;
  disabled?: boolean;
}>();

defineSlots<{
  default: () => any;
  tooltip: () => any;
}>();

const { t } = useI18n();
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top' }"
    :open-delay="200"
    class="text-no-wrap"
    :class="{ 'cursor-pointer': !disabled }"
    :disabled="disabled"
  >
    <template #activator>
      <slot />
    </template>

    <div
      class="text-center"
      data-cy="display-full-value"
    >
      <slot name="tooltip">
        <div v-if="tooltip">
          {{ tooltip }}
        </div>
      </slot>
      <div class="uppercase font-bold text-caption overflow-hidden h-5 transition-all duration-200">
        <div
          :class="{
            '-mt-5': copied,
          }"
        >
          {{ t('amount_display.click_to_copy') }}
        </div>
        <div class="text-rui-success-lighter">
          {{ t('amount_display.copied') }}
        </div>
      </div>
    </div>
  </RuiTooltip>
</template>
