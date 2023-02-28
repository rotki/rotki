import { useSessionSettingsStore } from '@/store/settings/session';

export const useScramble = () => {
  const alphaNumerics =
    '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';

  const { scrambleData, shouldShowAmount, scrambleMultiplier } = storeToRefs(
    useSessionSettingsStore()
  );

  const scrambleHex = (hex: string): string => {
    const isEth = hex.startsWith('0x');
    const multiplier = get(scrambleMultiplier);

    const trimmedHex = isEth ? hex.slice(2).toUpperCase() : hex;

    return (
      (isEth ? '0x' : '') +
      trimmedHex
        .split('')
        .map((char, charIndex) => {
          const index = alphaNumerics.indexOf(char);
          if (index === -1) return char;
          return alphaNumerics.charAt(
            Math.floor(index * (multiplier + charIndex)) %
              (isEth ? 16 : alphaNumerics.length)
          );
        })
        .join('')
    );
  };

  return {
    scrambleData,
    shouldShowAmount,
    scrambleHex
  };
};
