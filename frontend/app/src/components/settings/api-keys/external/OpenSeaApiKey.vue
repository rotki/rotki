<script setup lang="ts">
import { externalLinks } from '@/data/external-links';

const { t } = useI18n();

const name = 'opensea';

const { loading, apiKey, actionStatus, save, confirmDelete }
  = useExternalApiKeys(t);

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
      :label="t('external_services.api_key')"
      :hint="t('external_services.opensea.hint')"
      :loading="loading"
      :tooltip="t('external_services.opensea.delete_tooltip')"
      :status="status"
      @save="save($event)"
      @delete-key="confirmDelete($event)"
    >
      <i18n-t
        tag="div"
        class="text-rui-text-secondary text-body-2"
        keypath="external_services.get_api_key"
      >
        <template #link>
          <ExternalLink
            color="primary"
            :url="externalLinks.openSeaApiKeyReference"
          >
            {{ t('common.here') }}
          </ExternalLink>
        </template>
      </i18n-t>
    </ServiceKey>
  </RuiCard>
</template>
