from rotkehlchen.chain.solana.decoding.constants import ANCHOR_DISCRIMINATOR_LEN


def match_discriminator(
        data: bytes,
        discriminator: bytes,
        discriminator_len: int = ANCHOR_DISCRIMINATOR_LEN,
) -> bool:
    """Checks if the data starts with the specified discriminator."""
    return data[:discriminator_len] == discriminator


def get_data_for_discriminator(
        data: bytes,
        discriminator: bytes,
        discriminator_len: int = 8,
) -> bytes | None:
    """Extracts the data after the discriminator from the instruction data.
    Returns None if the discriminator is not found.
    """
    return data[discriminator_len:] if match_discriminator(
        data=data,
        discriminator=discriminator,
        discriminator_len=discriminator_len,
    ) else None
