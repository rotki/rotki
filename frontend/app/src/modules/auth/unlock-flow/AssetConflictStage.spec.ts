import type { AssetUpdateConflictResult } from '@/modules/assets/types';
import { I18nTStub } from '@test/stubs/I18nT';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import AssetConflictStage from './AssetConflictStage.vue';
import '@test/i18n';

function conflict(identifier: string, localName: string, remoteName: string): AssetUpdateConflictResult {
  return {
    identifier,
    local: { identifier, isRebasing: false, name: localName, symbol: 'TKN' },
    remote: { identifier, isRebasing: false, name: remoteName, symbol: 'TKN' },
  };
}

const CONFLICTS = [conflict('eip155:1/erc20:0xa', 'Mine A', 'Token A'), conflict('eip155:1/erc20:0xb', 'Mine B', 'Token B')];

function mountStage(conflicts = CONFLICTS): VueWrapper<InstanceType<typeof AssetConflictStage>> {
  return mount(AssetConflictStage, {
    global: { stubs: { DateDisplay: true, HashLink: true, I18nT: I18nTStub } },
    props: { conflicts, version: 42 },
  });
}

async function choose(wrapper: VueWrapper, value: string): Promise<void> {
  await wrapper.get(`[data-testid=asset-conflicts-choice] input[value=${value}]`).setValue(true);
}

async function apply(wrapper: VueWrapper): Promise<void> {
  await wrapper.get('[data-testid=asset-conflicts-apply]').trigger('click');
}

describe('modules/auth/unlock-flow/AssetConflictStage', () => {
  it('should say how many assets conflict with which version', () => {
    expect(mountStage().get('[data-testid=stage-subtitle]').text()).toBe('unlock_flow.asset_update.conflicts.subtitle::2, 42');
  });

  it('should use the update for every asset unless told otherwise', async () => {
    const wrapper = mountStage();
    await apply(wrapper);

    expect(wrapper.emitted('resolve')).toEqual([[{ 'eip155:1/erc20:0xa': 'remote', 'eip155:1/erc20:0xb': 'remote' }]]);
  });

  it('should keep every local edit when chosen', async () => {
    const wrapper = mountStage();
    await choose(wrapper, 'local');
    await apply(wrapper);

    expect(wrapper.emitted('resolve')).toEqual([[{ 'eip155:1/erc20:0xa': 'local', 'eip155:1/erc20:0xb': 'local' }]]);
  });

  it('should list only the fields that differ when choosing per asset', async () => {
    const wrapper = mountStage();
    expect(wrapper.find('[data-testid=asset-conflicts-list]').exists()).toBe(false);

    await choose(wrapper, 'manual');
    const first = wrapper.findAll('[data-testid=asset-conflict]')[0];

    expect(first.text()).toContain('Token A (TKN)');
    expect(first.findAll('tbody tr').map(row => row.find('td').text())).toStrictEqual(['name']);
  });

  it('should apply a per-asset choice and count it', async () => {
    const wrapper = mountStage();
    await choose(wrapper, 'manual');
    const buttons = wrapper.findAll('[data-testid=asset-conflict]')[1].findAll('button');
    await buttons.find(button => button.text() === 'unlock_flow.asset_update.conflicts.review.keep_local')!.trigger('click');

    expect(wrapper.get('[data-testid=asset-conflicts-summary]').text()).toBe('unlock_flow.asset_update.conflicts.review.summary::1, 1');
    await apply(wrapper);

    expect(wrapper.emitted('resolve')).toEqual([[{ 'eip155:1/erc20:0xa': 'remote', 'eip155:1/erc20:0xb': 'local' }]]);
  });

  it('should skip the update without resolving', async () => {
    const wrapper = mountStage();
    await wrapper.get('[data-testid=asset-conflicts-skip]').trigger('click');

    expect(wrapper.emitted('skip')).toHaveLength(1);
    expect(wrapper.emitted('resolve')).toBeUndefined();
  });

  it('should warn about an identifier that arrived twice', () => {
    const warning = mountStage([...CONFLICTS, CONFLICTS[0]]).get('[data-testid=asset-conflicts-duplicate]');

    expect(warning.get('strong').text()).toBe('eip155:1/erc20:0xa');
    expect(mountStage().find('[data-testid=asset-conflicts-duplicate]').exists()).toBe(false);
  });
});
