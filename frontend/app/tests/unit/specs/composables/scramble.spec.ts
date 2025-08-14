import { consistOfNumbers, isValidEthAddress } from '@rotki/common';
import { beforeAll, describe, expect, it } from 'vitest';
import { useScramble } from '@/composables/scramble';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

describe('composables::message-handling', () => {
  let store: ReturnType<typeof useFrontendSettingsStore>;

  beforeAll(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
    store = useFrontendSettingsStore();
  });

  it('should not scramble when the state is off', () => {
    const { scrambleAddress, scrambleIdentifier } = useScramble();

    const hex = '0xabcdef';
    const numbers = '123456';

    expect(scrambleAddress(hex)).toEqual(hex);
    expect(scrambleIdentifier(numbers)).toEqual(numbers);
  });

  it('should scramble hex', async () => {
    await store.updateSetting({ scrambleData: true });
    const { scrambleAddress } = useScramble();

    const address = '0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1';
    const result = scrambleAddress(address);

    expect(result).not.toEqual(address);
    expect(isValidEthAddress(result)).toBeTruthy();
  });

  it('should scramble identifier', async () => {
    await store.updateSetting({ scrambleData: true });
    const { scrambleIdentifier } = useScramble();

    const identifier = '123456';
    const result = scrambleIdentifier(identifier);

    expect(result).not.toEqual(identifier);
    expect(consistOfNumbers(result)).toBeTruthy();
  });
});
