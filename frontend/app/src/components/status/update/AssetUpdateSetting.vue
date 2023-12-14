<script setup lang="ts">
defineProps<{
  skipped: number;
  loading: boolean;
}>();

const emit = defineEmits<{ (e: 'check'): void }>();
const { t } = useI18n();
</script>

<template>
  <RuiCard class="mt-8">
    <template #header>{{ t('asset_update.manual.title') }}</template>
    <template #subheader>{{ t('asset_update.manual.subtitle') }}</template>
    <i18n v-if="skipped" path="asset_update.manual.skipped">
      <template #skipped>
        <BadgeDisplay class="ml-2">{{ skipped }}</BadgeDisplay>
      </template>
    </i18n>
    <template #footer>
      <RuiButton color="primary" :loading="loading" @click="emit('check')">
        {{ t('asset_update.manual.check') }}
      </RuiButton>
    </template>
  </RuiCard>
</template>
