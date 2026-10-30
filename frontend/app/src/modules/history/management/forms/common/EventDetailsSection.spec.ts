import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { nextTick } from 'vue';
import EventDetailsSection from '@/modules/history/management/forms/common/EventDetailsSection.vue';

type Errors = Record<string, string[]>;

function lookup(errors: Errors): (path: string) => string[] {
  return path => errors[path] ?? [];
}

function createWrapper(errors: Errors = {}): VueWrapper<InstanceType<typeof EventDetailsSection>> {
  return mount(EventDetailsSection, {
    attrs: { 'data-testid': 'details' },
    props: { errors: lookup(errors), paths: ['groupIdentifier', 'sequenceIndex'] },
    slots: { default: '<input data-testid="inside" />' },
  });
}

function state(wrapper: VueWrapper<any>): string | undefined {
  return wrapper.find('[data-testid=details]').attributes('data-state');
}

function errorCount(wrapper: VueWrapper<any>): string | undefined {
  const chip = wrapper.find('[data-testid=event-details-error-count]');
  return chip.exists() ? chip.text() : undefined;
}

describe('eventDetailsSection', () => {
  it('should start closed, with its fields rendered so the form can reach them', () => {
    const wrapper = createWrapper();

    expect(state(wrapper)).toBe('closed');
    expect(wrapper.find('[data-testid=inside]').exists()).toBe(true);
    expect(errorCount(wrapper)).toBeUndefined();
  });

  it('should open by itself when one of its fields shows an error', async () => {
    const wrapper = createWrapper();

    await wrapper.setProps({ errors: lookup({ groupIdentifier: ['taken'] }) });
    await nextTick();

    expect(state(wrapper)).toBe('open');
  });

  it('should count its fields in error, not their messages', async () => {
    const wrapper = createWrapper();

    await wrapper.setProps({ errors: lookup({ groupIdentifier: ['taken', 'too long'], sequenceIndex: ['required'] }) });

    expect(errorCount(wrapper)).toBe('2');
  });

  it('should ignore errors on fields outside it', async () => {
    const wrapper = createWrapper();

    await wrapper.setProps({ errors: lookup({ amount: ['required'] }) });
    await nextTick();

    expect(state(wrapper)).toBe('closed');
    expect(errorCount(wrapper)).toBeUndefined();
  });

  it('should stay where the user left it while errors remain', async () => {
    const wrapper = createWrapper();
    await wrapper.setProps({ errors: lookup({ groupIdentifier: ['taken'] }) });
    await nextTick();

    await wrapper.find('[data-accordion-trigger]').trigger('click');
    await wrapper.setProps({ errors: lookup({ groupIdentifier: ['taken'], sequenceIndex: ['required'] }) });
    await nextTick();

    expect(state(wrapper)).toBe('closed');
  });
});
