<script setup lang="ts">
import ConnectionFailureMessage from '@/modules/auth/ConnectionFailureMessage.vue';
import ConnectionLoading from '@/modules/auth/ConnectionLoading.vue';
import DockerWarning from '@/modules/auth/DockerWarning.vue';
import { useAutoLogin } from '@/modules/auth/use-auto-login';
import { useRestartingStatus } from '@/modules/auth/use-restarting-status';
import { useMainStore } from '@/modules/core/common/use-main-store';

defineSlots<{
  default: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });
const { autolog } = useAutoLogin();
const { restarting } = useRestartingStatus();

const { connected, connectionFailure, dockerRiskAccepted } = storeToRefs(useMainStore());

const isDocker = import.meta.env.VITE_DOCKER;
const showDockerWarning = logicAnd(isDocker, logicNot(dockerRiskAccepted));
// Hide the login form while an auto-unlock is running — the ConnectionLoading card is the
// single loading state for the whole attempt, so the empty form never shows behind it.
const displayRouter = logicAnd(connected, logicNot(autolog), logicNot(showDockerWarning), logicNot(restarting));
</script>

<template>
  <ConnectionLoading
    v-if="!connectionFailure"
    :connected="connected && !autolog"
    :logging-in="autolog"
    :restarting="restarting"
  />
  <ConnectionFailureMessage v-else />

  <div
    v-if="displayRouter"
    data-cy="account-management-forms"
    class="min-h-[150px]"
  >
    <slot />
  </div>

  <DockerWarning v-else-if="showDockerWarning" />
  <div
    v-else-if="connected && !autolog"
    class="max-w-[27.5rem] mx-auto flex flex-col gap-4 justify-center items-center py-12"
  >
    <RuiProgress
      color="primary"
      variant="indeterminate"
      circular
      size="48"
    />
    <p
      v-if="restarting"
      class="mb-0 text-rui-text-secondary text-center"
    >
      {{ t('connection_loading.restarting') }}
    </p>
  </div>
</template>
