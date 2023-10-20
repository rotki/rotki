<script setup lang="ts">
const { t } = useI18n();

const name = 'opensea';

const { loading, apiKey, actionStatus, save, confirmDelete } =
  useExternalApiKeys(t);

const key = apiKey(name);
const status = actionStatus(name);
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('external_services.opensea.title') }}
    </template>
    <template #subheader>
      {{ t('external_services.opensea.description') }}
    </template>

    <ServiceKey
      :api-key="key"
      :name="name"
      :data-cy="name"
      :label="t('external_services.opensea.label')"
      :hint="t('external_services.opensea.hint')"
      :loading="loading"
      :tooltip="t('external_services.opensea.delete_tooltip')"
      :status="status"
      @save="save($event)"
      @delete-key="confirmDelete($event)"
    >
      <i18n tag="div" path="external_services.opensea.link">
        <template #link>
          <ExternalLink
            url="https://docs.opensea.io/reference/api-keys#how-do-i-get-an-api-key"
          >
            {{ t('common.here') }}
          </ExternalLink>
        </template>
      </i18n>
    </ServiceKey>
  </RuiCard>
</template>
