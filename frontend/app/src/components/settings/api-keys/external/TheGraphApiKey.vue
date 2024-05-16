<script setup lang="ts">
import { externalLinks } from '@/data/external-links';

const name = 'thegraph';
const { t } = useI18n();

const { loading, apiKey, actionStatus, save, confirmDelete }
  = useExternalApiKeys(t);

const key = apiKey(name);
const status = actionStatus(name);

const { remove: removeNotification, prioritized } = useNotificationsStore();

/**
 * After an api key is added, remove thegraph notification
 */
function removeTheGraphNotification() {
  // using prioritized list here, because the actionable notifications are always on top (index 0|1)
  // so it is faster to find
  const notification = prioritized.find(
    data => data.i18nParam?.props?.service.toLowerCase() === name,
  );

  if (!notification)
    return;

  removeNotification(notification.id);
}

const link = externalLinks.applyTheGraphApiKey;
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('external_services.thegraph.title') }}
    </template>
    <template #subheader>
      {{ t('external_services.thegraph.description') }}
    </template>

    <ServiceKey
      :id="name"
      :api-key="key"
      :name="name"
      :data-cy="name"
      :label="t('external_services.api_key')"
      :hint="t('external_services.thegraph.hint')"
      :loading="loading"
      :tooltip="t('external_services.thegraph.delete_tooltip')"
      :status="status"
      @save="save($event, removeTheGraphNotification)"
      @delete-key="confirmDelete($event)"
    >
      <i18n
        v-if="link"
        tag="div"
        class="text-rui-text-secondary text-body-2"
        path="external_services.get_api_key"
      >
        <template #link>
          <ExternalLink
            color="primary"
            :url="link"
          >
            {{ t('common.here') }}
          </ExternalLink>
        </template>
      </i18n>
    </ServiceKey>
  </RuiCard>
</template>
