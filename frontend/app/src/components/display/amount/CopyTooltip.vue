<script setup lang="ts">
defineProps<{
  value: string;
  copied: boolean;
  tooltip?: string | null;
}>();
const css = useCssModule();
const { t } = useI18n();
</script>

<template>
  <VTooltip top open-delay="200ms">
    <template #activator="{ on, attrs }">
      <span
        data-cy="display-amount"
        class="text-no-wrap"
        v-bind="attrs"
        v-on="on"
      >
        {{ value }}
      </span>
    </template>
    <div class="text-center">
      <div v-if="tooltip" data-cy="display-full-value">
        {{ tooltip }}
      </div>
      <div :class="css.copy">
        <div
          class="text-uppercase font-weight-bold text-caption"
          :class="{
            [css['copy__wrapper']]: true,
            [css['copy__wrapper--copied']]: copied
          }"
        >
          <div>
            {{ t('amount_display.click_to_copy') }}
          </div>
          <div class="green--text text--lighten-2">
            {{ t('amount_display.copied') }}
          </div>
        </div>
      </div>
    </div>
  </VTooltip>
</template>

<style module lang="scss">
.copy {
  height: 20px;
  overflow: hidden;

  &__wrapper {
    transition: 0.2s all;

    &--copied {
      margin-top: -20px;
    }
  }
}
</style>
