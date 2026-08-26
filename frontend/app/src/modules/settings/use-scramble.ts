import type { ComputedRef, Ref } from 'vue';
import { findAddressKnownPrefix } from '@/modules/core/common/display/truncate';
import { generateRandomScrambleMultiplier } from '@/modules/session/session-utils';
import { useSetting } from '@/modules/settings/use-setting';

interface UseScrambleReturn {
  scrambleData: ComputedRef<boolean>;
  shouldShowAmount: Readonly<Ref<boolean>>;
  scrambleInteger: (number: number, min?: number, max?: number) => number;
  scrambleIdentifier: (number: number | string, lowerBound?: number, upperBound?: number) => string;
  scrambleAddress: (address: string) => string;
  scrambleTimestamp: (timestamp: number, milliseconds?: boolean) => number;
}

export function useScramble(): UseScrambleReturn {
  const alphaNumerics = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';

  const scrambleSetting = useSetting('scrambleData');
  const scrambleMultiplierRef = useSetting('scrambleMultiplier');
  const shouldShowAmount = useSetting('shouldShowAmount');

  const scrambleMultiplier = ref<number>(get(scrambleMultiplierRef) ?? generateRandomScrambleMultiplier());

  watchEffect(() => {
    const newValue = get(scrambleMultiplierRef);
    if (newValue !== undefined)
      set(scrambleMultiplier, newValue);
  });

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

    let multiplier = +get(scrambleMultiplier);
    if (multiplier < 1)
      multiplier += 1;

    /**
     * Deterministic offset built from prime factors, so every date component is scrambled: day,
     * month, year, hour, minute and second. Past dates stay past and future dates stay future.
     *
     * A pure offset also preserves ordering, so a date that sorted before another still does after
     * scrambling.
     */
    const offsetSeconds = multiplier * 13 * 86400
      + multiplier * 7 * 3600
      + multiplier * 23 * 60
      + multiplier * 37;

    const nowSeconds = Math.round(Date.now() / 1000);
    const tsSeconds = milliseconds ? Math.round(timestamp / 1000) : timestamp;
    const direction = tsSeconds <= nowSeconds ? -1 : 1;

    return Math.round(timestamp + direction * offsetSeconds * (milliseconds ? 1000 : 1));
  };

  return {
    scrambleAddress,
    scrambleData,
    scrambleIdentifier,
    scrambleInteger,
    scrambleTimestamp,
    shouldShowAmount,
  };
}
