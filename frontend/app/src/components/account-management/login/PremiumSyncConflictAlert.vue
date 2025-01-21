<script setup lang="ts">
import { useSessionAuthStore } from '@/store/session/auth';
import { useRefMap } from '@/composables/utils/useRefMap';
import DateDisplay from '@/components/display/DateDisplay.vue';
import LoginActionAlert from '@/components/account-management/login/LoginActionAlert.vue';

const emit = defineEmits<{ (e: 'proceed', approval: 'yes' | 'no'): void }>();

const { t } = useI18n();

const { syncConflict } = storeToRefs(useSessionAuthStore());

const lastModified = useRefMap(syncConflict, (conflict) => {
  if (!conflict || !conflict.payload)
    return null;

  const { localLastModified, remoteLastModified } = conflict.payload;
  return {
    local: localLastModified,
    remote: remoteLastModified,
  };
});
</script>

<template>
  <Transition name="bounce">
    <LoginActionAlert
      v-if="syncConflict"
      icon="lu-cloud-download-fill"
      @cancel="emit('proceed', 'no')"
      @confirm="emit('proceed', 'yes')"
    >
      <template #title>
        {{ t('login.sync_error.title') }}
      </template>

      <div>{{ syncConflict.message }}</div>
      <ul
        v-if="lastModified"
        class="mt-2 list-disc"
      >
        <li>
          <i18n-t
            keypath="login.sync_error.local_modified"
            class="font-medium"
          >
            <DateDisplay :timestamp="lastModified.local" />
          </i18n-t>
        </li>
        <li class="mt-2">
          <i18n-t
            keypath="login.sync_error.remote_modified"
            class="font-medium"
          >
            <DateDisplay :timestamp="lastModified.remote" />
          </i18n-t>
        </li>
      </ul>
      <div class="mt-2">
        {{ t('login.sync_error.question') }}
      </div>
    </LoginActionAlert>
  </Transition>
</template>
