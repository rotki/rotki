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
import { disconnectWalletIfActive } from '@/modules/wallet/use-wallet-store';
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

/** The phases that mean work is in progress; the phases that wait on the user are absent. */
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
 * Builds the single funnel every unlock path runs through: manual login, account creation and
 * auto-login/resume all drive one shared `useUnlockFlow`, so the login page renders progress no
 * matter which path started it.
 */
export function createUnlockFlowController(): UseUnlockFlowControllerReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { createSteps, loginSteps } = useUnlockSteps();
  const { handleSessionReady } = useSessionReady();
  const { logged, upgradeVisible, username } = storeToRefs(useSessionAuthStore());

  api.setOnAuthFailure(
    () => set(logged, false),
    () => get(logged),
  );
  const { updateFrontendSetting } = useSettingsOperations();
  const { savedUsername } = useRememberSettings();
  const { checkIfPasswordConfirmationNeeded } = usePasswordConfirmation();
  const { restarting } = useRestartingStatus();

  const mode = ref<UnlockMode>('login');
  let active: UnlockSteps = loginSteps;
  /** Epoch milliseconds of when the current account creation started; 0 outside a creation. */
  let createStartedAt = 0;

  const proxy: UnlockSteps = {
    applyUpdate: async (version, resolution) => active.applyUpdate(version, resolution),
    authenticate: async credentials => active.authenticate(credentials),
    checkUpdate: async () => active.checkUpdate(),
    connect: async () => active.connect(),
    disconnect: () => active.disconnect(),
    loadSession: async () => active.loadSession(),
    login: async credentials => active.login(credentials),
    probeSession: async credentials => active.probeSession(credentials),
    requestRestart: async () => active.requestRestart(),
    resolveCredentials: async () => active.resolveCredentials(),
    resume: async credentials => active.resume(credentials),
    waitReady: async () => active.waitReady(),
  };

  const flow = useUnlockFlow(proxy);

  /**
   * Whether the form shows a busy state. Never during an auto-unlock: toggling the username
   * autocomplete's disabled state fires a spurious empty-username validation on first open.
   */
  const loading = computed<boolean>(() => get(mode) !== 'auto' && IN_FLIGHT.has(get(flow.state).kind));

  /**
   * The unlock failures the form itself renders. A wrong password is not one: it reaches the user
   * as the server's own message under {@link UnlockErrorKind.unknown}.
   */
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
      case UnlockErrorKind.wrongPassword:
      case UnlockErrorKind.syncConflict:
      case UnlockErrorKind.incompleteUpgrade:
        return [];
    }
  });

  /**
   * Runs the post-unlock side-effects once the flow reports ready.
   *
   * @remarks
   * `ready.resumed`, not the caller's mode, picks the branch: a saved-password auto-unlock can end
   * in either. A create that also ran an upgrade is padded only when it was fast, so the progress
   * bar is seen at all; a slow upgrade was on screen long enough already.
   */
  async function onReady(): Promise<void> {
    const current = get(mode);
    const state = get(flow.state);
    const resumed = state.kind === UnlockPhase.ready && state.resumed;

    if (current === 'create' && get(upgradeVisible) && (dayjs().valueOf() - createStartedAt) / 1000 < 10)
      await wait(3000);
    if (!resumed && current !== 'create')
      await updateFrontendSetting({ lastPasswordConfirmed: dayjs().unix() });
    if (current === 'create')
      set(savedUsername, get(username));

    await handleSessionReady();

    if (current === 'create')
      return;
    if (resumed)
      await checkIfPasswordConfirmationNeeded(get(username));
    else
      await disconnectWalletIfActive();
  }

  watch(flow.state, (current) => {
    set(restarting, current.kind === UnlockPhase.restarting);
    if (current.kind === UnlockPhase.error && current.error.kind === UnlockErrorKind.unknown && current.error.message)
      logger.error(`unlock failed: ${current.error.message}`);
    if (current.kind === UnlockPhase.ready)
      startPromise(onReady());
  });

  /**
   * Reports whether a new flow may start; only one runs at a time. The starts it turns away are
   * real: both `useAutoLogin` instances react to `connected`, and a resume can race a manual login.
   */
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
 * App-wide singleton. Every consumer (login page, account management, auto-login) shares one flow
 * instance so the UI reflects whichever path is driving the unlock.
 */
export const useUnlockFlowController = createSharedComposable(createUnlockFlowController);
