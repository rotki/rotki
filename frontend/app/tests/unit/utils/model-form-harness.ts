import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import { vi } from 'vitest';
import { type Component, type ComponentPublicInstance, defineComponent, h, ref, shallowRef } from 'vue';

interface ExposedForm {
  validate: () => boolean | Promise<boolean>;
}

function isExposedForm(value: unknown): value is ExposedForm {
  return typeof value === 'object' && value !== null && typeof Reflect.get(value, 'validate') === 'function';
}

export interface ModelFormHarness<TPayload extends object> {
  wrapper: VueWrapper;
  /** The payload as the dialog above the form holds it, after every write the form has made. */
  model: () => TPayload;
  /** The dialog's prompt-on-close flag. False on open is the contract; see `mountModelForm`. */
  stateUpdated: () => boolean;
  /** Field errors as reported by the api, which the form both reads and clears. */
  errors: () => ValidationErrors;
  validate: () => boolean | Promise<boolean>;
}

export interface ModelFormOptions<TPayload extends object> {
  payload: TPayload;
  /** Only bound when given, so a form that declares no `errorMessages` model gets no stray attr. */
  errors?: ValidationErrors;
  props?: Record<string, unknown>;
  global?: ComponentMountingOptions<Component>['global'];
}

/**
 * Mounts a form whose payload belongs to the dialog above it, with a parent that holds that payload
 * in a real ref.
 *
 * The round trip is part of what these forms do, so it has to be real: re-feeding `modelValue` with
 * `wrapper.setProps` never reaches the form's own state, which leaves the edit-driven assertions
 * passing for the wrong reason and the ones about `stateUpdated` failing for no reason.
 *
 * Two contracts are worth asserting for every one of these forms, because neither is visible
 * without a test and both have been broken in practice:
 *
 * - `expect(harness.stateUpdated()).toBe(false)` after mount settles. A form that decides part of
 *   its own opening state - a remembered chain, a suggested name - must seed it into the baseline
 *   (`useModelForm`'s `seed`), or the dialog prompts about unsaved changes before the user has
 *   touched anything.
 * - an edit reaching `harness.model()`, since the dialog saves what it reads off the model rather
 *   than what the form holds.
 */
export function mountModelForm<TPayload extends object>(
  component: Component,
  options: ModelFormOptions<TPayload>,
): ModelFormHarness<TPayload> {
  const model = ref<TPayload>(options.payload);
  const errors = ref<ValidationErrors>(options.errors ?? {});
  const stateUpdated = ref<boolean>(false);
  const form = shallowRef<ExposedForm>();

  const bindsErrors = options.errors !== undefined;

  const parent = defineComponent({
    setup() {
      return () => h(component, {
        ...options.props,
        'modelValue': get(model),
        'onUpdate:modelValue': (value: TPayload): void => set(model, value),
        'ref': (instance: Element | ComponentPublicInstance | null): void => {
          if (isExposedForm(instance))
            set(form, instance);
        },
        'stateUpdated': get(stateUpdated),
        'onUpdate:stateUpdated': (value: boolean): void => set(stateUpdated, value),
        ...(bindsErrors
          ? {
              'errorMessages': get(errors),
              'onUpdate:errorMessages': (value: ValidationErrors): void => set(errors, value),
            }
          : {}),
      });
    },
  });

  const wrapper = mount(parent, { global: options.global });

  return {
    errors: (): ValidationErrors => get(errors),
    model: (): TPayload => get(model),
    stateUpdated: (): boolean => get(stateUpdated),
    validate: (): boolean | Promise<boolean> => {
      const instance = get(form);
      if (!instance)
        throw new Error('the form did not expose a validate method');
      return instance.validate();
    },
    wrapper,
  };
}

/**
 * Runs out the debounced work a form kicks off while mounting.
 *
 * @remarks
 * Call this before the edit a test is actually about, so that edit is the only one in play.
 * Without it the mount's own settling lands mid-test and the assertions read its writes instead.
 *
 * Requires `vi.useFakeTimers()`, and outlasts the 500ms validation debounce these forms share.
 */
export async function settleMountedWork(): Promise<void> {
  await vi.advanceTimersByTimeAsync(600);
}
