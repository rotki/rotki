<script setup lang="ts">
const css = useCssModule();

const { t } = useI18n();

const copyright = computed(() =>
  t('app.copyright', { year: new Date().getFullYear() })
);
</script>

<template>
  <div :class="css.text">
    <slot :copyright="copyright" />
  </div>
</template>

<style lang="scss" module>
.text {
  letter-spacing: 0.025rem;
  @apply font-normal text-sm leading-6 text-rui-text-secondary;
}
</style>
