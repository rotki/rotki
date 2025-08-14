<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';
import ServiceKeyCard from '@/components/settings/api-keys/ServiceKeyCard.vue';
import { useExternalApiKeys, useServiceKeyHandler } from '@/composables/settings/api-keys/external';

const name = 'coingecko';

const { t } = useI18n({ useScope: 'global' });

const { actionStatus, apiKey, confirmDelete, loading, save } = useExternalApiKeys(t);
const { saveHandler, serviceKeyRef } = useServiceKeyHandler<InstanceType<typeof ServiceKey>>();

const key = apiKey(name);
const status = actionStatus(name);

const link = externalLinks.coingeckoApiKey;
</script>

<template>
  <ServiceKeyCard
    :key-set="!!key"
    :title="t('external_services.coingecko.title')"
    :subtitle="t('external_services.coingecko.description')"
    image-src="./assets/images/services/coingecko.svg"
    :primary-action="key
      ? t('external_services.replace_key')
      : t('external_services.save_key')"
    :action-disabled="!serviceKeyRef?.currentValue"
    @confirm="saveHandler()"
  >
    <template #left-buttons>
      <RuiButton
        :disabled="loading || !key"
        color="error"
        variant="text"
        @click="confirmDelete(name)"
      >
        <template #prepend>
          <RuiIcon
            name="lu-trash-2"
            size="16"
          />
        </template>
        {{ t('external_services.delete_key') }}
      </RuiButton>
    </template>
    <ServiceKey
      ref="serviceKeyRef"
      hide-actions
      :api-key="key"
      :name="name"
      :data-cy="name"
      :label="t('external_services.api_key')"
      :hint="t('external_services.coingecko.hint')"
      :loading="loading"
      :status="status"
      @save="save($event)"
      @delete-key="confirmDelete($event)"
    >
      <i18n-t
        v-if="link"
        scope="global"
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
  </ServiceKeyCard>
</template>
