import { mount } from '@vue/test-utils';

/**
 * Runs a composable inside a mounted component's `setup`, so composables that
 * register component lifecycle hooks (`onMounted`, `onBeforeUnmount`) or an
 * `onScopeDispose` have an active instance/scope to attach to. Without this,
 * calling such a composable bare in a test emits a Vue warning and the hook
 * silently no-ops.
 *
 * @param composable factory invoked inside setup; its return value is exposed as `result`
 * @returns the composable's return value and the test wrapper (call `wrapper.unmount()` to trigger teardown hooks)
 */
export function withSetup<T>(composable: () => T): { result: T; wrapper: ReturnType<typeof mount> } {
  let result!: T;
  const wrapper = mount({
    setup() {
      result = composable();
      return {};
    },
    template: '<div />',
  });
  return { result, wrapper };
}
