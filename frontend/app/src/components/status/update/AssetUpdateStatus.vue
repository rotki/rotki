<script setup lang="ts">
const props = defineProps<{
  status: 'checking' | 'applying';
  remoteVersion: number;
}>();

const { status, remoteVersion } = toRefs(props);

const { t } = useI18n();

const title = computed(() => {
  const updateStatus = get(status);

  if (updateStatus === 'checking') {
    return t('asset_update_status.checking.title');
  }
  return t('asset_update_status.applying.title');
});

const message = computed(() => {
  const updateStatus = get(status);

  if (updateStatus === 'checking') {
    return t('asset_update_status.checking.message');
  }
  return t('asset_update_status.applying.message', {
    remoteVersion: get(remoteVersion)
  });
});
</script>

<template>
  <Card flat>
    <template #title>{{ title }}</template>
    <div class="my-6 text-body-1">
      <VRow align="center">
        <VCol cols="auto" class="mx-2">
          <VProgressCircular color="primary" indeterminate class="mx-auto" />
        </VCol>
        <VCol>
          {{ message }}
        </VCol>
      </VRow>
    </div>
  </Card>
</template>
