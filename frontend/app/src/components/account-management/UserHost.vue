<script setup lang="ts">
import { useMainStore } from '@/store/main';

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
