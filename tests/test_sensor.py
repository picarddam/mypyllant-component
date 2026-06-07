import pytest as pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from homeassistant.helpers.entity_registry import DATA_REGISTRY, EntityRegistry
from homeassistant.helpers.recorder import DATA_INSTANCE
from homeassistant.loader import DATA_COMPONENTS, DATA_INTEGRATIONS

from myPyllant.api import MyPyllantAPI
from myPyllant.models import DeviceData, DeviceDataBucket
from myPyllant.enums import CircuitState
from myPyllant.tests.generate_test_data import DATA_DIR
from myPyllant.tests.utils import list_test_data, load_test_data

from custom_components.mypyllant.sensor import (
    CircuitFlowTemperatureSensor,
    CircuitHeatingCurveSensor,
    CircuitMinFlowTemperatureSetpointSensor,
    CircuitStateSensor,
    DataSensor,
    DomesticHotWaterCurrentSpecialFunctionSensor,
    DomesticHotWaterOperationModeSensor,
    DomesticHotWaterSetPointSensor,
    DomesticHotWaterTankTemperatureSensor,
    HomeEntity,
    SystemOutdoorTemperatureSensor,
    ZoneCurrentRoomTemperatureSensor,
    ZoneCurrentSpecialFunctionSensor,
    ZoneDesiredRoomTemperatureSetpointSensor,
    ZoneHeatingOperatingModeSensor,
    ZoneHumiditySensor,
    SystemDeviceOnOffCyclesSensor,
    SystemDeviceOperationTimeSensor,
    create_system_sensors,
    SystemTopDHWTemperatureSensor,
    SystemBottomDHWTemperatureSensor,
    SystemTopCHTemperatureSensor,
    SystemDeviceCurrentPowerSensor,
)
from custom_components.mypyllant.const import DOMAIN
from tests.utils import get_config_entry


@pytest.mark.parametrize("test_data", list_test_data())
async def test_create_system_sensors(
    hass,
    mypyllant_aioresponses,
    mocked_api: MyPyllantAPI,
    system_coordinator_mock,
    test_data,
):
    hass.data[DATA_COMPONENTS] = {}
    hass.data[DATA_INTEGRATIONS] = {}
    hass.data[DATA_REGISTRY] = EntityRegistry(hass)
    with mypyllant_aioresponses(test_data) as _:
        config_entry = get_config_entry()
        system_coordinator_mock.data = (
            await system_coordinator_mock._async_update_data()
        )
        hass.data[DOMAIN] = {
            config_entry.entry_id: {"system_coordinator": system_coordinator_mock}
        }
        sensors = await create_system_sensors(hass, config_entry)
        assert len(sensors) > 0

        await mocked_api.aiohttp_session.close()


@pytest.mark.parametrize("test_data", list_test_data())
async def test_system_sensors(
    mypyllant_aioresponses, mocked_api: MyPyllantAPI, system_coordinator_mock, test_data
):
    with mypyllant_aioresponses(test_data) as _:
        system_coordinator_mock.data = (
            await system_coordinator_mock._async_update_data()
        )
        if "outdoorTemperature" in str(test_data):
            assert isinstance(
                SystemOutdoorTemperatureSensor(0, system_coordinator_mock).native_value,
                float,
            )
        # TODO: No water pressure in no_cooling.yaml
        # assert isinstance(
        #    SystemWaterPressureSensor(0, system_coordinator_mock).native_value, float
        # )

        home = HomeEntity(0, system_coordinator_mock)
        assert isinstance(home.device_info, dict)
        assert (
            home.extra_state_attributes
            and "controller_type" in home.extra_state_attributes
        )

        await mocked_api.aiohttp_session.close()


