import type { PendingSuggestion, SuggestionAction } from './settings-suggestions';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { EvmIndexer } from '@/modules/settings/types/evm-indexer';
import SettingsSuggestionsDialog from './SettingsSuggestionsDialog.vue';

const mockPush = vi.fn();

vi.mock('vue-router', () => ({
  useRouter: vi.fn(() => ({ push: mockPush })),
}));

const gnosisAction: SuggestionAction = { label: 'Add a Blockscout API key', service: 'blockscout' };

const gnosisSuggestion: PendingSuggestion = {
  choices: [
    { id: EvmIndexer.BLOCKSCOUT, label: 'Blockscout, then Etherscan', value: { gnosis: [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN] } },
    { id: EvmIndexer.ETHERSCAN, label: 'Etherscan, then Blockscout', value: { gnosis: [EvmIndexer.ETHERSCAN, EvmIndexer.BLOCKSCOUT] } },
  ],
  currentValue: { gnosis: [EvmIndexer.ETHERSCAN] },
  description: 'Choose which indexer rotki uses for Gnosis',
  fromVersion: '1.44.0',
  key: 'evmIndexersOrder',
  recommendedChoice: EvmIndexer.BLOCKSCOUT,
  requirements: [
    { label: 'Blockscout API key', met: false },
    { label: 'Etherscan API key (paid plan)', met: true },
  ],
  settingType: 'general',
  suggestedValue: { gnosis: [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN] },
  action: gnosisAction,
};

describe('settingsSuggestionsDialog', () => {
  function createWrapper(suggestions: PendingSuggestion[] = [gnosisSuggestion]): VueWrapper {
    return mount(SettingsSuggestionsDialog, {
      props: { modelValue: true, suggestions },
      global: { stubs: { RuiDialog: { template: '<div><slot /></div>' } } },
    });
  }

  it('should preselect the recommended choice and hand it back on apply', async () => {
    const wrapper = createWrapper();

    expect(wrapper.find<HTMLInputElement>('[data-testid=suggestion-choice][data-key=blockscout] input').element.checked).toBe(true);
    await wrapper.find('[data-testid=apply-suggestions]').trigger('click');

    expect(wrapper.emitted('apply')?.[0]).toEqual([{
      choices: { 'general:evmIndexersOrder': EvmIndexer.BLOCKSCOUT },
      selected: [gnosisSuggestion],
    }]);
  });

  it('should hand back the choice the user switched to', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=suggestion-choice][data-key=etherscan] input').setValue(true);
    await wrapper.find('[data-testid=apply-suggestions]').trigger('click');

    expect(wrapper.emitted('apply')?.[0]).toEqual([{
      choices: { 'general:evmIndexersOrder': EvmIndexer.ETHERSCAN },
      selected: [gnosisSuggestion],
    }]);
  });

  it('should send the user to the api key page and close without dismissing', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=suggestion-action]').trigger('click');

    expect(mockPush).toHaveBeenCalledWith({ name: '/api-keys/external/', query: { service: 'blockscout' } });
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([false]);
    expect(wrapper.emitted('dismiss')).toBeUndefined();
  });
});
