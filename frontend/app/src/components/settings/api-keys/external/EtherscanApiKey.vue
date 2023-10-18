<script setup lang="ts">
const props = defineProps<{ evmChain: string; chainName: string }>();
const { evmChain } = toRefs(props);

const name = 'etherscan';
const { t } = useI18n();

const { loading, apiKey, actionStatus, save, confirmDelete, getName } =
  useExternalApiKeys(t);

const key = apiKey(name, evmChain);
const status = actionStatus(name, evmChain);
const identifier = computed(() => getName(name, get(evmChain)));

const { remove: removeNotification, prioritized } = useNotificationsStore();

/**
 * After an api key is added, remove the etherscan notification for that location
 */
const removeEtherscanNotification = () => {
  // using prioritized list here, because the actionable notifications are always on top (index 0|1)
  // so it is faster to find
  const notification = prioritized.find(
    data => data.i18nParam?.props?.key === get(evmChain)
  );

  if (!notification) {
    return;
  }

  removeNotification(notification.id);
};
</script>

<template>
  <ServiceKey
    :api-key="key"
    :name="identifier"
    :data-cy="identifier"
    :label="t('external_services.etherscan.label')"
    :hint="
      t('external_services.etherscan.hint', {
        chain: chainName
      })
    "
    :loading="loading"
    :tooltip="
      t('external_services.etherscan.delete_tooltip', {
        chain: chainName
      })
    "
    :status="status"
    @save="save($event)"
    @delete-key="confirmDelete($event, removeEtherscanNotification)"
  />
</template>
