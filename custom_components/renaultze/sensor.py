"""Support for MyRenault services."""

import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from .myrenaultservice.MyRenaultService import (
    MyRenaultService,
    MyRenaultServiceException
    )

import voluptuous as vol

from homeassistant.helpers.entity import Entity

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_NAME

_LOGGER = logging.getLogger(__name__)

ATTR_CHARGING = 'charging'
ATTR_PLUGGED = 'plugged'
ATTR_CHARGE_LEVEL = 'charge_level'
ATTR_REMAINING_RANGE = 'remaining_range'
ATTR_LAST_UPDATE = 'last_update'
ATTR_BATTERY_TEMPERATURE = 'battery_temperature'
ATTR_MILEAGE = 'mileage'

CONF_VIN = 'vin'
CONF_ANDROID_LNG = 'android_lng'

SCAN_INTERVAL = timedelta(seconds=60)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_VIN): cv.string,
    vol.Optional(CONF_ANDROID_LNG, default='fr_FR'): cv.string,
    vol.Optional(CONF_NAME, default=None): cv.string,
})


async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Setup the sensor platform."""
    _LOGGER.debug("Initialising renaultze platform")
    wrapper = MyRenaultService(config.get(CONF_USERNAME),
                               config.get(CONF_PASSWORD))
    await wrapper.initialise_configuration(config.get(CONF_ANDROID_LNG))

    devices = [
        RenaultZESensor(wrapper,
                        config.get(CONF_VIN),
                        config.get(CONF_NAME, config.get(CONF_VIN))
                        )
        ]
    async_add_entities(devices)


class RenaultZESensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, wrapper, vin, name):
        """Initialize the sensor."""
        _LOGGER.debug("Initialising RenaultZESensor %s" % name)
        self._state = None
        self._wrapper = wrapper
        self._vin = vin
        self._name = name
        self._attrs = {}
        self._lastdeepupdate = 0

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        return self._attrs

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return '%'

    def process_battery_response(self, jsonresult):
        """Update new state data for the sensor."""
        self._state = jsonresult['batteryLevel']

        self._attrs[ATTR_CHARGING] = jsonresult['chargeStatus'] > 0
        self._attrs[ATTR_LAST_UPDATE] = jsonresult['lastUpdateTime']
        self._attrs[ATTR_PLUGGED] = jsonresult['plugStatus'] > 0
        if "batteryTemperature" in jsonresult:
            self._attrs[ATTR_BATTERY_TEMPERATURE] = jsonresult["batteryTemperature"]
        self._attrs[ATTR_REMAINING_RANGE] = jsonresult['rangeHvacOff']

    def process_mileage_response(self, jsonresult):
        """Update new state data for the sensor."""
        self._attrs[ATTR_MILEAGE] = jsonresult['totalMileage']

    async def async_update(self):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        # Run standard update
        try:
            jsonresult = await self._wrapper.apiGetBatteryStatus(self._vin)
            _LOGGER.debug("Battery update result: %s" % jsonresult)
            self.process_battery_response(jsonresult['data']['attributes'])
        except MyRenaultServiceException as e:
            _LOGGER.error("Battery update failed: %s" % e)

        try:
            jsonresult = await self._wrapper.apiGetMileage(self._vin)
            _LOGGER.debug("Mileage update result: %s" % jsonresult)
            self.process_mileage_response(jsonresult['data']['attributes'])
        except MyRenaultServiceException as e:
            _LOGGER.error("Mileage update failed: %s" % e)