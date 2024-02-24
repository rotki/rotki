<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';

const { autolog } = useAutoLogin();
const { connectionFailure, connected, dockerRiskAccepted } = storeToRefs(
  useMainStore(),
);

const isDocker = import.meta.env.VITE_DOCKER;
const showDockerWarning = logicAnd(isDocker, logicNot(dockerRiskAccepted));
const displayRouter = logicAnd(connected, logicNot(showDockerWarning));

const css = useCssModule();
</script>

<template>
  <Fragment>
    <ConnectionLoading
      v-if="!connectionFailure"
      :connected="connected && !autolog"
    />
    <ConnectionFailureMessage v-else />

    <div
      v-if="displayRouter"
      data-cy="account-management-forms"
      :class="css.router"
    >
      <slot />
    </div>

    <DockerWarning
      v-else-if="showDockerWarning"
    />
  </Fragment>
</template>

<style lang="scss" module>
.router {
  min-height: 150px;
}
</style>
