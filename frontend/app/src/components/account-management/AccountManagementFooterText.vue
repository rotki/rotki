<script setup lang="ts">
defineSlots<{
  default: (props: { copyright: string }) => any;
}>();

const { t } = useI18n();

const copyright = computed<string>(() => t('app.copyright', { year: new Date().getFullYear() }));
</script>

<template>
  <div :class="$style.text">
    <slot :copyright="copyright" />
  </div>
</template>

<style lang="scss" module>
.text {
  @apply font-normal text-sm leading-6 text-rui-text-secondary;
  letter-spacing: 0.025rem;
}
</style>
