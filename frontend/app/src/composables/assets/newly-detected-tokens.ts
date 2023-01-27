import { type Ref } from 'vue';
import { type NewDetectedToken } from '@/types/websocket-messages';

const MAX_SIZE = 500;

export const useNewlyDetectedTokens = createSharedComposable(() => {
  const tokens: Ref<NewDetectedToken[]> = useLocalStorage(
    'rotki.newly_detected_tokens',
    []
  );

  const addNewDetectedToken = (data: NewDetectedToken) => {
    const tokenList = [...get(tokens)];
    const tokenIndex = tokenList.findIndex(
      ({ tokenIdentifier }) => tokenIdentifier === data.tokenIdentifier
    );
    if (tokenIndex === -1) {
      tokenList.push(data);
    } else {
      tokenList.splice(tokenIndex, 1, data);
    }
    set(tokens, tokenList.slice(-MAX_SIZE));
  };

  const removeNewDetectedTokens = (tokensToRemove: string[]) => {
    const filtered = get(tokens).filter(
      item => !tokensToRemove.includes(item.tokenIdentifier)
    );

    set(tokens, filtered);
  };

  return {
    tokens,
    removeNewDetectedTokens,
    addNewDetectedToken
  };
});
