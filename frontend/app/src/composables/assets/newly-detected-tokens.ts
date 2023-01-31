import { type Ref } from 'vue';
import { type NewDetectedToken } from '@/types/websocket-messages';

const MAX_SIZE = 500;

const createStorage = (username: string): Ref<NewDetectedToken[]> => {
  return useLocalStorage(`rotki.newly_detected_tokens.${username}`, []);
};

export const useNewlyDetectedTokens = createSharedComposable(() => {
  let tokens: Ref<NewDetectedToken[]> = ref([]);

  const initTokens = (username: string) => {
    tokens = createStorage(username);
  };

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
    initTokens,
    removeNewDetectedTokens,
    addNewDetectedToken
  };
});
