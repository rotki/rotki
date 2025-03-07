<script setup lang="ts">
import { useMainStore } from '@/store/main';
import { useAutoLogin, useRestartingStatus } from '@/composables/user/account';
import DockerWarning from '@/components/account-management/DockerWarning.vue';
import ConnectionFailureMessage from '@/components/account-management/ConnectionFailureMessage.vue';
import ConnectionLoading from '@/components/account-management/ConnectionLoading.vue';

defineSlots<{
  default: () => any;
}>();

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
  />
  <ConnectionFailureMessage v-else />

  <div
    v-if="displayRouter"
    data-cy="account-management-forms"
    :class="$style.router"
  >
    <slot />
  </div>

  <DockerWarning v-else-if="showDockerWarning" />
  <div
    v-else-if="connected"
    class="w-full h-full flex items-center justify-center"
  >
    <RuiProgress
      thickness="2"
      color="primary"
      variant="indeterminate"
      circular
    />
  </div>
</template>

<style lang="scss" module>
.router {
  min-height: 150px;
}
</style>
