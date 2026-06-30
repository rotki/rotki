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
const displayRouter = logicAnd(connected, logicNot(showDockerWarning), logicNot(restarting));
</script>

<template>
  <ConnectionLoading
    v-if="!connectionFailure"
    :connected="connected && !autolog"
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
    v-else-if="connected"
    class="w-full h-full flex flex-col gap-4 items-center justify-center"
  >
    <RuiProgress
      thickness="2"
      color="primary"
      variant="indeterminate"
      circular
    />
    <p
      v-if="restarting"
      class="mb-0 text-rui-text-secondary"
    >
      {{ t('connection_loading.restarting') }}
    </p>
  </div>
</template>
