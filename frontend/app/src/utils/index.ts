import { logger } from '@/utils/logging';

export const startPromise = <T>(promise: Promise<T>) => {
  promise.then().catch(e => logger.debug(e));
};
