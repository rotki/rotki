import type { ComputedRef, Ref } from 'vue';
import type { CreateAccountPayload } from '@/modules/auth/login';
import { startPromise, wait } from '@shared/utils';
import dayjs from 'dayjs';
import { usePasswordConfirmation } from '@/modules/auth/use-password-confirmation';
import { useRememberSettings } from '@/modules/auth/use-remember-settings';
import { useRestartingStatus } from '@/modules/auth/use-restarting-status';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { api } from '@/modules/core/api/rotki-api';
import { logger } from '@/modules/core/common/logging/logging';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';
import { useSessionReady } from './use-session-ready';
import {
  type Resolution,
  type UnlockCredentials,
  UnlockErrorKind,
  UnlockPhase,
  type UnlockState,
  type UnlockSteps,
  useUnlockFlow,
} from './use-unlock-flow';
import { useUnlockSteps } from './use-unlock-steps';

type UnlockMode = 'login' | 'create' | 'auto';

// Phases where the form must show a busy state (the asset-update prompt/conflict phases
// are excluded — they wait on the user, not on us).
const IN_FLIGHT: ReadonlySet<string> = new Set([
  UnlockPhase.resolving,
  UnlockPhase.authenticating,
  UnlockPhase.connecting,
  UnlockPhase.probing,
  UnlockPhase.checkingUpdate,
  UnlockPhase.applyingUpdate,
  UnlockPhase.restarting,
  UnlockPhase.unlocking,
  UnlockPhase.loadingSession,
  UnlockPhase.ready,
]);

export interface UseUnlockFlowControllerReturn {
  state: Readonly<Ref<UnlockState>>;
  loading: ComputedRef<boolean>;
  errors: ComputedRef<string[]>;
  upgradeVisible: Readonly<Ref<boolean>>;
  startLogin: (credentials: UnlockCredentials) => Promise<void>;
  startCreate: (payload: CreateAccountPayload) => Promise<void>;
  startAuto: () => Promise<void>;
  applyUpdate: (resolution?: Resolution, version?: number) => Promise<void>;
  skipUpdate: () => Promise<void>;
  reset: () => void;
}

/**
 * The single funnel for every unlock path — manual login, account creation, and
 * auto-login/resume all drive ONE shared `useUnlockFlow` instance (so the login page
 * renders progress regardless of which path started it). Owns the active step-set per
 * mode and runs the post-unlock side-effects on `ready`: the shared ones via
 * `useSessionReady`, plus the small per-mode extras.
 */