async def test_zone_sensors(
    hass,
    mypyllant_aioresponses,
    mocked_api: MyPyllantAPI,
    system_coordinator_mock,
):
    test_data = load_test_data(DATA_DIR / "heatpump_cooling")
    with mypyllant_aioresponses(test_data) as _:
        system_coordinator_mock.data = (
            await system_coordinator_mock._async_update_data()
        )
        if "humidity" in str(test_data):
            assert isinstance(
                ZoneHumiditySensor(0, 0, system_coordinator_mock).native_value, float
            )
        if "currentTemperature" in str(test_data):
            assert isinstance(
                ZoneCurrentRoomTemperatureSensor(
                    0, 0, system_coordinator_mock
                ).native_value,
                float,
            )
        assert isinstance(
            ZoneDesiredRoomTemperatureSetpointSensor(
                0, 0, system_coordinator_mock
            ).native_value,
            float | int,
        )
        assert isinstance(
            ZoneCurrentSpecialFunctionSensor(
                0, 0, system_coordinator_mock
            ).native_value,
            str,
        )
        assert isinstance(
            ZoneHeatingOperatingModeSensor(0, 0, system_coordinator_mock).native_value,
            str,
        )
        await mocked_api.aiohttp_session.close()


@pytest.mark.parametrize("test_data", list_test_data())
async def test_circuit_sensors(
    mypyllant_aioresponses, mocked_api: MyPyllantAPI, system_coordinator_mock, test_data
):
    with mypyllant_aioresponses(test_data) as _:
        system_coordinator_mock.data = (
            await system_coordinator_mock._async_update_data()
        )
        circuit_state = CircuitStateSensor(0, 0, system_coordinator_mock)
        assert isinstance(circuit_state.native_value, CircuitState)
        assert isinstance(circuit_state.extra_state_attributes, dict)
        if "room_temperature_control_mode" in test_data:
            assert (
                "room_temperature_control_mode" in circuit_state.extra_state_attributes
            )
        assert isinstance(
            CircuitFlowTemperatureSensor(0, 0, system_coordinator_mock).native_value,
            (int, float, complex),
        )
        if "heatingCurve" in str(test_data):
            assert isinstance(
                CircuitHeatingCurveSensor(0, 0, system_coordinator_mock).native_value,
                (int, float, complex),
            )
        if "minFlowTemperatureSetpoint" in str(test_data):
            assert isinstance(
                CircuitMinFlowTemperatureSetpointSensor(
                    0, 0, system_coordinator_mock
                ).native_value,
                (int, float, complex),
            )
        await mocked_api.aiohttp_session.close()


@pytest.mark.parametrize("test_data", list_test_data())
async def test_domestic_hot_water_sensor(
    hass,
    mypyllant_aioresponses,
    mocked_api: MyPyllantAPI,
    system_coordinator_mock,
    test_data,
):
    with mypyllant_aioresponses(test_data) as _:
        system_coordinator_mock.data = (
            await system_coordinator_mock._async_update_data()
        )
        if not system_coordinator_mock.data[0].domestic_hot_water:
            await mocked_api.aiohttp_session.close()
            pytest.skip(
                f"No DHW in system {system_coordinator_mock.data[0]}, skipping DHW sensors"
            )
        assert isinstance(
            DomesticHotWaterOperationModeSensor(
                0, 0, system_coordinator_mock
            ).native_value,
            str,
        )
        assert isinstance(
            DomesticHotWaterSetPointSensor(0, 0, system_coordinator_mock).native_value,
            (int, float, complex),
        )
        assert isinstance(
            DomesticHotWaterCurrentSpecialFunctionSensor(
                0, 0, system_coordinator_mock
            ).native_value,
            str,
        )
        if "currentDhwTankTemperature" in str(test_data):
            assert isinstance(
                DomesticHotWaterTankTemperatureSensor(
                    0, 0, system_coordinator_mock
                ).native_value,
                float,
            )
        await mocked_api.aiohttp_session.close()


@pytest.mark.parametrize("test_data", list_test_data())
async def test_data_sensor(
    mypyllant_aioresponses,
    mocked_api: MyPyllantAPI,
    daily_data_coordinator_mock,
    test_data,
):
    with mypyllant_aioresponses(test_data) as _:
        system_coordinator = daily_data_coordinator_mock.hass_data["system_coordinator"]
        system_coordinator.data = await system_coordinator._async_update_data()
        daily_data_coordinator_mock.data = (
            await daily_data_coordinator_mock._async_update_data()
        )
        system_id = next(iter(daily_data_coordinator_mock.data), None)
        if system_id is None or not daily_data_coordinator_mock.data[system_id]:
            await mocked_api.aiohttp_session.close()
            pytest.skip(f"No devices in system {system_id}, skipping data sensor tests")
        data_sensor = DataSensor(system_id, 0, 0, daily_data_coordinator_mock)
        assert isinstance(
            data_sensor.device_data,
            DeviceData,
        )
        assert isinstance(
            data_sensor.native_value,
            (int, float, complex),
        )
        assert isinstance(
            data_sensor.name,
            str,
        )
        assert data_sensor.last_reset is None
        await mocked_api.aiohttp_session.close()


