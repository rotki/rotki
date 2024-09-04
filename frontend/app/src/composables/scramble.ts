interface UseScrambleReturn {
  scrambleData: ComputedRef<boolean>;
  shouldShowAmount: ComputedRef<boolean>;
  scrambleInteger: (number: number, min?: number, max?: number) => number;
  scrambleIdentifier: (number: number | string, lowerBound?: number, upperBound?: number) => string;
  scrambleAddress: (address: string) => string;
  scrambleTimestamp: (timestamp: number, milliseconds?: boolean) => number;
}

export function useScramble(): UseScrambleReturn {
  const alphaNumerics = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';

  const {
    scrambleData: scrambleSetting,
    shouldShowAmount,
    scrambleMultiplier,
  } = storeToRefs(useSessionSettingsStore());

  const scrambleData = logicOr(scrambleSetting, logicNot(shouldShowAmount));

  const scrambleAddress = (address: string): string => {
    if (!get(scrambleData))
      return address;

    let multiplier = +get(scrambleMultiplier);
    if (multiplier < 1)
      multiplier += 1;

    const knownPrefix = findAddressKnownPrefix(address);

    const trimmedAddress = knownPrefix ? address.slice(knownPrefix.length).toUpperCase() : address;
    const isHex = address.startsWith('0x');

    return (
      knownPrefix
      + trimmedAddress
        .split('')
        .map((char, charIndex) => {
          const index = alphaNumerics.indexOf(char);
          if (index === -1)
            return char;

          return alphaNumerics.charAt(
            Math.floor(index * (multiplier + charIndex)) % (isHex ? 16 : alphaNumerics.length),
          );
        })
        .join('')
    );
  };

  const scrambleInteger = (number: number, min = 0, max = -1): number => {
    const multiplied = Math.floor(number * number * get(scrambleMultiplier)) + min;

    if (max > -1)
      return (multiplied % (max - min)) + min;

    return multiplied;
  };

  const scrambleIdentifier = (number: number | string, lowerBound = 100000, upperBound = 999999): string => {
    const parsed = typeof number === 'string' ? parseInt(number) : number;
    if (!get(scrambleData))
      return parsed.toString();

    const min = Math.max(lowerBound, 10 ** Math.floor(Math.log10(parsed)));
    const max = Math.max(upperBound, min * 10);

    return scrambleInteger(parsed, min, max).toString();
  };

  const scrambleTimestamp = (timestamp: number, milliseconds: boolean = false): number => {
    if (!get(scrambleData))
      return timestamp;

    const currentTimestamp = Date.now();
    const diff = (milliseconds ? timestamp : timestamp * 1000) - currentTimestamp;
    let multiplier = +get(scrambleMultiplier);
    if (multiplier < 1)
      multiplier += 1;

    return Math.round(timestamp + (diff * multiplier * multiplier) / (milliseconds ? 1 : 1000));
  };

  return {
    scrambleData,
    shouldShowAmount,
    scrambleInteger,
    scrambleIdentifier,
    scrambleAddress,
    scrambleTimestamp,
  };
}
