"""The Jablotron integration."""

from homeassistant.const import Platform
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from typing import Final

from .const import (
	DATA_JABLOTRON,
	DATA_OPTIONS_UPDATE_UNSUBSCRIBER,
	DOMAIN,
	LOGGER,
)
from .jablotron import Jablotron

PLATFORMS: Final = [
	Platform.ALARM_CONTROL_PANEL,
	Platform.BINARY_SENSOR,
	Platform.SENSOR,
	Platform.SWITCH
];

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
	hass.data.setdefault(DOMAIN, {})

	jablotron_instance: Jablotron = Jablotron(hass, config_entry.entry_id, config_entry.data, config_entry.options)
	await jablotron_instance.initialize()

	hass.data[DOMAIN][config_entry.entry_id] = {
		DATA_JABLOTRON: jablotron_instance,
		DATA_OPTIONS_UPDATE_UNSUBSCRIBER: config_entry.add_update_listener(options_update_listener),
	}

	central_unit = jablotron_instance.central_unit()
	device_registry = dr.async_get(hass)

	device_registry.async_get_or_create(
		config_entry_id=config_entry.entry_id,
		identifiers={(DOMAIN, central_unit.unique_id)},
		name="Jablotron 100",
		model="{} ({})".format(central_unit.model, central_unit.hardware_version),
		manufacturer="Jablotron",
		sw_version=central_unit.firmware_version,
	)

	await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

	return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
	await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)

	data = hass.data[DOMAIN].pop(config_entry.entry_id)

	options_update_unsubscriber = data[DATA_OPTIONS_UPDATE_UNSUBSCRIBER]
	options_update_unsubscriber()

	jablotron_instance: Jablotron = data[DATA_JABLOTRON]
	jablotron_instance.shutdown_and_clean()

	return True


async def options_update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
	jablotron_instance: Jablotron = hass.data[DOMAIN][config_entry.entry_id][DATA_JABLOTRON]

	await jablotron_instance.update_config_and_options(config_entry.data, config_entry.options)

	async_dispatcher_send(hass, jablotron_instance.signal_entities_added())
