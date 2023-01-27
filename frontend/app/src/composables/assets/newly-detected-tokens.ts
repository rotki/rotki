import { type Ref } from 'vue';
import { uniqueStrings } from '@/utils/data';

const MAX_SIZE = 500;

export const useNewlyDetectedTokens = createSharedComposable(() => {
  const tokens: Ref<string[]> = useLocalStorage(
    'rotki.newly_detected_tokens',
    []
  );

  const addNewDetectedToken = (identifier: string) => {
    set(
      tokens,
      [identifier, ...get(tokens)].filter(uniqueStrings).slice(0, MAX_SIZE)
    );
  };

  const removeNewDetectedTokens = (tokensToRemove: string[]) => {
    const filtered = get(tokens).filter(item => !tokensToRemove.includes(item));

    set(tokens, filtered);
  };

  return {
    tokens,
    removeNewDetectedTokens,
    addNewDetectedToken
  };
});
