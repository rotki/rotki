import { Zero } from '@rotki/common';
import { useTimeoutFn } from '@vueuse/core';
import { set } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { err, ok, type Result } from 'plainfp/result';
import { type MaybeRefOrGetter, readonly, type Ref, shallowRef, toValue } from 'vue';
import { useI18n } from 'vue-i18n';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { Module, SUPPORTED_MODULES } from '@/modules/core/common/modules';
import { type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { moduleToggleActivity } from '@/modules/settings/modules/module-toggle.activity';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseModuleToggleReturn {
  /** Whether a settings write for a module change is in flight. */
  loading: Readonly<Ref<boolean>>;
  /** Turns one module on or off, announced as its own {@link moduleToggleActivity}. */
  switchModule: (module: Module, enabled: boolean) => Promise<void>;
  /** Turns every supported module on. */
  enableAll: () => Promise<void>;
  /** Turns every module off. */
  disableAll: () => Promise<void>;
}

/**
 * Writes module on/off changes to the settings, one at a time or in bulk, and clears the NFT
 * balances shortly after the NFT module goes off.
 */
export function useModuleToggle(activeModules: MaybeRefOrGetter<Module[]>): UseModuleToggleReturn {
  const { t } = useI18n({ useScope: 'global' });

  const supportedModules = SUPPORTED_MODULES;
  const loading = shallowRef<boolean>(false);

  const { update: updateSettings } = useSettingsOperations();

  const { nonFungibleTotalValue } = storeToRefs(useBalancesStore());
  const { submitTask } = useNativeTask();

  const { start: clearNfBalances } = useTimeoutFn(() => {
    set(nonFungibleTotalValue, Zero);
  }, 800, { immediate: false });

  async function update(activeModules: Module[]): Promise<void> {
    set(loading, true);
    await updateSettings({ activeModules });
    set(loading, false);
  }

  async function switchModule(module: Module, enabled: boolean): Promise<void> {
    const active = toValue(activeModules);
    let modules: Module[];
    if (enabled)
      modules = [...active, module];
    else modules = active.filter(m => m !== module);

    await submitTask({
      ephemeral: true,
      id: moduleToggleActivity.id({ enabled, module }),
      kind: moduleToggleActivity.kind,
      run: async (): Promise<Result<void, TaskError>> => {
        try {
          await update(modules);
          return ok(undefined);
        }
        catch (error: unknown) {
          return err(TaskFailed({ cause: error, message: getErrorMessage(error) }));
        }
      },
      title: t('module_selector.tasks.toggle'),
    });

    if (module === Module.NFTS && !enabled)
      clearNfBalances();
  }

  /**
   * Applies a bulk module change, announcing each module whose state actually flips as its own
   * {@link moduleToggleActivity}.
   *
   * @remarks
   * One settings write, several identities. Consumers subscribe per module and direction
   * (`use-nft-balances.ts` keys on `module-toggle:nfts:enabled`), so a bulk change that announced
   * only itself would leave them stale: "Enable all" would never tell NFT balances they can load.
   */
  async function applyBulk(next: Module[]): Promise<void> {
    const active = toValue(activeModules);
    const changed = supportedModules
      .map(module => module.identifier)
      .filter(module => active.includes(module) !== next.includes(module));

    if (changed.length === 0)
      return;

    const written = update(next).then(
      (): Result<void, TaskError> => ok(undefined),
      (error: unknown): Result<void, TaskError> => err(TaskFailed({ cause: error, message: getErrorMessage(error) })),
    );

    await Promise.all(changed.map(async module => submitTask({
      ephemeral: true,
      id: moduleToggleActivity.id({ enabled: next.includes(module), module }),
      kind: moduleToggleActivity.kind,
      run: async (): Promise<Result<void, TaskError>> => written,
      title: t('module_selector.tasks.toggle'),
    })));
  }

  async function enableAll(): Promise<void> {
    await applyBulk(supportedModules.map(x => x.identifier));
  }

  async function disableAll(): Promise<void> {
    const active = toValue(activeModules);
    await applyBulk([]);
    if (active.includes(Module.NFTS))
      clearNfBalances();
  }

  return {
    disableAll,
    enableAll,
    loading: readonly(loading),
    switchModule,
  };
}
