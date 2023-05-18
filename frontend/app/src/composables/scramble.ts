export const useScramble = () => {
  const alphaNumerics =
    '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';

  const {
    scrambleData: scrambleSetting,
    shouldShowAmount,
    scrambleMultiplier
  } = storeToRefs(useSessionSettingsStore());

  const scrambleData = logicOr(scrambleSetting, logicNot(shouldShowAmount));

  const scrambleHex = (hex: string): string => {
    if (!get(scrambleData)) {
      return hex;
    }

    const isEth = hex.startsWith('0x');
    const multiplier = get(scrambleMultiplier);

    const trimmedHex = isEth ? hex.slice(2).toUpperCase() : hex;

    return (
      (isEth ? '0x' : '') +
      trimmedHex
        .split('')
        .map((char, charIndex) => {
          const index = alphaNumerics.indexOf(char);
          if (index === -1) {
            return char;
          }
          return alphaNumerics.charAt(
            Math.floor(index * (multiplier + charIndex)) %
              (isEth ? 16 : alphaNumerics.length)
          );
        })
        .join('')
    );
  };

  const scrambleInteger = (number: number, min = 0, max = -1): number => {
    const multiplied = Math.floor(number * get(scrambleMultiplier)) + min;

    if (max > -1) {
      return (multiplied % (max - min)) + min;
    }

    return multiplied;
  };

  const scrambleIdentifier = (number: number | string): string => {
    const parsed = typeof number === 'string' ? parseInt(number) : number;
    if (!get(scrambleData)) {
      return parsed.toString();
    }

    const min = 10 ** Math.floor(Math.log10(parsed));
    const max = min * 10 - 1;

    return scrambleInteger(parsed, min, max).toString();
  };

  return {
    scrambleData,
    shouldShowAmount,
    scrambleInteger,
    scrambleIdentifier,
    scrambleHex
  };
};
