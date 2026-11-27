import type { DockSection as Section } from '@/modules/task-center/use-dock-panel';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { msg } from '@/message-key';
import DockSection from '@/modules/task-center/components/DockSection.vue';
import {
  type Activity,
  ActivityKind,
  ActivitySourceType,
  ActivityStatus,
  makeActivityId,
} from '@/modules/task-center/core/types';

const NOW = 1_000_000;

function job(name: string, startedAt: number, settledAt: number): Activity {
  return {
    cancellable: false,
    id: makeActivityId(ActivityKind.PRICES, name),
    kind: ActivityKind.PRICES,
    percentage: 100,
    rerunnable: false,
    settledAt,
    source: { type: ActivitySourceType.NATIVE },
    startedAt,
    status: ActivityStatus.COMPLETE,
    subtitle: `Updating ${name}`,
    title: 'Prices',
  };
}

const JOBS = [job('eur', NOW - 90_000, NOW - 80_000), job('usd', NOW - 85_000, NOW - 10_000)];

function createWrapper(section: Partial<Section> = {}): VueWrapper {
  return mount(DockSection, {
    props: {
      children: new Map(),
      now: NOW,
      section: { key: ActivityKind.PRICES, kindHeading: true, roots: JOBS, title: 'Prices', ...section },
    },
  });
}

describe('dockSection', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should fold to a heading naming its jobs and the wall time they took between them', () => {
    const wrapper = createWrapper({ folded: true });

    expect(wrapper.findAll('[data-testid=dock-activity-row]')).toHaveLength(0);
    expect(wrapper.get('[data-testid=dock-section-toggle]').attributes('aria-expanded')).toBe('false');
    expect(wrapper.get('[data-testid=dock-section-count]').text()).toBe('task_dock.panel.section_jobs::2');
    expect(wrapper.get('[data-testid=dock-section-span]').text()).toBe('1m 20s');
  });

  it('should list its jobs once the heading is clicked', async () => {
    const wrapper = createWrapper({ folded: true });

    await wrapper.get('[data-testid=dock-section-toggle]').trigger('click');

    expect(wrapper.findAll('[data-testid=dock-activity-row]')).toHaveLength(2);
  });

  it('should name each job by its subtitle under a heading that already names their kind', () => {
    const labels = createWrapper().findAll('[data-testid=activity-label]').map(label => label.text());

    expect(labels).toEqual(['Updating eur', 'Updating usd']);
  });

  it('should name a job by a translated subtitle with a single param, which is not an address', () => {
    const pools = (protocol: string): Activity => ({
      ...job(protocol, NOW - 2000, NOW),
      subtitle: { key: msg.$t('task_center.activity.liquidity_pools.protocol'), params: { protocol } },
      title: 'Liquidity pools',
    });
    const labels = createWrapper({ roots: [pools('Uniswap V2'), pools('Sushiswap')] })
      .findAll('[data-testid=activity-label]')
      .map(label => label.text());

    expect(labels).toEqual([
      'task_center.activity.liquidity_pools.protocol::Uniswap V2',
      'task_center.activity.liquidity_pools.protocol::Sushiswap',
    ]);
  });

  it('should keep each job\'s own title when no heading names their kind', () => {
    const labels = createWrapper({ kindHeading: false, title: undefined }).findAll('[data-testid=activity-label]').map(label => label.text());

    expect(labels).toEqual(['Prices', 'Prices']);
  });
});
