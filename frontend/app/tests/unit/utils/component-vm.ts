import type { VueWrapper } from '@vue/test-utils';

/**
 * Access a component's `<script setup>` internals (setup-scoped state and
 * methods) from a test. Vue's public `vm` type never exposes those, so a cast
 * is unavoidable — it is contained here instead of being repeated across specs.
 *
 * @example
 * const vm = componentVm<{ save: () => void }>(wrapper);
 */
export function componentVm<T>(wrapper: VueWrapper): T {
  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- vm never exposes <script setup> internals in its public type; contained to this helper
  return wrapper.vm as unknown as T;
}
