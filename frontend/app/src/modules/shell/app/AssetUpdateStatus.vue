<script setup lang="ts">
const { remoteVersion, status } = defineProps<{
  status: 'checking' | 'applying';
  remoteVersion: number;
}>();

const { t } = useI18n({ useScope: 'global' });

const title = computed<string>(() => {
  if (status === 'checking')
    return t('asset_update_status.checking.title');

  return t('asset_update_status.applying.title');
});

const message = computed<string>(() => {
  if (status === 'checking')
    return t('asset_update_status.checking.message');

  return t('asset_update_status.applying.message', {
    remoteVersion,
  });
});
</script>

<template>
  <div class="max-w-[27.5rem] mx-auto flex flex-col items-center gap-4 py-12 text-center">
    <RuiProgress
      color="primary"
      variant="indeterminate"
      circular
      size="48"
    />
    <div>
      <h5 class="text-h6 mb-1">
        {{ title }}
      </h5>
      <p class="mb-0 text-rui-text-secondary">
        {{ message }}
      </p>
    </div>
  </div>
</template>
