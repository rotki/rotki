import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import WalletAddressesImport from '@/modules/accounts/blockchain/WalletAddressesImport.vue';

const { metamaskImport } = vi.hoisted(() => ({
  metamaskImport: vi.fn<() => Promise<string[]>>(),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): Record<string, unknown> => ({ isPackaged: true, metamaskImport }),
}));

function createWrapper(): VueWrapper<InstanceType<typeof WalletAddressesImport>> {
  return mount(WalletAddressesImport, {
    global: {
      stubs: { RuiTooltip: { template: '<div><slot name="activator" /></div>' } },
    },
    props: { disabled: false },
  });
}

async function clickImport(wrapper: VueWrapper): Promise<void> {
  await wrapper.find('button').trigger('click');
  await flushPromises();
}

describe('walletAddressesImport', () => {
  beforeEach(() => {
    metamaskImport.mockReset();
  });

  it('should hand the imported addresses on', async () => {
    metamaskImport.mockResolvedValue(['0x9531C059098e3d194fF87FebB587aB07B30B1306']);
    const wrapper = createWrapper();

    await clickImport(wrapper);

    expect(wrapper.emitted('update:addresses')).toEqual([[['0x9531C059098e3d194fF87FebB587aB07B30B1306']]]);
    expect(wrapper.emitted('failure')).toBeUndefined();
  });

  it('should emit a failed import as a message naming the import', async () => {
    metamaskImport.mockRejectedValue(new Error('no provider'));
    const wrapper = createWrapper();

    await clickImport(wrapper);

    expect(wrapper.emitted('failure')).toEqual([['input_mode_select.import_from_wallet.label: no provider']]);
    expect(wrapper.emitted('update:addresses')).toBeUndefined();
  });
});
