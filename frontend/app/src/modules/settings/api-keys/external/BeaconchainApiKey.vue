<script setup lang="ts">
import { NotificationCategory } from '@rotki/common';
import { getPublicServiceImagePath } from '@/modules/core/common/file/file';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import { useServiceKeyHandler } from '@/modules/settings/api-keys/external/use-service-key-handler';
import { useServiceKeyNotifications } from '@/modules/settings/api-keys/external/use-service-key-notifications';
import ServiceKey from '@/modules/settings/api-keys/ServiceKey.vue';
import ServiceKeyCard from '@/modules/settings/api-keys/ServiceKeyCard.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const name = 'beaconchain';
const { t } = useI18n({ useScope: 'global' });

const { actionStatus, useApiKey, confirmDelete, loading, save } = useExternalApiKeys();
const { saveHandler, serviceKeyRef } = useServiceKeyHandler<InstanceType<typeof ServiceKey>>();

const key = useApiKey(name);
const status = actionStatus(name);

const { dismissCategory } = useServiceKeyNotifications();

function dismissKeyRequest(): void {
  dismissCategory(NotificationCategory.BEACONCHAIN);
}
</script>

<template>
  <ServiceKeyCard
    rounded-icon
    :name="name"
    :key-set="!!key"
    :title="t('external_services.beaconchain.title')"
    :subtitle="t('external_services.beaconchain.description')"
    :image-src="getPublicServiceImagePath('beaconchain.svg')"
    :action="{ disabled: !serviceKeyRef?.currentValue }"
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
        {{ t('external_services.actions.delete_key') }}
      </RuiButton>
    </template>
    <ServiceKey
      ref="serviceKeyRef"
      hide-actions
      :api-key="key"
      :name="name"
      :data-testid="name"
      :label="t('external_services.api_key')"
      :hint="t('external_services.beaconchain.hint')"
      :loading="loading"
      :status="status"
      @save="save($event, dismissKeyRequest)"
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
            url="https://beaconcha.in/user/settings"
          >
            {{ t('common.here') }}
          </ExternalLink>
        </template>
      </i18n-t>
    </ServiceKey>
  </ServiceKeyCard>
</template>
