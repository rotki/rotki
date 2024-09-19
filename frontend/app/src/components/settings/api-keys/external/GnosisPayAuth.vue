<script setup lang="ts">
const { t } = useI18n();
const understand = ref<boolean>(false);
const name = 'gnosis_pay';
const { loading, apiKey, actionStatus, save, confirmDelete } = useExternalApiKeys(t);
const key = apiKey(name);
const status = actionStatus(name);
watchImmediate(key, (value) => {
  if (value)
    set(understand, true);
});
const premium = usePremium();
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('external_services.gnosispay.title') }}
    </template>
    <template #subheader>
      {{ t('external_services.gnosispay.description') }}
    </template>
    <template v-if="premium">
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
        :api-key="key"
        :name="name"
        :data-cy="name"
        :loading="loading"
        :tooltip="t('external_services.gnosispay.delete_tooltip')"
        :status="status"
        :label="t('external_services.gnosispay.api_key_label')"
        :hint="t('external_services.gnosispay.api_key_hint')"
        @save="save($event)"
        @delete-key="confirmDelete($event)"
      >
        <p class="text-sm text-gray-600 mt-2">
          {{ t('external_services.gnosispay.session_token_instructions') }}
        </p>
      </ServiceKey>
    </template>
    <template v-else>
      <div class="flex items-center gap-2 text-body-2">
        <PremiumLock />
        {{ t('external_services.gnosispay.non_premium') }}
      </div>
    </template>
  </RuiCard>
</template>
