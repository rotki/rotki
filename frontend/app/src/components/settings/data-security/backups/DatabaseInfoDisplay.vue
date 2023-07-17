<script setup lang="ts">
import { type PropType } from 'vue';

interface UserDbInfo {
  version: string;
  size: string;
}

interface GlobalDbInfo {
  schema: string;
  assets: string;
}

defineProps({
  directory: {
    required: true,
    type: String
  },
  globalDb: {
    required: true,
    type: Object as PropType<GlobalDbInfo>
  },
  userDb: {
    required: true,
    type: Object as PropType<UserDbInfo>
  }
});

const { t } = useI18n();
</script>

<template>
  <Card>
    <template #title>{{ t('database_info_display.title') }}</template>

    <VRow>
      <VCol>
        <VRow>
          <VCol class="text-h6">
            {{ t('database_info_display.userdb') }}
          </VCol>
        </VRow>
        <VRow align="start" no-gutters class="mt-2">
          <VCol :class="$style.label" cols="auto">
            {{ t('database_info_display.directory') }}
          </VCol>
          <VCol>{{ directory }}</VCol>
        </VRow>
        <VRow align="start" no-gutters>
          <VCol :class="$style.label" cols="auto">
            {{ t('database_info_display.userdb_version') }}
          </VCol>
          <VCol>{{ userDb.version }}</VCol>
        </VRow>
        <VRow align="start" no-gutters>
          <VCol :class="$style.label" cols="auto">
            {{ t('database_info_display.userdb_size') }}
          </VCol>
          <VCol>{{ userDb.size }}</VCol>
        </VRow>
      </VCol>
      <VCol>
        <VRow>
          <VCol class="text-h6">
            {{ t('database_info_display.globaldb') }}
          </VCol>
        </VRow>
        <VRow align="start" no-gutters class="mt-2">
          <VCol :class="$style.label" cols="auto">
            {{ t('database_info_display.globaldb_schema') }}
          </VCol>
          <VCol>{{ globalDb.schema }}</VCol>
        </VRow>
        <VRow align="start" no-gutters>
          <VCol :class="$style.label" cols="auto">
            {{ t('database_info_display.globaldb_assets') }}
          </VCol>
          <VCol>{{ globalDb.assets }}</VCol>
        </VRow>
      </VCol>
    </VRow>
  </Card>
</template>

<style module lang="scss">
.label {
  font-weight: 600;
  margin-right: 8px;
  min-width: 150px;
}
</style>
