describe('composables::message-handling', () => {
  let store: ReturnType<typeof useSessionSettingsStore>;

  beforeAll(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
    store = useSessionSettingsStore();
  });

  test('Should not scramble when the state is off', () => {
    const { scrambleHex, scrambleIdentifier } = useScramble();

    const hex = '0xabcdef';
    const numbers = '123456';

    expect(scrambleHex(hex)).toEqual(hex);
    expect(scrambleIdentifier(numbers)).toEqual(numbers);
  });

  test('Should scramble hex', () => {
    store.update({ scrambleData: true });
    const { scrambleHex } = useScramble();

    const address = '0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1';
    const result = scrambleHex(address);

    expect(result).not.toEqual(address);
    expect(isValidEthAddress(result)).toBeTruthy();
  });

  test('Should scramble identifier', () => {
    store.update({ scrambleData: true });
    const { scrambleIdentifier } = useScramble();

    const identifier = '123456';
    const result = scrambleIdentifier(identifier);

    expect(result).not.toEqual(identifier);
    expect(consistOfNumbers(result)).toBeTruthy();
  });
});
