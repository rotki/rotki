<script setup lang="ts">
import { blockscoutLink } from '@shared/external-links';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';
import ServiceKeyCard from '@/components/settings/api-keys/ServiceKeyCard.vue';
import { useExternalApiKeys, useServiceKeyHandler } from '@/composables/settings/api-keys/external';
import { getPublicServiceImagePath } from '@/utils/file';

const name = 'blockscout';
const { t } = useI18n({ useScope: 'global' });

const { actionStatus, useApiKey, confirmDelete, loading, save } = useExternalApiKeys();
const { saveHandler, serviceKeyRef } = useServiceKeyHandler<InstanceType<typeof ServiceKey>>();

const key = useApiKey(name);
const status = actionStatus(name);
</script>

<template>
  <ServiceKeyCard
    :name="name"
    :key-set="!!key"
    :data-cy="`${name}-api-keys`"
    :title="t('external_services.blockscout.title')"
    :subtitle="t('external_services.blockscout.description')"
    :image-src="getPublicServiceImagePath('blockscout.svg')"
    :action-disabled="!serviceKeyRef?.currentValue"
    @confirm="saveHandler()"
  >
    <template #left-buttons>
      <RuiButton
        :disabled="loading || !key"
        color="error"
        variant="text"
        data-cy="delete-button"
        @click="confirmDelete(name)"
      >
        <template #prepend>
          <RuiIcon
            name="lu-trash-2"
            size="16"
          />
        </template>
        {{ t('external_services.actions.delete_key') }}
      </RuiButton>
    </template>

    <ServiceKey
      ref="serviceKeyRef"
      hide-actions
      :api-key="key"
      :name="name"
      :data-cy="name"
      :label="t('external_services.api_key')"
      :hint="t('external_services.blockscout.hint')"
      :loading="loading"
      :status="status"
      @save="save($event)"
    >
      <i18n-t
        scope="global"
        tag="div"
        class="text-rui-text-secondary text-body-2"
        keypath="external_services.get_api_key"
      >
        <template #link>
          <ExternalLink
            color="primary"
            :url="blockscoutLink"
          >
            {{ t('common.here') }}
          </ExternalLink>
        </template>
      </i18n-t>
    </ServiceKey>
  </ServiceKeyCard>
</template>
