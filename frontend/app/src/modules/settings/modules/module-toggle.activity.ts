import type { Module } from '@/modules/core/common/modules';
import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { ActivityKind } from '@/modules/task-center/core/types';

/** One module switching on or off. */
export interface ModuleToggleSubject {
  readonly module: Module;
  readonly enabled: boolean;
}

/**
 * A module switching on or off, keyed by module and direction.
 *
 * @remarks
 * Consumers subscribe per module and direction (NFT balances go stale on `nfts:enabled`), so a
 * bulk change announces each module that actually flips under its own id.
 */
export const moduleToggleActivity = defineActivity<ModuleToggleSubject, readonly [Module, string]>({
  key: subject => [subject.module, subject.enabled ? 'enabled' : 'disabled'],
  kind: ActivityKind.MODULE_TOGGLE,
});
