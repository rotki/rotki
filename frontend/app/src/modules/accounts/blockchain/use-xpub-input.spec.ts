import { Blockchain } from '@rotki/common';
import { describe, expect, it, vi } from 'vitest';
import { XpubKeyType, type XpubPayload } from '@/modules/accounts/blockchain-accounts';
import { useXpubInput, type XpubFormState } from '@/modules/accounts/blockchain/use-xpub-input';

function setup(payload?: XpubPayload): { model: Ref<XpubPayload | undefined>; state: XpubFormState } {
  const state = reactive<XpubFormState>({ derivationPath: '', xpub: '' });
  const model = ref<XpubPayload | undefined>(payload);

  useXpubInput(state, model, {
    blockchain: Blockchain.BTC,
    disabled: false,
    onAddressDetected: vi.fn(),
  });

  return { model, state };
}

describe('useXpubInput', () => {
  it('should keep the apostrophes the user typed when the path means the same thing', async () => {
    const { model, state } = setup();
    state.derivationPath = `m/44'/0'/0'`;
    await nextTick();

    set(model, { derivationPath: 'm/44/0/0', xpub: 'xpub6C', xpubType: XpubKeyType.XPUB });
    await nextTick();

    expect(state.derivationPath).toBe(`m/44'/0'/0'`);
  });

  it('should adopt a derivation path that means something different', async () => {
    const { model, state } = setup();
    state.derivationPath = `m/44'/0'/0'`;
    await nextTick();

    set(model, { derivationPath: 'm/84/0/0', xpub: 'xpub6C', xpubType: XpubKeyType.XPUB });
    await nextTick();

    expect(state.derivationPath).toBe('m/84/0/0');
  });

  it('should write the payload xpub into the field', async () => {
    const { model, state } = setup();

    set(model, { derivationPath: '', xpub: 'xpub6CUGRUon', xpubType: XpubKeyType.XPUB });
    await nextTick();

    expect(state.xpub).toBe('xpub6CUGRUon');
  });
});
