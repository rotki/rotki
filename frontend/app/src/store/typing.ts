type GettersDefinition<S, G, RS, RG> = {
  [P in keyof G]: (
    state: S,
    getters: G,
    rootState: RS,
    rootGetters: RG
  ) => G[P];
};

export type Getters<S, G, RS, RG> = GettersDefinition<S, G, RS, RG>;
