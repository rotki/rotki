<script setup lang="ts">
defineProps<{ remoteVersion: number }>();

const emit = defineEmits<{ (e: 'confirm'): void }>();

const { t } = useI18n();
</script>

<template>
  <RuiCard variant="flat" class="bg-transparent">
    <template #header>
      {{ t('asset_update.success.title') }}
    </template>
    <div class="flex items-center gap-4">
      <SuccessDisplay size="32" success class="shrink-0" />

      {{ t('asset_update.success.description', { remoteVersion }) }}
    </div>
    <template #footer>
      <div class="grow" />
      <RuiButton color="primary" @click="emit('confirm')">
        {{ t('common.actions.ok') }}
      </RuiButton>
    </template>
  </RuiCard>
</template>
