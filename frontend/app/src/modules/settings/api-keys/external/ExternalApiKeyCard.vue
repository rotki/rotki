<script setup lang="ts">
import type { ExternalApiKeyService } from '@/modules/settings/api-keys/external/external-api-key-services';
import { getPublicServiceImagePath } from '@/modules/core/common/file/file';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import { useServiceKeyHandler } from '@/modules/settings/api-keys/external/use-service-key-handler';
import ServiceKey from '@/modules/settings/api-keys/ServiceKey.vue';
import ServiceKeyCard, { type ServiceKeyAction } from '@/modules/settings/api-keys/ServiceKeyCard.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const { service } = defineProps<{
  service: ExternalApiKeyService;
}>();

const { t } = useI18n({ useScope: 'global' });

const { actionStatus, useApiKey, confirmDelete, loading, save } = useExternalApiKeys();
const { saveHandler, serviceKeyRef } = useServiceKeyHandler<InstanceType<typeof ServiceKey>>();

const key = useApiKey(() => service.name);
const status = actionStatus(() => service.name);

// a computed rather than an inline object, so the card only re-renders when saving becomes possible
const action = computed<ServiceKeyAction>(() => ({ disabled: !get(serviceKeyRef)?.currentValue }));
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
    :action="action"
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
      <ExternalLink
        v-if="service.link"
        color="primary"
        class="inline-flex items-center gap-1 self-start text-sm"
        :url="service.link"
      >
        {{ t('external_services.get_key_from', { service: t(service.title) }) }}
        <RuiIcon
          name="lu-external-link"
          size="14"
        />
      </ExternalLink>
    </ServiceKey>
  </ServiceKeyCard>
</template>