async def test_device_sensor(
    mypyllant_aioresponses,
    mocked_api: MyPyllantAPI,
    system_coordinator_mock,
):
    test_data = load_test_data(DATA_DIR / "vrc700_mpc_rts.yaml")
    with mypyllant_aioresponses(test_data) as _:
        system_coordinator_mock.data = (
            await system_coordinator_mock._async_update_data()
        )
        assert isinstance(
            SystemDeviceOnOffCyclesSensor(0, 0, system_coordinator_mock).native_value,
            int,
        )
        assert isinstance(
            SystemDeviceOperationTimeSensor(0, 0, system_coordinator_mock).native_value,
            float,
        )
        assert isinstance(
            SystemDeviceCurrentPowerSensor(0, 0, system_coordinator_mock).native_value,
            int,
        )
        await mocked_api.aiohttp_session.close()


async def test_additional_system_sensors(
    mypyllant_aioresponses,
    mocked_api: MyPyllantAPI,
    system_coordinator_mock,
):
    test_data = load_test_data(DATA_DIR / "two_systems")
    with mypyllant_aioresponses(test_data) as _:
        system_coordinator_mock.data = (
            await system_coordinator_mock._async_update_data()
        )
        assert isinstance(
            SystemTopDHWTemperatureSensor(0, system_coordinator_mock).native_value,
            float,
        )
        assert isinstance(
            SystemBottomDHWTemperatureSensor(0, system_coordinator_mock).native_value,
            float,
        )
        assert isinstance(
            SystemTopCHTemperatureSensor(0, system_coordinator_mock).native_value,
            float,
        )
        await mocked_api.aiohttp_session.close()


@pytest.mark.parametrize("test_data", list_test_data())
async def test_push_external_statistics(
    hass,
    mypyllant_aioresponses,
    mocked_api: MyPyllantAPI,
    daily_data_coordinator_mock,
    test_data,
):
    """Test that _push_external_statistics is called with correct metadata and data."""
    with mypyllant_aioresponses(test_data) as _:
        system_coordinator = daily_data_coordinator_mock.hass_data["system_coordinator"]
        system_coordinator.data = await system_coordinator._async_update_data()
        daily_data_coordinator_mock.data = (
            await daily_data_coordinator_mock._async_update_data()
        )
        system_id = next(iter(daily_data_coordinator_mock.data), None)
        if system_id is None or not daily_data_coordinator_mock.data[system_id]:
            await mocked_api.aiohttp_session.close()
            pytest.skip(f"No devices in system {system_id}, skipping recorder tests")

        assert system_id is not None  # Help type checker after pytest.skip

        # Set up recorder instance marker
        daily_data_coordinator_mock.hass.data[DATA_INSTANCE] = MagicMock()

        data_sensor = DataSensor(system_id, 0, 0, daily_data_coordinator_mock)
        data_sensor.hass = daily_data_coordinator_mock.hass

        with patch(
            "custom_components.mypyllant.sensor.async_add_external_statistics"
        ) as mock_add_stats:
            data_sensor._push_external_statistics()

            # Verify called once
            assert mock_add_stats.call_count == 1

            # Verify metadata
            _, metadata, statistics = mock_add_stats.call_args[0]
            assert metadata["source"] == DOMAIN
            assert metadata["statistic_id"].startswith(f"{DOMAIN}:")
            assert metadata["has_sum"] is True
            assert len(statistics) > 0

        await mocked_api.aiohttp_session.close()


