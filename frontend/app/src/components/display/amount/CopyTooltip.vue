<script setup lang="ts">
defineProps<{
  copied: boolean;
  tooltip?: string | null;
}>();
const { t } = useI18n();
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top' }"
    :open-delay="200"
    class="text-no-wrap"
    data-cy="display-amount"
  >
    <template #activator>
      <slot />
    </template>

    <div class="text-center" data-cy="display-full-value">
      <template v-if="tooltip">
        {{ tooltip }}
      </template>
      <div
        class="text-uppercase font-bold text-caption overflow-hidden h-5 transition-all duration-200"
      >
        <div
          :class="{
            '-mt-5': copied
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
