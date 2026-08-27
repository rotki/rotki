import type { VueWrapper } from '@vue/test-utils';
import type { ComponentPublicInstance } from 'vue';

/**
 * The instance type of a stub that declares its props at runtime.
 *
 * @remarks
 * A stub built from a `props: ['modelValue', ...]` array has no compile-time prop types, so its
 * instance is typed as an open record. Tightening this to a real props interface makes
 * `props('size')` stop compiling against every such stub.
 */
export type StubInstance = ComponentPublicInstance<Record<string, unknown>>;

/**
 * Accesses a component's `<script setup>` internals, meaning its setup-scoped state and methods.
 *
 * @remarks
 * Vue's public `vm` type never exposes those, so a cast is unavoidable. It is contained here
 * instead of being repeated across specs.
 *
 * @example
 * const vm = componentVm<{ save: () => void }>(wrapper);
 */
export function componentVm<T>(wrapper: VueWrapper): T {
  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- vm never exposes <script setup> internals in its public type; contained to this helper
  return wrapper.vm as unknown as T;
}
