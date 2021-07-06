import * as logger from 'loglevel';
import { DEBUG } from '@/utils/log-level';

if (process.env.NODE_ENV === 'development') {
  logger.setDefaultLevel(DEBUG);
}