export function createUnlockFlowController(): UseUnlockFlowControllerReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { createSteps, loginSteps } = useUnlockSteps();
  const { handleSessionReady } = useSessionReady();
  const { logged, upgradeVisible, username } = storeToRefs(useSessionAuthStore());

  // A 401 only means "session lost" when a session is actually active. While logged out
  // (login screen) a 401 is expected and must stay local to its caller, or it would abort an
  // in-progress login. This is the pre-auth-hardening gate — it must be wired for every run.
  api.setOnAuthFailure(
    () => set(logged, false),
    () => get(logged),
  );
  const { updateFrontendSetting } = useSettingsOperations();
  const { disconnect: disconnectWallet } = useWalletStore();
  const { savedUsername } = useRememberSettings();
  const { checkIfPasswordConfirmationNeeded } = usePasswordConfirmation();
  const { restarting } = useRestartingStatus();

  const mode = ref<UnlockMode>('login');
  // The step-set the proxy currently delegates to; swapped synchronously before each start.
  let active: UnlockSteps = loginSteps;
  // When the current account-creation started, to gate the slow-upgrade UX pad in onReady.
  let createStartedAt = 0;

  const proxy: UnlockSteps = {
    applyUpdate: async (version, resolution) => active.applyUpdate(version, resolution),
    authenticate: async credentials => active.authenticate(credentials),
    checkUpdate: async () => active.checkUpdate(),
    connect: async () => active.connect(),
    loadSession: async () => active.loadSession(),
    login: async credentials => active.login(credentials),
    probeSession: async credentials => active.probeSession(credentials),
    requestRestart: async () => active.requestRestart(),
    resolveCredentials: async () => active.resolveCredentials(),
    resume: async credentials => active.resume(credentials),
    waitReady: async () => active.waitReady(),
  };

  const flow = useUnlockFlow(proxy);

  // Auto-unlock runs in the background — it must not flip the login form into its disabled
  // "loading" state (the disable→enable toggle on the autocomplete would otherwise fire a
  // spurious empty-username validation on first open).
  const loading = computed<boolean>(() => get(mode) !== 'auto' && IN_FLIGHT.has(get(flow.state).kind));

  const errors = computed<string[]>(() => {
    const current = get(flow.state);
    if (current.kind !== UnlockPhase.error)
      return [];
    const error = current.error;
    switch (error.kind) {
      case UnlockErrorKind.unknown:
        return error.message ? [error.message] : [];
      case UnlockErrorKind.updateFailed:
        return [error.message];
      case UnlockErrorKind.restartFailed:
        return [t('unlock_flow.errors.restart_failed')];
      // wrong-password surfaces via the server message (unknown); sync/upgrade conflicts
      // drive their own store-backed alerts inside LoginForm.
      case UnlockErrorKind.wrongPassword:
      case UnlockErrorKind.syncConflict:
      case UnlockErrorKind.incompleteUpgrade:
        return [];
    }
  });

  async function onReady(): Promise<void> {
    const current = get(mode);
    const state = get(flow.state);
    // The flow owns the resume-vs-fresh-login branch, so `ready.resumed` — not the caller's
    // mode — decides which post-unlock effects apply (a saved-password auto-unlock can end
    // in either branch).
    const resumed = state.kind === UnlockPhase.ready && state.resumed;

    // Pad only a *fast* create+upgrade so the progress bar is actually seen — a long upgrade
    // is already visible long enough and shouldn't tack on a needless delay before navigating.
    if (current === 'create' && get(upgradeVisible) && (dayjs().valueOf() - createStartedAt) / 1000 < 10)
      await wait(3000);
    // A fresh login (manual or saved-password auto-unlock) proves the password; record it.
    if (!resumed && current !== 'create')
      await updateFrontendSetting({ lastPasswordConfirmed: dayjs().unix() });
    if (current === 'create')
      set(savedUsername, get(username));

    await handleSessionReady();

    if (current === 'create')
      return;
    // A resumed session hasn't re-proven the password, so it may still need confirmation; a
    // fresh login just did, and disconnects any wallet lingering from the previous session.
    if (resumed)
      await checkIfPasswordConfirmationNeeded(get(username));
    else
      await disconnectWallet();
  }

  watch(flow.state, (current) => {
    // Surface the flow's restart as the shared "restarting" status so the connection screen
    // shows a restart message (the backend connection drops while it restarts).
    set(restarting, current.kind === UnlockPhase.restarting);
    // Log unexpected failures so a failed login is diagnosable in the field (conflicts and
    // wrong-password are expected and drive their own UI, so they are not logged).
    if (current.kind === UnlockPhase.error && current.error.kind === UnlockErrorKind.unknown && current.error.message)
      logger.error(`unlock failed: ${current.error.message}`);
    if (current.kind === UnlockPhase.ready)
      startPromise(onReady());
  });

  // Only one flow runs at a time: ignore a start while another is mid-flight (e.g. the two
  // `useAutoLogin` instances both reacting to `connected`, or a resume racing a manual login).
  function canStart(): boolean {
    const kind = get(flow.state).kind;
    return kind === UnlockPhase.idle || kind === UnlockPhase.error;
  }

  async function startLogin(credentials: UnlockCredentials): Promise<void> {
    if (!canStart())
      return;
    set(mode, 'login');
    active = loginSteps;
    await flow.start(credentials);
  }

  async function startCreate(payload: CreateAccountPayload): Promise<void> {
    if (!canStart())
      return;
    set(mode, 'create');
    active = createSteps(payload);
    createStartedAt = dayjs().valueOf();
    await flow.start(payload.credentials);
  }

  async function startAuto(): Promise<void> {
    if (!canStart())
      return;
    set(mode, 'auto');
    active = loginSteps;
    await flow.startAuto();
    // A background auto-unlock that hit a real failure (e.g. a stale saved password) ends in
    // `error` — fall back to a clean idle form rather than parking the login screen in error.
    // Guarded by the canStart() check above so it can never clear another in-flight flow.
    if (get(flow.state).kind === UnlockPhase.error)
      flow.reset();
  }

  return {
    applyUpdate: flow.applyUpdate,
    errors,
    loading,
    reset: flow.reset,
    skipUpdate: flow.skipUpdate,
    startAuto,
    startCreate,
    startLogin,
    state: flow.state,
    upgradeVisible,
  };
}

/**
 * App-wide singleton: every consumer (login page, account-management, auto-login) shares
 * one flow instance so the UI reflects whichever path is driving the unlock.
 */
export const useUnlockFlowController = createSharedComposable(createUnlockFlowController);
