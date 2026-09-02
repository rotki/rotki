import type { ValidatorData } from '@/modules/accounts/blockchain-accounts';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { Blockchain, type EthStakingCombinedFilter, type EthStakingFilter } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { defineComponent, h, type Ref } from 'vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import EnumValueEditor from '@/modules/core/table/pill/EnumValueEditor.vue';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import PillMenu from '@/modules/core/table/pill/PillMenu.vue';
import EthStakingFilterBar from './EthStakingFilterBar.vue';
import '@test/i18n';

const VALIDATOR: ValidatorData = {
  index: 9,
  ownershipPercentage: '100',
  publicKey: '0xabc123',
  status: 'active',
  type: 'validator',
  withdrawalAddress: '0x347AC2e04dD10cBF70F65c058Ac3a078D4D9E0e5',
};

const RuiMenuStub = defineComponent({
  name: 'RuiMenu',
  emits: ['update:modelValue'],
  props: { disabled: { default: false, type: Boolean }, modelValue: { default: false, type: Boolean } },
  template: '<div><slot name="activator" :attrs="{}" /><slot /></div>',
});

type BarWrapper = VueWrapper<InstanceType<typeof PillFilterBar>>;

interface Harness {
  bar: BarWrapper;
  filter: Ref<EthStakingCombinedFilter | undefined>;
  selection: Ref<EthStakingFilter>;
  warnings: string[];
}

function createHarnessWithModelsWrittenBack(): Harness {
  const pinia = createCustomPinia();
  setActivePinia(pinia);
  useBlockchainAccountsStore().accounts[Blockchain.ETH2] = [{
    chain: Blockchain.ETH2,
    data: VALIDATOR,
    label: 'Validator 9',
    nativeAsset: 'ETH2',
  }];

  const selection = ref<EthStakingFilter>({ validators: [] });
  const filter = ref<EthStakingCombinedFilter | undefined>({ status: 'active' });

  const Host = defineComponent({
    name: 'Host',
    render: () => h(EthStakingFilterBar, {
      'filter': get(filter),
      'modelValue': get(selection),
      'onUpdate:filter': (value: EthStakingCombinedFilter | undefined): void => set(filter, value),
      'onUpdate:modelValue': (value: EthStakingFilter): void => set(selection, value),
    }),
  });

  const warnings: string[] = [];
  const wrapper = mount(Host, {
    global: {
      config: {
        warnHandler: (message: string): void => {
          warnings.push(message);
        },
      },
      plugins: [pinia],
      stubs: { AssetValueEditor: true, RuiAutoComplete: true, RuiMenu: RuiMenuStub },
    },
  });

  return { bar: wrapper.findComponent(PillFilterBar), filter, selection, warnings };
}

async function addValidatorPillAndPick(bar: BarWrapper): Promise<void> {
  const fields: FieldDef[] = bar.props('fields');
  bar.findComponent(PillMenu).vm.$emit('select', fields.find(field => field.key === 'validator'));
  await nextTick();
  await nextTick();

  const editor = bar.findAllComponents(EnumValueEditor)
    .find(candidate => candidate.props('field').key === 'validator');
  expect(editor, 'the validator editor opens with its pill').toBeDefined();

  editor!.vm.$emit('update', { fieldKey: 'validator', op: 'is', values: ['9'] });
  await nextTick();
  await nextTick();
}

describe('ethStakingFilterBar', () => {
  it('should not loop when a validator is picked while a status filter is active', async () => {
    const { bar, warnings } = createHarnessWithModelsWrittenBack();
    await nextTick();

    await addValidatorPillAndPick(bar);

    expect(warnings.filter(message => message.includes('Maximum recursive updates'))).toEqual([]);
  });

  it('should clear the status filter, not just hide its field, when a validator is picked', async () => {
    const { bar, filter, selection } = createHarnessWithModelsWrittenBack();
    await nextTick();

    expect(get(filter)?.status).toBe('active');
    expect(bar.props('fields').some((field: FieldDef) => field.key === 'status')).toBe(true);

    await addValidatorPillAndPick(bar);

    const picked = get(selection);
    expect('validators' in picked && picked.validators.map(entry => entry.index)).toEqual([9]);
    expect(get(filter)?.status).toBeUndefined();
    expect(bar.props('fields').some((field: FieldDef) => field.key === 'status')).toBe(false);
  });
});
