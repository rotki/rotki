import type { ComponentProps } from 'vue-component-type-helpers';

/** The `v-model` a wrapper owns, so a caller cannot also reach the wrapped component's. */
type ModelKeys = 'modelValue' | 'modelModifiers' | 'onUpdate:modelValue' | 'onUpdate:model-value';

/**
 * The props, events and attributes a wrapper hands to the component it wraps through `$attrs`, less
 * what the wrapper declares itself, the events it emits itself and the `v-model` it owns. All of it is
 * optional, since a prop the wrapped component requires is one the wrapper already binds.
 *
 * @remarks
 * Intersect it into `defineProps` behind a `@vue-ignore` block comment, as in
 * `defineProps<Props & /* @vue-ignore *\/ ForwardedProps<typeof RuiTextField, Props>>()`. That types
 * the wrapper's template usage without turning the forwarded names into runtime props, which would
 * take them out of `$attrs` and stop them reaching the wrapped component.
 */
/**
 * `RuiAutoComplete` props whose types the library does not export. Name them in `TOwn` from a generic
 * wrapper: its emitted type cannot refer to them, and the build fails with TS2883.
 */
export type UnexportedAutoCompleteProps = Record<'groupBy' | 'itemDisabled', unknown>;

export type ForwardedProps<TComponent, TOwn = object, TEmits extends string = never> = Partial<Omit<
  ComponentProps<TComponent>,
  keyof TOwn | ModelKeys | `on${Capitalize<TEmits>}`
>>;
