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
  <LoginOverlay>
    <div :class="css.wrapper">
      <div :class="css.container">
        <VCard
          class="pb-4"
          :class="css.card"
          light
          data-cy="account-management"
        >
          <LoginHeader />
          <DockerWarning v-if="!dockerRiskAccepted && isDocker" />
          <ConnectionLoading
            v-else-if="!connectionFailure"
            :connected="connected && !autolog"
          />
          <ConnectionFailureMessage v-else />
          <div
            v-if="displayRouter"
            data-cy="account-management-forms"
            :class="css.router"
          >
            <RouterView />
          </div>
        </VCard>
      </div>

      <LoginIcon left>
        <AnimationsButton />
      </LoginIcon>
      <PrivacyNotice />
      <LoginIcon>
        <template v-if="isPackaged">
          <OnboardingSettingsButton />
        </template>
        <template v-else>
          <AboutButton />
        </template>
      </LoginIcon>
    </div>
  </LoginOverlay>
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
