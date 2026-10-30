import type { AccountManage } from '@/modules/accounts/blockchain/use-account-manage';
import { Blockchain } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { createNewBlockchainAccount } from '@/modules/accounts/blockchain/new-account-state';
import AddressAccountForm from '@/modules/accounts/management/types/AddressAccountForm.vue';

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): Record<string, unknown> => ({ isEvm: (): boolean => true }),
}));

vi.mock('@/modules/accounts/blockchain/use-address-check', () => ({
  useAddressCheck: (): Record<string, unknown> => ({ addressCheck: (): undefined => undefined }),
}));

const importLink = '[data-testid=account-form-import-csv]';

function createWrapper(modelValue: AccountManage): VueWrapper<InstanceType<typeof AddressAccountForm>> {
  return mount(AddressAccountForm, {
    global: {
      stubs: {
        AccountDataInput: true,
        AddressInput: { template: '<div><slot name="bulk-actions" /></div>' },
        ModuleActivator: true,
        RuiButton: { emits: ['click'], template: '<button @click="$emit(\'click\')"><slot /></button>' },
      },
    },
    props: { errorMessages: {}, loading: false, modelValue },
  });
}

describe('addressAccountForm', () => {
  describe('the CSV import link', () => {
    it('should ask for the CSV import when clicked', async () => {
      const wrapper = createWrapper(createNewBlockchainAccount());

      await wrapper.find(importLink).trigger('click');

      expect(wrapper.emitted('import-csv')).toHaveLength(1);
    });

    it('should not be offered while editing an account', () => {
      const wrapper = createWrapper({
        chain: Blockchain.ETH,
        data: { address: '0x9531C059098e3d194fF87FebB587aB07B30B1306', tags: null },
        mode: 'edit',
        type: 'account',
      });

      expect(wrapper.find(importLink).exists()).toBe(false);
    });
  });
});
