<script setup lang="ts">
const css = useCssModule();

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
</script>

<template>
  <login-overlay>
    <div :class="css.wrapper">
      <div :class="css.container">
        <v-card
          class="pb-4"
          :class="css.card"
          light
          data-cy="account-management"
        >
          <login-header />
          <docker-warning v-if="!dockerRiskAccepted && isDocker" />
          <connection-loading
            v-else-if="!connectionFailure"
            :connected="connected && !autolog"
          />
          <connection-failure-message v-else />
          <div
            v-if="displayRouter"
            data-cy="account-management-forms"
            :class="css.router"
          >
            <router-view />
          </div>
        </v-card>
      </div>

      <login-icon left>
        <animations-button />
      </login-icon>
      <privacy-notice />
      <login-icon>
        <template v-if="isPackaged">
          <onboarding-settings-button />
        </template>
        <template v-else>
          <about-button />
        </template>
      </login-icon>
    </div>
  </login-overlay>
</template>

<style module lang="scss">
.container {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.wrapper {
  width: 600px;
  max-width: 100%;
  padding: 32px 16px 24px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100vh;

  @media (max-height: 800px) {
    padding-top: 0;
  }
}

.router {
  min-height: 150px;
}

.card {
  z-index: 5;
  max-height: calc(100vh - 140px);
  overflow: auto;
}
</style>
