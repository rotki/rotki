<script setup lang="ts">
defineSlots<{
  default: (props: { copyright: string }) => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const copyright = computed<string>(() => t('app.copyright', { year: new Date().getFullYear() }));
</script>

<template>
  <div class="font-normal text-sm leading-6 text-rui-text-secondary tracking-[0.025rem]">
    <slot :copyright="copyright" />
  </div>
</template>
