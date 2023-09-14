<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';

const { autolog } = useAutoLogin();
const { isPackaged } = useInterop();
const { connectionFailure, connected, dockerRiskAccepted } = storeToRefs(
  useMainStore()
);

const isDocker = import.meta.env.VITE_DOCKER;
const hasAcceptedDockerRisk = logicAnd(dockerRiskAccepted, isDocker);
const loginIfConnected = logicOr(
  isPackaged,
  hasAcceptedDockerRisk,
  logicNot(isDocker)
);
const displayRouter = logicAnd(connected, loginIfConnected);

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
  </Fragment>
</template>

<style lang="scss" module>
.router {
  min-height: 150px;
}
</style>
