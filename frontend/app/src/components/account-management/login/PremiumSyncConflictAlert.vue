<script setup lang="ts">
const emit = defineEmits<{ (e: 'proceed', approval: 'yes' | 'no'): void }>();

const { t } = useI18n();

const { syncConflict } = storeToRefs(useSessionAuthStore());

const lastModified = useRefMap(syncConflict, conflict => {
  if (!conflict || !conflict.payload) {
    return null;
  }
  const { localLastModified, remoteLastModified } = conflict.payload;
  return {
    remote: remoteLastModified,
    local: localLastModified
  };
});
</script>

<template>
  <Transition name="bounce">
    <LoginActionAlert
      v-if="syncConflict"
      icon="mdi-cloud-download"
      @cancel="emit('proceed', 'no')"
      @confirm="emit('proceed', 'yes')"
    >
      <template #title>{{ t('login.sync_error.title') }}</template>

      <div>{{ syncConflict.message }}</div>
      <ul v-if="lastModified" class="mt-2">
        <li>
          <I18n path="login.sync_error.local_modified">
            <div class="font-weight-medium">
              <DateDisplay :timestamp="lastModified.local" />
            </div>
          </I18n>
        </li>
        <li class="mt-2">
          <I18n path="login.sync_error.remote_modified">
            <div class="font-weight-medium">
              <DateDisplay :timestamp="lastModified.remote" />
            </div>
          </I18n>
        </li>
      </ul>
      <div class="mt-2">{{ t('login.sync_error.question') }}</div>
    </LoginActionAlert>
  </Transition>
</template>
