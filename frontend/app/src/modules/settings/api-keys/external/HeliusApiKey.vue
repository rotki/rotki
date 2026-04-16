<script setup lang="ts">
import { NotificationCategory } from '@rotki/common';
import { heliusLink } from '@shared/external-links';
import { getPublicServiceImagePath } from '@/modules/core/common/file/file';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import { useServiceKeyHandler } from '@/modules/settings/api-keys/external/use-service-key-handler';
import ServiceKey from '@/modules/settings/api-keys/ServiceKey.vue';
import ServiceKeyCard from '@/modules/settings/api-keys/ServiceKeyCard.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const name = 'helius';
const { t } = useI18n({ useScope: 'global' });

const { actionStatus, useApiKey, confirmDelete, loading, save } = useExternalApiKeys();
const { saveHandler, serviceKeyRef } = useServiceKeyHandler<InstanceType<typeof ServiceKey>>();

const key = useApiKey(name);
const status = actionStatus(name);

const { prioritized, remove: removeNotification } = useNotificationsStore();

/**
 * After an api key is added, remove the helius notification
 */
function removeHeliusNotification() {
  // using prioritized list here, because the actionable notifications are always on top (index 0|1)
  // so it is faster to find
  const notifications = prioritized.filter(data => data.category === NotificationCategory.HELIUS);

  notifications.forEach((notification) => {
    removeNotification(notification.id);
  });
}
</script>

<template>
  <ServiceKeyCard
    :name="name"
    :key-set="!!key"
    data-cy="helius-api-keys"
    :title="t('external_services.helius.title')"
    :subtitle="t('external_services.helius.description')"
    :image-src="getPublicServiceImagePath('helius.svg')"
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
      :hint="t('external_services.helius.hint')"
      :loading="loading"
      :status="status"
      @save="save($event, removeHeliusNotification)"
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
            :url="heliusLink"
          >
            {{ t('common.here') }}
          </ExternalLink>
        </template>
      </i18n-t>
    </ServiceKey>
  </ServiceKeyCard>
</template>
