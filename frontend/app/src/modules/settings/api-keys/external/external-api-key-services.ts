import type { ExternalServiceName } from '@/modules/integrations/types';
import { NotificationCategory } from '@rotki/common';
import { blockscoutLink, etherscanLink, externalLinks, heliusLink } from '@shared/external-links';
import { type MessageKey, msg } from '@/message-key';

/**
 * How saving a key clears the notification that asked for it.
 *
 * @remarks
 * A service that owns a notification category is dismissed by that category. One whose notification
 * sits in a shared category is found by the service name the message interpolates.
 */
type KeyRequestDismissal =
  | { readonly category: NotificationCategory }
  | { readonly byServiceName: true };

/** One external service whose api key is entered through a plain key card. */
export interface ExternalApiKeyService {
  readonly name: ExternalServiceName;
  readonly title: MessageKey;
  readonly description: MessageKey;
  readonly hint: MessageKey;
  /** File name inside the public services image folder. */
  readonly image: string;
  /** Where a key is obtained; a service without one shows no link. */
  readonly link?: string;
  readonly roundedIcon?: boolean;
  readonly dismissal?: KeyRequestDismissal;
}

export const EXTERNAL_API_KEY_SERVICES = {
  alchemy: {
    description: msg.$t('external_services.alchemy.description'),
    hint: msg.$t('external_services.alchemy.hint'),
    image: 'alchemy.svg',
    link: externalLinks.alchemyApiKey,
    name: 'alchemy',
    title: msg.$t('external_services.alchemy.title'),
  },
  beaconchain: {
    description: msg.$t('external_services.beaconchain.description'),
    dismissal: { category: NotificationCategory.BEACONCHAIN },
    hint: msg.$t('external_services.beaconchain.hint'),
    image: 'beaconchain.svg',
    link: 'https://beaconcha.in/user/settings',
    name: 'beaconchain',
    roundedIcon: true,
    title: msg.$t('external_services.beaconchain.title'),
  },
  birdeye: {
    description: msg.$t('external_services.birdeye.description'),
    hint: msg.$t('external_services.birdeye.hint'),
    image: 'birdeye.png',
    link: externalLinks.birdeyeApiKey,
    name: 'birdeye',
    title: msg.$t('external_services.birdeye.title'),
  },
  blockscout: {
    description: msg.$t('external_services.blockscout.description'),
    hint: msg.$t('external_services.blockscout.hint'),
    image: 'blockscout.svg',
    link: blockscoutLink,
    name: 'blockscout',
    title: msg.$t('external_services.blockscout.title'),
  },
  coingecko: {
    description: msg.$t('external_services.coingecko.description'),
    hint: msg.$t('external_services.coingecko.hint'),
    image: 'coingecko.svg',
    link: externalLinks.coingeckoApiKey,
    name: 'coingecko',
    title: msg.$t('external_services.coingecko.title'),
  },
  cryptocompare: {
    description: msg.$t('external_services.cryptocompare.description'),
    hint: msg.$t('external_services.cryptocompare.hint'),
    image: 'cryptocompare.svg',
    name: 'cryptocompare',
    title: msg.$t('external_services.cryptocompare.title'),
  },
  defillama: {
    description: msg.$t('external_services.defillama.description'),
    hint: msg.$t('external_services.defillama.hint'),
    image: 'defillama.svg',
    link: externalLinks.defillamaApiKey,
    name: 'defillama',
    title: msg.$t('external_services.defillama.title'),
  },
  etherscan: {
    description: msg.$t('external_services.etherscan.description'),
    dismissal: { category: NotificationCategory.ETHERSCAN },
    hint: msg.$t('external_services.etherscan.hint'),
    image: 'etherscan.svg',
    link: etherscanLink,
    name: 'etherscan',
    title: msg.$t('external_services.etherscan.title'),
  },
  helius: {
    description: msg.$t('external_services.helius.description'),
    dismissal: { category: NotificationCategory.HELIUS },
    hint: msg.$t('external_services.helius.hint'),
    image: 'helius.svg',
    link: heliusLink,
    name: 'helius',
    title: msg.$t('external_services.helius.title'),
  },
  moralis: {
    description: msg.$t('external_services.moralis.description'),
    hint: msg.$t('external_services.moralis.hint'),
    image: 'moralis.png',
    link: externalLinks.moralisApiKey,
    name: 'moralis',
    title: msg.$t('external_services.moralis.title'),
  },
  opensea: {
    description: msg.$t('external_services.opensea.description'),
    hint: msg.$t('external_services.opensea.hint'),
    image: 'opensea.svg',
    link: externalLinks.openSeaApiKeyReference,
    name: 'opensea',
    title: msg.$t('external_services.opensea.title'),
  },
  thegraph: {
    description: msg.$t('external_services.thegraph.description'),
    dismissal: { byServiceName: true },
    hint: msg.$t('external_services.thegraph.hint'),
    image: 'thegraph.svg',
    link: externalLinks.applyTheGraphApiKey,
    name: 'thegraph',
    title: msg.$t('external_services.thegraph.title'),
  },
} as const satisfies Record<string, ExternalApiKeyService>;
