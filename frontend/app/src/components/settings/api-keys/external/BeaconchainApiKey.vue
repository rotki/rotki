<script setup lang="ts">
const name = 'beaconchain';

const { t } = useI18n();

const { loading, apiKey, actionStatus, save, confirmDelete } =
  useExternalApiKeys(t);

const key = apiKey(name);
const status = actionStatus(name);
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('external_services.beaconchain.title') }}
    </template>
    <template #subheader>
      {{ t('external_services.beaconchain.description') }}
    </template>

    <ServiceKey
      :api-key="key"
      :name="name"
      :data-cy="name"
      :label="t('external_services.api_key')"
      :hint="t('external_services.beaconchain.hint')"
      :loading="loading"
      :tooltip="t('external_services.beaconchain.delete_tooltip')"
      :status="status"
      @save="save($event)"
      @delete-key="confirmDelete($event)"
    />
  </RuiCard>
</template>
