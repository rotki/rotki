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
    let multiplier = +get(scrambleMultiplier);
    if (multiplier < 1) {
      multiplier += 1;
    }

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
    const multiplied =
      Math.floor(number * number * get(scrambleMultiplier)) + min;

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

    const min = Math.max(100000, 10 ** Math.floor(Math.log10(parsed)));
    const max = Math.max(999999, min * 10);

    return scrambleInteger(parsed, min, max).toString();
  };

  const scrambleTimestamp = (timestamp: number) => {
    if (!get(scrambleData)) {
      return timestamp;
    }

    const currentTimestamp = Date.now() / 1000;
    const diff = timestamp - currentTimestamp;
    let multiplier = +get(scrambleMultiplier);
    if (multiplier < 1) {
      multiplier += 1;
    }

    return Math.round(timestamp + diff * multiplier * multiplier);
  };

  return {
    scrambleData,
    shouldShowAmount,
    scrambleInteger,
    scrambleIdentifier,
    scrambleHex,
    scrambleTimestamp
  };
};
