import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import { type Component, defineComponent, h, type VNode } from 'vue';

/**
 * Mounts a `<script setup generic>` component with props a template would accept.
 *
 * @remarks
 * `mount` types a generic component's props at its type parameters' constraints, so a value built
 * for a narrower type argument, such as a matching kind of one item type, does not compile there,
 * although a template infers the type argument and accepts it. A host renders the component with
 * the props instead. The returned wrapper is the component itself, so its props and emits are
 * asserted as usual. The props are fixed: `setProps` does not reach the component, and a
 * `v-model` update is emitted but never fed back.
 */
export function mountGeneric(
  component: Component,
  props: Record<string, unknown>,
  global?: ComponentMountingOptions<Component>['global'],
): VueWrapper {
  const host = mount(defineComponent({ setup: () => (): VNode => h(component, props) }), { global });
  return host.findComponent(component);
}
