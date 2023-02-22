import { useSessionSettingsStore } from '@/store/settings/session';

export const useScramble = () => {
  const alphaNumerics =
    '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';

  const { scrambleData, shouldShowAmount, scrambleMultiplier } = storeToRefs(
    useSessionSettingsStore()
  );

  const scrambleHex = (hex: string): string => {
    const isEth = hex.startsWith('0x');
    const multiplier = get(scrambleMultiplier) * 100;

    const trimmedHex = isEth ? hex.slice(2).toUpperCase() : hex;

    return (
      (isEth ? '0x' : '') +
      trimmedHex
        .split('')
        .map(char => {
          const index = alphaNumerics.indexOf(char);
          if (index === -1) {
            return char;
          }
          return alphaNumerics.charAt(
            Math.floor(index * multiplier * 100) %
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
