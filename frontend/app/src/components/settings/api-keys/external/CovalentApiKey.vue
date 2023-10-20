<script setup lang="ts">
const name = 'covalent';
const { t } = useI18n();

const { loading, apiKey, actionStatus, save, confirmDelete } =
  useExternalApiKeys(t);

const key = apiKey(name);
const status = actionStatus(name);
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('external_services.covalent.title') }}
    </template>
    <template #subheader>
      {{ t('external_services.covalent.description') }}
    </template>

    <ServiceKey
      :api-key="key"
      :name="name"
      :data-cy="name"
      :label="t('external_services.covalent.label')"
      :hint="t('external_services.covalent.hint')"
      :loading="loading"
      :tooltip="t('external_services.covalent.delete_tooltip')"
      :status="status"
      @save="save($event)"
      @delete-key="confirmDelete($event)"
    />
  </RuiCard>
</template>
