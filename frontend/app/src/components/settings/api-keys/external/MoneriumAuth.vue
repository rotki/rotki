<script setup lang="ts">
import ServiceKeyCard from '@/components/settings/api-keys/ServiceKeyCard.vue';
import ServiceWithAuth from '@/components/settings/api-keys/ServiceWithAuth.vue';
import { useExternalApiKeys, useServiceKeyHandler } from '@/composables/settings/api-keys/external';

const { t } = useI18n({ useScope: 'global' });

const understand = ref<boolean>(false);

const name = 'monerium';

const { actionStatus, confirmDelete, credential, loading, save } = useExternalApiKeys(t);
const { saveHandler, serviceKeyRef } = useServiceKeyHandler<InstanceType<typeof ServiceWithAuth>>();

const credentialData = credential(name);
const status = actionStatus(name);

watchImmediate(credentialData, (credential) => {
  if (credential)
    set(understand, true);
});
</script>

<template>
  <ServiceKeyCard
    need-premium
    :key-set="!!credentialData"
    :title="t('external_services.monerium.title')"
    :subtitle="t('external_services.monerium.description')"
    image-src="./assets/images/services/monerium.png"
    :primary-action="serviceKeyRef?.editMode
      ? t('common.actions.save')
      : t('common.actions.edit')"
    :action-disabled="!serviceKeyRef?.allFilled"
    @confirm="saveHandler()"
  >
    <template #left-buttons>
      <RuiButton
        :disabled="loading || !credentialData"
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
      {{ t('external_services.monerium.warning') }}

      <RuiButton
        v-if="!understand"
        color="secondary"
        class="mt-2"
        size="sm"
        @click="understand = true"
      >
        {{ t('external_services.monerium.understand') }}
      </RuiButton>
    </RuiAlert>

    <ServiceWithAuth
      v-if="understand"
      ref="serviceKeyRef"
      hide-actions
      :credential="credentialData"
      :name="name"
      :data-cy="name"
      :loading="loading"
      :status="status"
      @save="save($event)"
      @delete-key="confirmDelete($event)"
    />
  </ServiceKeyCard>
</template>