async def test_push_external_statistics_empty_data(hass):
    """Test that empty device_data.data doesn't crash (regression for 70dd1ea)."""
    sensor = DataSensor("system_0", 0, 0, MagicMock())
    sensor.hass = hass
    sensor.coordinator.data = {
        "system_0": {
            "home_name": "Test",
            "devices_data": [[MagicMock(data=[], device=None)]]
        }
    }
    # Should not raise — empty bucket list returns early
    sensor._push_external_statistics()


async def test_push_external_statistics_no_recorder(hass):
    """Test that recorder-not-enabled guard prevents crash."""
    hass.data = {}  # No DATA_INSTANCE key
    sensor = DataSensor("system_0", 0, 0, MagicMock())
    sensor.hass = hass
    sensor.coordinator.data = {
        "system_0": {
            "home_name": "Test",
            "devices_data": [[MagicMock(data=[
                DeviceDataBucket(
                    start_date=datetime(2026, 6, 6, 0, 0, tzinfo=timezone.utc),
                    end_date=datetime(2026, 6, 6, 1, 0, tzinfo=timezone.utc),
                    value=1000.0,
                )
            ])]]
        }
    }
    # Should not raise — recorder guard returns early
    sensor._push_external_statistics()


async def test_push_external_statistics_none_device(hass):
    """Test that None device (and thus None unique_id) is handled gracefully."""
    sensor = DataSensor("system_0", 0, 0, MagicMock())
    sensor.hass = hass
    sensor.coordinator.data = {
        "system_0": {
            "home_name": "Test",
            "devices_data": [[MagicMock(data=[], device=None)]]
        }
    }
    # Should not raise — device_data returns DeviceData with device=None,
    # unique_id returns None when device is None
    sensor._push_external_statistics()


async def test_push_external_statistics_running_sum_reset(hass):
    """Test that running sum resets at midnight."""
    tz = timezone(timedelta(hours=2))  # Europe/Berlin-like
    buckets = [
        # Day 1, hour 23
        DeviceDataBucket(
            start_date=datetime(2026, 6, 6, 23, 0, tzinfo=tz),
            end_date=datetime(2026, 6, 7, 0, 0, tzinfo=tz),
            value=500.0,
        ),
        # Day 2, hour 0 (new day — sum should reset)
        DeviceDataBucket(
            start_date=datetime(2026, 6, 7, 0, 0, tzinfo=tz),
            end_date=datetime(2026, 6, 7, 1, 0, tzinfo=tz),
            value=300.0,
        ),
        # Day 2, hour 1
        DeviceDataBucket(
            start_date=datetime(2026, 6, 7, 1, 0, tzinfo=tz),
            end_date=datetime(2026, 6, 7, 2, 0, tzinfo=tz),
            value=200.0,
        ),
    ]

    device_data = MagicMock(spec=DeviceData)
    device_data.operation_mode = "heating"
    device_data.energy_type = "consumed_electrical_energy"
    device_data.data = buckets
    # Create a mock device for unique_id
    mock_device = MagicMock()
    mock_device.device_uuid = "test_uuid_123"
    mock_device.system_id = "system_0"
    device_data.device = mock_device

    hass_mock = MagicMock()
    hass_mock.data = {DATA_INSTANCE: MagicMock()}

    coordinator = MagicMock()
    coordinator.data = {
        "system_0": {
            "home_name": "Test",
            "devices_data": [[device_data]]
        }
    }

    sensor = DataSensor("system_0", 0, 0, coordinator)
    sensor.hass = hass_mock

    with patch(
        "custom_components.mypyllant.sensor.async_add_external_statistics"
    ) as mock_add_stats:
        sensor._push_external_statistics()

        _, metadata, statistics = mock_add_stats.call_args[0]

        # 3 statistics pushed
        assert len(statistics) == 3

        # First bucket (day 1, hour 23): sum = 500
        assert statistics[0]["sum"] == 500.0

        # Second bucket (day 2, hour 0): sum resets to 300
        assert statistics[1]["sum"] == 300.0

        # Third bucket (day 2, hour 1): sum = 300 + 200 = 500
        assert statistics[2]["sum"] == 500.0

        # last_reset changes between bucket 0 and bucket 1
        assert statistics[0]["last_reset"] != statistics[1]["last_reset"]

        # last_reset is same for bucket 1 and 2 (same day)
        assert statistics[1]["last_reset"] == statistics[2]["last_reset"]
