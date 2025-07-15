<script setup lang="ts">
import { blockscoutLinks } from '@shared/external-links';
import { camelCase } from 'es-toolkit';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';
import { useExternalApiKeys } from '@/composables/settings/api-keys/external';
import { useNotificationsStore } from '@/store/notifications';
import { isBlockscoutKey } from '@/types/external';

const props = defineProps<{ evmChain: string; chainName: string }>();
const { evmChain } = toRefs(props);

const name = 'blockscout';
const { t } = useI18n({ useScope: 'global' });

const { actionStatus, apiKey, confirmDelete, getName, loading, save } = useExternalApiKeys(t);

const key = apiKey(name, evmChain);
const status = actionStatus(name, evmChain);
const identifier = computed(() => getName(name, get(evmChain)));

const { prioritized, remove: removeNotification } = useNotificationsStore();

function removeBlockscoutNotification() {
  const notification = prioritized.find(data => data.i18nParam?.props?.key === get(evmChain));

  if (!notification)
    return;

  removeNotification(notification.id);
}

const link = computed(() => {
  const location = camelCase(get(evmChain));
  if (isBlockscoutKey(location))
    return blockscoutLinks[location];

  return undefined;
});
</script>

<template>
  <ServiceKey
    :api-key="key"
    :name="identifier"
    :data-cy="identifier"
    :label="t('external_services.api_key')"
    :hint="
      t('external_services.blockscout.hint', {
        chain: chainName,
      })
    "
    :loading="loading"
    :tooltip="
      t('external_services.blockscout.delete_tooltip', {
        chain: chainName,
      })
    "
    :status="status"
    class="pt-2"
    @save="save($event, removeBlockscoutNotification)"
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
</template>
