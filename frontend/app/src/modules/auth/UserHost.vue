<script setup lang="ts">
import { logicAnd, logicNot, logicOr } from '@vueuse/math';
import { storeToRefs } from 'pinia';
import ConnectionFailureMessage from '@/modules/auth/ConnectionFailureMessage.vue';
import ConnectionLoading from '@/modules/auth/ConnectionLoading.vue';
import DockerWarning from '@/modules/auth/DockerWarning.vue';
import { useAutoLogin } from '@/modules/auth/use-auto-login';
import { useRestartingStatus } from '@/modules/auth/use-restarting-status';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useMainStore } from '@/modules/core/common/use-main-store';

defineSlots<{
  /**
   * The account page's form, placed at the top offset every account page shares, so the heading
   * stays put when moving between login and profile creation.
   */
  default: () => any;
}>();

const { autolog } = useAutoLogin();
const { restarting } = useRestartingStatus();
const { upgradeVisible } = storeToRefs(useSessionAuthStore());

const { connected, connectionFailure, sessionAuthEnabled, unauthenticatedApiAccepted } = storeToRefs(useMainStore());

const isDocker = import.meta.env.VITE_DOCKER === 'true';
/**
 * Whether this deployment is exposed unauthenticated and has not said so deliberately. Either half
 * settles it: session authentication means there is no exposure, and the operator can accept the
 * risk through the env var or the button on the warning itself.
 */
const showDockerWarning = logicAnd(isDocker, logicNot(sessionAuthEnabled), logicNot(unauthenticatedApiAccepted));

/**
 * Whether the page's unlock stage is reporting progress the connection screen would hide: the
 * backend restart after an asset update, when the connection drops on purpose, and a DB upgrade
 * during an auto-unlock, which would otherwise run behind the "signing in" loader.
 */
const stageOwnsScreen = logicAnd(logicNot(connectionFailure), logicOr(restarting, logicAnd(autolog, upgradeVisible)));

/**
 * Held back during an auto-unlock, so the empty login form never shows behind the ConnectionLoading
 * card, which is the single loading state for the whole attempt.
 */
const displayRouter = logicOr(stageOwnsScreen, logicAnd(connected, logicNot(autolog), logicNot(showDockerWarning)));
</script>

<template>
  <div
    class="grow flex flex-col pt-14 lg:pt-[calc(12vh+3.5rem)]"
    data-testid="user-host"
  >
    <template v-if="!stageOwnsScreen">
      <ConnectionLoading
        v-if="!connectionFailure"
        :connected="connected && !autolog"
        :logging-in="autolog"
      />
      <ConnectionFailureMessage v-else />
    </template>

    <div
      v-if="displayRouter"
      data-testid="account-management-forms"
      class="min-h-37.5"
    >
      <slot />
    </div>

    <DockerWarning v-else-if="showDockerWarning" />
  </div>
</template>
