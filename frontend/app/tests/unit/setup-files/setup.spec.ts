import { describe, expect, it } from 'vitest';
import { useRoute, useRouter } from 'vue-router';

describe('the global vue-router mock', () => {
  it.each(['push', 'replace'] as const)('should expose %s and write the query back to the route', async (method) => {
    const router = useRouter();
    const route = useRoute();

    await router[method]({ query: { add: 'true' } });

    expect(get(route).query).toStrictEqual({ add: 'true' });
  });
});
