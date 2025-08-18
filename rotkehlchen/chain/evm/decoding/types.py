from typing import NamedTuple


class CounterpartyDetails(NamedTuple):
    """
    Details for a counterparty returned to the api consumer.

    The icon is used when the counterparty uses an icon from the icon package instead of
    a preselected image.
    """
    identifier: str
    label: str
    image: str | None = None
    darkmode_image: str | None = None
    icon: str | None = None

    def serialize(self) -> dict[str, str]:
        data = {'identifier': self.identifier, 'label': self.label}
        if self.image is not None:
            data['image'] = self.image
        if self.darkmode_image is not None:
            data['darkmode_image'] = self.darkmode_image
        if self.icon is not None:
            data['icon'] = self.icon

        return data

    @classmethod
    def from_versioned_counterparty(
            cls,
            counterparty: str,
            image: str | None = None,
            darkmode_image: str | None = None,
            icon: str | None = None,
    ) -> 'CounterpartyDetails':
        """Create a CounterpartyDetails from a counterparty identifier
        ending with '-vX' where X is the version number.
        """
        return cls(
            identifier=counterparty,
            label=counterparty.capitalize().replace('-v', ' V'),
            image=image,
            darkmode_image=darkmode_image,
            icon=icon,
        )
