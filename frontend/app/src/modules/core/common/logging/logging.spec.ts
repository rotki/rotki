import { LogLevels, type LogObject } from 'consola';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { RequestCancelledError } from '@/modules/core/api/request-queue/errors';
import { logger } from './logging';

describe('logger', () => {
  const logged: string[] = [];
  const reporter = {
    log: (logObj: LogObject): void => {
      logged.push(logObj.type);
    },
  };
  let level: number;

  beforeEach(() => {
    logged.length = 0;
    level = logger.level;
    logger.level = LogLevels.debug;
    logger.addReporter(reporter);
  });

  afterEach(() => {
    logger.removeReporter(reporter);
    logger.level = level;
  });

  it('should log an error carrying a cancelled request at debug', () => {
    logger.error('Failed to fetch tags:', new RequestCancelledError('No live session'));

    expect(logged).toEqual(['debug']);
  });

  it('should log a warning carrying a cancelled request at debug', () => {
    logger.warn(new RequestCancelledError('Request cancelled'));

    expect(logged).toEqual(['debug']);
  });

  it('should log a real failure as an error', () => {
    logger.error('Failed to fetch tags:', new Error('backend down'));

    expect(logged).toEqual(['error']);
  });
});
