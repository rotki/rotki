<script setup lang="ts">
const { remoteVersion, status } = defineProps<{
  status: 'checking' | 'applying';
  remoteVersion: number;
}>();

const { t } = useI18n({ useScope: 'global' });

const title = computed(() => {
  if (status === 'checking')
    return t('asset_update_status.checking.title');

  return t('asset_update_status.applying.title');
});

const message = computed(() => {
  if (status === 'checking')
    return t('asset_update_status.checking.message');

  return t('asset_update_status.applying.message', {
    remoteVersion,
  });
});
</script>

<template>
  <RuiCard
    variant="flat"
    class="max-w-[27.5rem] mx-auto !bg-transparent"
  >
    <template #header>
      {{ title }}
    </template>
    <div class="flex items-center space-x-10">
      <RuiProgress
        color="primary"
        variant="indeterminate"
        circular
      />
      <p class="mb-0 text-rui-text-secondary">
        {{ message }}
      </p>
    </div>
  </RuiCard>
</template>
