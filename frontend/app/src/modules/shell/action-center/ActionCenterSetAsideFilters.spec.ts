import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import ActionCenterSetAsideFilters from '@/modules/shell/action-center/ActionCenterSetAsideFilters.vue';
import { SetAside } from '@/modules/shell/action-center/use-action-center-snooze';

function mountFilters(counts: Record<SetAside, number>, revealed: SetAside[] = []): VueWrapper<InstanceType<typeof ActionCenterSetAsideFilters>> {
  return mount(ActionCenterSetAsideFilters, { props: { counts, revealed } });
}

function filterFor(wrapper: VueWrapper, kind: SetAside): ReturnType<VueWrapper['find']> {
  return wrapper.find(`[data-testid="actions-center-set-aside-toggle"][data-key="${kind}"]`);
}

describe('modules/shell/action-center/ActionCenterSetAsideFilters', () => {
  it('should render nothing when no row was put away', () => {
    const wrapper = mountFilters({ [SetAside.MUTED]: 0, [SetAside.SNOOZED]: 0 });

    expect(wrapper.find('[data-testid="actions-center-set-aside"]').exists()).toBe(false);
  });

  it('should offer a filter, with its count, only for the kinds that have rows', () => {
    const wrapper = mountFilters({ [SetAside.MUTED]: 0, [SetAside.SNOOZED]: 2 });

    expect(filterFor(wrapper, SetAside.SNOOZED).text()).toContain('action_center.set_aside.snoozed');
    expect(filterFor(wrapper, SetAside.SNOOZED).text()).toContain('2');
    expect(filterFor(wrapper, SetAside.MUTED).exists()).toBe(false);
  });

  it('should reveal a kind on click, keeping the kinds already revealed', async () => {
    const wrapper = mountFilters({ [SetAside.MUTED]: 1, [SetAside.SNOOZED]: 2 }, [SetAside.SNOOZED]);

    await filterFor(wrapper, SetAside.MUTED).trigger('click');

    expect(wrapper.emitted('update:revealed')).toEqual([[[SetAside.SNOOZED, SetAside.MUTED]]]);
  });

  it('should keep the same label when revealed, marking it as pressed instead', async () => {
    const wrapper = mountFilters({ [SetAside.MUTED]: 1, [SetAside.SNOOZED]: 0 });
    const hidden = filterFor(wrapper, SetAside.MUTED);
    const label = hidden.text();
    expect(hidden.attributes('aria-pressed')).toBe('false');

    await wrapper.setProps({ revealed: [SetAside.MUTED] });

    expect(filterFor(wrapper, SetAside.MUTED).text()).toBe(label);
    expect(filterFor(wrapper, SetAside.MUTED).attributes('aria-pressed')).toBe('true');
  });

  it('should hide a revealed kind on click', async () => {
    const wrapper = mountFilters({ [SetAside.MUTED]: 1, [SetAside.SNOOZED]: 0 }, [SetAside.MUTED]);

    await filterFor(wrapper, SetAside.MUTED).trigger('click');

    expect(wrapper.emitted('update:revealed')).toEqual([[[]]]);
  });
});
