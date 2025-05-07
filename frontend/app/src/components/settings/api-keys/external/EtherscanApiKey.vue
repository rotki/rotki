<script setup lang="ts">
import ExternalLink from '@/components/helper/ExternalLink.vue';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';
import ServiceKeyCard from '@/components/settings/api-keys/ServiceKeyCard.vue';
import { useExternalApiKeys, useServiceKeyHandler } from '@/composables/settings/api-keys/external';
import { useNotificationsStore } from '@/store/notifications';
import { NotificationCategory } from '@rotki/common';
import { etherscanLink } from '@shared/external-links';

const name = 'etherscan';
const { t } = useI18n({ useScope: 'global' });

const { actionStatus, apiKey, confirmDelete, loading, save } = useExternalApiKeys(t);
const { saveHandler, serviceKeyRef } = useServiceKeyHandler<InstanceType<typeof ServiceKey>>();

const key = apiKey(name);
const status = actionStatus(name);

const { prioritized, remove: removeNotification } = useNotificationsStore();

/**
 * After an api key is added, remove the etherscan notification for that location
 */
function removeEtherscanNotification() {
  // using prioritized list here, because the actionable notifications are always on top (index 0|1)
  // so it is faster to find
  const notifications = prioritized.filter(data => data.category === NotificationCategory.ETHERSCAN);

  notifications.forEach((notification) => {
    removeNotification(notification.id);
  });
}
</script>

<template>
  <ServiceKeyCard
    :name="name"
    :key-set="!!key"
    data-cy="etherscan-api-keys"
    :title="t('external_services.etherscan.title')"
    :subtitle="t('external_services.etherscan.description')"
    image-src="./assets/images/services/etherscan.svg"
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
        data-cy="delete-button"
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
      :hint="t('external_services.etherscan.hint')"
      :loading="loading"
      :status="status"
      @save="save($event, removeEtherscanNotification)"
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
            :url="etherscanLink"
          >
            {{ t('common.here') }}
          </ExternalLink>
        </template>
      </i18n-t>
    </ServiceKey>
  </ServiceKeyCard>
</template>
