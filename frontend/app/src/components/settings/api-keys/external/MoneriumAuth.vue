<script setup lang="ts">
const { t } = useI18n();

const understand = ref<boolean>(false);

const name = 'monerium';

const { loading, credential, actionStatus, save, confirmDelete } = useExternalApiKeys(t);

const credentialData = credential(name);
const status = actionStatus(name);

watchImmediate(credentialData, (credential) => {
  if (credential)
    set(understand, true);
});

const premium = usePremium();
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('external_services.monerium.title') }}
    </template>
    <template #subheader>
      {{ t('external_services.monerium.description') }}
    </template>
    <template v-if="premium">
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
    </template>
    <template v-else>
      <div class="flex items-center gap-2 text-body-2">
        <PremiumLock />
        {{ t('external_services.monerium.non_premium') }}
      </div>
    </template>
  </RuiCard>
</template>
