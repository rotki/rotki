<script setup lang="ts">
import type { ExternalApiKeyService } from '@/modules/settings/api-keys/external/external-api-key-services';
import { getPublicServiceImagePath } from '@/modules/core/common/file/file';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import { useServiceKeyHandler } from '@/modules/settings/api-keys/external/use-service-key-handler';
import ServiceKey from '@/modules/settings/api-keys/ServiceKey.vue';
import ServiceKeyCard from '@/modules/settings/api-keys/ServiceKeyCard.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const { service } = defineProps<{
  service: ExternalApiKeyService;
}>();

const { t } = useI18n({ useScope: 'global' });

const { actionStatus, useApiKey, confirmDelete, loading, save } = useExternalApiKeys();
const { saveHandler, serviceKeyRef } = useServiceKeyHandler<InstanceType<typeof ServiceKey>>();

const key = useApiKey(() => service.name);
const status = actionStatus(() => service.name);
</script>

<template>
  <ServiceKeyCard
    :name="service.name"
    :key-set="!!key"
    :data-testid="`${service.name}-api-keys`"
    :title="t(service.title)"
    :subtitle="t(service.description)"
    :image-src="getPublicServiceImagePath(service.image)"
    :rounded-icon="service.roundedIcon"
    :action="{ disabled: !serviceKeyRef?.currentValue }"
    @confirm="saveHandler()"
  >
    <template #left-buttons>
      <RuiButton
        :disabled="loading || !key"
        color="error"
        variant="text"
        data-testid="delete-button"
        @click="confirmDelete(service.name)"
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
      :name="service.name"
      :data-testid="service.name"
      :label="t('external_services.api_key')"
      :hint="t(service.hint)"
      :loading="loading"
      :status="status"
      @save="save($event)"
    >
      <i18n-t
        v-if="service.link"
        scope="global"
        tag="div"
        class="text-rui-text-secondary text-body-2"
        keypath="external_services.get_api_key"
      >
        <template #link>
          <ExternalLink
            color="primary"
            :url="service.link"
          >
            {{ t('common.here') }}
          </ExternalLink>
        </template>
      </i18n-t>
    </ServiceKey>
  </ServiceKeyCard>
</template>
