<script setup lang="ts">
const { t } = useI18n();

const understand: Ref<boolean> = ref(false);

const name = 'monerium';

const { loading, credential, actionStatus, save, confirmDelete }
  = useExternalApiKeys(t);

const credentialData = credential(name);
const status = actionStatus(name);

watchImmediate(credentialData, (credential) => {
  if (credential)
    set(understand, true);
});
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('external_services.monerium.title') }}
    </template>
    <template #subheader>
      {{ t('external_services.monerium.description') }}
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
      :credential="credentialData"
      :name="name"
      :data-cy="name"
      :loading="loading"
      :tooltip="t('external_services.monerium.delete_tooltip')"
      :status="status"
      @save="save($event)"
      @delete-key="confirmDelete($event)"
    />
  </RuiCard>
</template>
