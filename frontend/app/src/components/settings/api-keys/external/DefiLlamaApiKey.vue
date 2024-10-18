<script setup lang="ts">
const name = 'defillama';

const { t } = useI18n();

const { loading, apiKey, actionStatus, save, confirmDelete } = useExternalApiKeys(t);

const key = apiKey(name);
const status = actionStatus(name);

const link = externalLinks.defillamaApiKey;
</script>

<template>
  <RuiCard id="defillama-api-key">
    <template #header>
      {{ t('external_services.defillama.title') }}
    </template>
    <template #subheader>
      {{ t('external_services.defillama.description') }}
    </template>
    <ServiceKey
      :api-key="key"
      :name="name"
      :data-cy="name"
      :label="t('external_services.api_key')"
      :hint="t('external_services.defillama.hint')"
      :loading="loading"
      :tooltip="t('external_services.defillama.delete_tooltip')"
      :status="status"
      @save="save($event)"
      @delete-key="confirmDelete($event)"
    >
      <i18n-t
        v-if="link"
        tag="div"
        class="text-rui-text-secondary text-body-2"
        keypath="external_services.get_api_key"
      >
        <template #link>
          <ExternalLink
            color="primary"
            :url="link"
          >
            {{ t('common.here') }}
          </ExternalLink>
        </template>
      </i18n-t>
    </ServiceKey>
  </RuiCard>
</template>
