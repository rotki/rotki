<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import { useExternalApiKeys, useServiceKeyHandler } from '@/composables/settings/api-keys/external';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import ServiceKeyCard from '@/components/settings/api-keys/ServiceKeyCard.vue';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';

const { t } = useI18n();

const understand = ref<boolean>(false);

const name = 'gnosis_pay';
const { actionStatus, apiKey, confirmDelete, loading, save } = useExternalApiKeys(t);
const { saveHandler, serviceKeyRef } = useServiceKeyHandler<InstanceType<typeof ServiceKey>>();

const key = apiKey(name);
const status = actionStatus(name);

const link = externalLinks.usageGuideSection.gnosisPayKey;

watchImmediate(key, (value) => {
  if (value)
    set(understand, true);
});
</script>

<template>
  <ServiceKeyCard
    need-premium
    rounded-icon
    :name="name"
    :key-set="!!key"
    :title="t('external_services.gnosispay.title')"
    :subtitle="t('external_services.gnosispay.description')"
    image-src="./assets/images/services/gnosispay.png"
    :primary-action="key
      ? t('external_services.replace_key')
      : t('external_services.save_key')"
    :action-disabled="!serviceKeyRef?.currentValue"
    @confirm="saveHandler()"
  >
    <template
      v-if="understand"
      #left-buttons
    >
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
    <RuiAlert
      type="warning"
      class="mb-6"
    >
      {{ t('external_services.gnosispay.warning') }}
      <RuiButton
        v-if="!understand"
        color="secondary"
        class="mt-2"
        size="sm"
        @click="understand = true"
      >
        {{ t('external_services.gnosispay.understand') }}
      </RuiButton>
    </RuiAlert>
    <ServiceKey
      v-if="understand"
      ref="serviceKeyRef"
      hide-actions
      :api-key="key"
      :name="name"
      :data-cy="name"
      :loading="loading"
      :status="status"
      :label="t('external_services.gnosispay.api_key_label')"
      :hint="t('external_services.gnosispay.api_key_hint')"
      @save="save($event)"
    >
      <i18n-t
        tag="div"
        class="text-rui-text-secondary text-body-2"
        keypath="external_services.gnosispay.session_token_instructions"
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
