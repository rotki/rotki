import type { Ref } from 'vue';
import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import LabeledAddressDisplay from '@/modules/shell/components/display/LabeledAddressDisplay.vue';
import { createRuiPlugin } from '@/plugins/rui';

const { getAddressName, getEnsName, labelWidth, SCRAMBLED_ADDRESS, scrambleData, shouldShowAmount } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    getAddressName: vi.fn(),
    getEnsName: vi.fn(),
    SCRAMBLED_ADDRESS: '0x1111111111111111111111111111111111111111',
    /** happy-dom measures every element as zero-wide, so the width is supplied here instead. */
    labelWidth: ref<number>(1000),
    scrambleData: ref<boolean>(false),
    shouldShowAmount: ref<boolean>(true),
  };
});

vi.mock('@/modules/settings/use-scramble', () => ({
  useScramble: (): Record<string, unknown> => ({
    scrambleAddress: (address: string) => (get(scrambleData) ? SCRAMBLED_ADDRESS : address),
    scrambleData,
    scrambleIdentifier: (id: string) => `scrambled-${id}`,
    shouldShowAmount,
  }),
}));

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: (): { getAddressName: Mock; getEnsName: Mock } => ({
    getAddressName,
    getEnsName,
  }),
}));

vi.mock('@vueuse/core', async () => {
  const actual = await vi.importActual<typeof import('@vueuse/core')>('@vueuse/core');
  return { ...actual, useElementSize: (): { width: Ref<number> } => ({ width: labelWidth }) };
});

const ADDRESS = '0x9531C059098e3d194fF87FebB587aB07B30B1306';

function account(overrides: Partial<BlockchainAccount> = {}): BlockchainAccount {
  return {
    chain: 'eth',
    data: { address: ADDRESS, type: 'address' },
    label: 'my wallet',
    nativeAsset: 'ETH',
    tags: undefined,
    ...overrides,
  };
}

function xpubAccount(): BlockchainAccount {
  return account({
    chain: 'btc',
    data: { derivationPath: 'm/84/0/0', type: 'xpub', xpub: 'xpub6C...' },
    label: 'cold storage',
  });
}

function createWrapper(acc: BlockchainAccount = account()): VueWrapper<any> {
  return mount(LabeledAddressDisplay, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: {
        EnsAvatar: { name: 'EnsAvatar', props: ['address', 'avatar'], template: '<div />' },
        HashLink: { name: 'HashLink', props: ['text', 'displayMode', 'location'], template: '<div />' },
        RuiDivider: true,
      },
    },
    props: { account: acc },
  });
}

function shown(wrapper: VueWrapper<any>): string {
  return wrapper.find('[data-testid=labeled-address-display]').text();
}

/**
 * The full detail lives in a tooltip, which renders only while hovered.
 *
 * @param wrapper - the mounted display
 * @returns everything the tooltip reveals
 */
async function tooltip(wrapper: VueWrapper<any>): Promise<string> {
  await wrapper.find('[data-testid=labeled-address-display]').trigger('mouseover');
  return wrapper.text();
}

describe('labeledAddressDisplay', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(scrambleData, false);
    set(shouldShowAmount, true);
    set(labelWidth, 1000);
    getAddressName.mockReturnValue(undefined);
    getEnsName.mockReturnValue(null);
  });

  /** The account's own label is a fallback; a name resolved for the address is the better one. */
  describe('which name it shows', () => {
    it('should show the account label when the address resolves to nothing', () => {
      expect(shown(createWrapper())).toContain('my wallet');
    });

    it('should prefer a resolved address book name', () => {
      getAddressName.mockReturnValue('Exchange deposit');

      expect(shown(createWrapper())).toContain('Exchange deposit');
    });

    it('should keep the label for an xpub rather than resolving its address', () => {
      getAddressName.mockReturnValue('Exchange deposit');

      expect(shown(createWrapper(xpubAccount()))).toContain('cold storage');
    });

    it('should fall back to the address when there is no label at all', () => {
      expect(shown(createWrapper(account({ label: '' })))).toContain('0x9531');
    });
  });

  /**
   * A numeric label is an account identifier rather than a name the user chose, so it is scrambled
   * with the same treatment identifiers get elsewhere.
   */
  describe('a numeric label', () => {
    it('should be scrambled as an identifier', () => {
      expect(shown(createWrapper(account({ label: '12345' })))).toContain('scrambled-12345');
    });

    it('should leave a label that only starts with digits alone', () => {
      expect(shown(createWrapper(account({ label: '1st wallet' })))).toContain('1st wallet');
    });
  });

  /** Scrambling exists so a screenshot leaks nothing, so no resolved name may survive it. */
  describe('while scrambling', () => {
    it('should withhold a resolved address book name', () => {
      getAddressName.mockReturnValue('Exchange deposit');
      set(scrambleData, true);

      expect(shown(createWrapper())).not.toContain('Exchange deposit');
    });

    it('should withhold the ens name', async () => {
      getEnsName.mockReturnValue('rotki.eth');
      set(scrambleData, true);

      expect(await tooltip(createWrapper())).not.toContain('rotki.eth');
    });

    it('should show a scrambled address rather than the real one', () => {
      set(scrambleData, true);

      const label = shown(createWrapper(account({ label: '' })));

      expect(label).not.toContain('0x9531');
      expect(label).toContain('0x1111');
    });
  });

  describe('an xpub account', () => {
    it('should be marked as one', () => {
      expect(shown(createWrapper(xpubAccount()))).toContain('common.xpub');
    });

    it('should show its derivation path', async () => {
      expect(await tooltip(createWrapper(xpubAccount()))).toContain('m/84/0/0');
    });

    /** An xpub has no address to open on a block explorer, so the link only offers a copy. */
    it('should offer only copying rather than a block explorer link', () => {
      const link = createWrapper(xpubAccount()).findComponent({ name: 'HashLink' });

      expect(link.props('displayMode')).toBe('copy');
    });

    it('should link a plain address to its explorer', () => {
      expect(createWrapper().findComponent({ name: 'HashLink' }).props('displayMode')).toBe('default');
    });
  });

  it('should shorten the label to the space it has', () => {
    set(labelWidth, 120);

    expect(shown(createWrapper(account({ label: '' })))).toContain('...');
  });

  it('should blur the label when amounts are hidden', () => {
    set(shouldShowAmount, false);

    expect(createWrapper().find('.blur').exists()).toBe(true);
  });
});
