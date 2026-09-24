import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DockAdditionDetail from '@/modules/task-center/components/DockAdditionDetail.vue';

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({ getChainName: (chain: string): string => `name:${chain}` })),
}));

const NOTHING = { added: [], everyChain: false, existed: [], failed: [], noActivity: [] };

function createWrapper(props: Partial<InstanceType<typeof DockAdditionDetail>['$props']>): VueWrapper {
  return mount(DockAdditionDetail, {
    props: { ...NOTHING, ...props },
    global: {
      stubs: { ChainIcon: { props: ['chain'], template: '<i data-testid="chain-icon">{{ chain }}</i>' } },
    },
  });
}

function text(wrapper: VueWrapper, id: string): string | undefined {
  const element = wrapper.find(`[data-testid=${id}]`);
  return element.exists() ? element.text() : undefined;
}

describe('dockAdditionDetail', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should show an icon per chain the address landed on, naming them all on hover', () => {
    const wrapper = createWrapper({ added: ['eth', 'base'] });

    expect(wrapper.findAll('[data-testid=chain-icon]').map(icon => icon.text())).toStrictEqual(['eth', 'base']);
    expect(wrapper.find('[data-testid=dock-addition-added]').attributes('title')).toBe('name:eth, name:base');
  });

  it('should cap the icons and count the rest', () => {
    const wrapper = createWrapper({ added: ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'] });

    expect(wrapper.findAll('[data-testid=chain-icon]')).toHaveLength(6);
    expect(text(wrapper, 'dock-addition-added')).toContain('task_dock.detail.addition.more::2');
  });

  it('should say every chain in words rather than draw every icon', () => {
    const wrapper = createWrapper({ everyChain: true });

    expect(wrapper.text()).toContain('task_dock.detail.addition.every_chain');
    expect(wrapper.findAll('[data-testid=chain-icon]')).toHaveLength(0);
  });

  it('should count the chains it was not added on rather than name them', () => {
    const wrapper = createWrapper({ added: ['eth'], existed: ['base'], noActivity: ['gnosis', 'scroll'] });

    expect(text(wrapper, 'dock-addition-skipped'))
      .toBe('task_dock.detail.addition.no_activity::2 · task_dock.detail.addition.existed::1');
  });

  it('should name the chains that could not be checked', () => {
    const wrapper = createWrapper({ added: ['eth'], failed: ['scroll', 'base'] });

    expect(text(wrapper, 'dock-addition-failed')).toBe('task_dock.detail.addition.failed::name:scroll, name:base');
  });

  it('should count more than three failed chains, naming them all on hover', () => {
    const wrapper = createWrapper({ added: ['eth'], failed: ['scroll', 'base', 'gnosis', 'ink'] });
    const line = wrapper.find('[data-testid=dock-addition-failed]');

    expect(line.text()).toBe('task_dock.detail.addition.failed_count::4');
    expect(line.attributes('title')).toBe('name:scroll, name:base, name:gnosis, name:ink');
  });

  it('should add no skipped or failed line when every chain went through', () => {
    const wrapper = createWrapper({ added: ['eth'] });

    expect(text(wrapper, 'dock-addition-skipped')).toBeUndefined();
    expect(text(wrapper, 'dock-addition-failed')).toBeUndefined();
  });
});
