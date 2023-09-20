import {
  TRADE_LOCATION_ARBITRUM_ONE,
  TRADE_LOCATION_BASE,
  TRADE_LOCATION_ETHEREUM,
  TRADE_LOCATION_OPTIMISM,
  TRADE_LOCATION_POLYGON_POS
} from '@/data/defaults';
import { pslSuffixes } from '@/data/psl';
import { Routes } from '@/router/routes';

export const getDomain = (str: string): string => {
  const pattern = /^(?:https?:)?(?:\/\/)?(?:[^\n@]+@)?(?:www\.)?([^\n/:]+)/;
  const exec = pattern.exec(str);

  const withSubdomain = exec?.[1];

  if (!withSubdomain) {
    return str;
  }

  const parts = withSubdomain.split('.');
  const length = parts.length;
  let i = length - 1;
  let domain = withSubdomain;

  while (i > 0) {
    const used = parts.slice(-i).join('.');
    const found = pslSuffixes.has(used);

    if (found) {
      break;
    }

    domain = used;
    i -= 1;
  }

  return domain;
};

/**
 * Returns the registration url of a specified Etherscan location and a path to the local page
 * @param {string} location
 * @returns {{external: string, route: {path: string, hash: string}} | {}}
 */
export const getEtherScanRegisterUrl = (location: string) => {
  switch (location) {
    case TRADE_LOCATION_OPTIMISM:
      return {
        external: 'https://optimistic.etherscan.io/register',
        route: { path: Routes.API_KEYS_EXTERNAL_SERVICES, hash: `#${location}` }
      };
    case TRADE_LOCATION_ETHEREUM:
      return {
        external: 'https://etherscan.io/register',
        route: { path: Routes.API_KEYS_EXTERNAL_SERVICES, hash: `#${location}` }
      };
    case TRADE_LOCATION_POLYGON_POS:
      return {
        external: 'https://polygonscan.com/register',
        route: { path: Routes.API_KEYS_EXTERNAL_SERVICES, hash: `#${location}` }
      };
    case TRADE_LOCATION_ARBITRUM_ONE:
      return {
        external: 'https://arbiscan.io/register',
        route: { path: Routes.API_KEYS_EXTERNAL_SERVICES, hash: `#${location}` }
      };
    case TRADE_LOCATION_BASE:
      return {
        external: 'https://basescan.org/register',
        route: { path: Routes.API_KEYS_EXTERNAL_SERVICES, hash: `#${location}` }
      };
    default:
      logger.warn(`Unsupported etherscan location: '${location}'`);
      return {};
  }
};

/**
 * Returns the registration url of a specified service location and a path to the local page
 * @param {string} service
 * @param {string} location
 * @returns {{} | {external: string, route: {path: string, hash: string}}}
 */
export const getServiceRegisterUrl = (service: string, location: string) => {
  switch (service) {
    case 'etherscan':
      return getEtherScanRegisterUrl(location);
    default:
      logger.warn(`Unsupported service: '${service}'`);
      return {};
  }
};
