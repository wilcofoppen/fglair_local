"""Constants for FGLair Local. Types and read-only flags come from the FGLair cloud."""

DOMAIN = "fglair_local"

CONF_LANIP_KEY = "lanip_key"
CONF_CALLBACK_IP = "callback_ip"
CONF_CALLBACK_PORT = "callback_port"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_REGION = "region"
CONF_DEVICE = "device"

DEFAULT_PORT = 8888
DEFAULT_SCAN_INTERVAL = 60

MIN_TEMP_HEAT = 16.0
MIN_TEMP_OTHER = 18.0
MAX_TEMP = 30.0


def sensed_to_celsius(value: int) -> float:
    """Convert display_temperature and outdoor_temperature to degrees Celsius."""
    return (value - 5000) / 100


# operation_mode values
MODE_OFF = 0
MODE_ON = 1
MODE_AUTO = 2
MODE_COOL = 3
MODE_DRY = 4
MODE_FAN = 5
MODE_HEAT = 6

# device_capabilities bits
CAP_COOL = 0
CAP_DRY = 1
CAP_FAN = 2
CAP_HEAT = 3
CAP_AUTO = 4
CAP_FAN_AUTO = 5
CAP_FAN_HIGH = 6
CAP_FAN_MEDIUM = 7
CAP_FAN_LOW = 8
CAP_FAN_QUIET = 9
CAP_SWING_VERTICAL = 10
CAP_SWING_HORIZONTAL = 11
CAP_ECO = 12
CAP_MIN_HEAT = 13
CAP_POWERFUL = 16
CAP_OUTDOOR_LOW_NOISE = 17
CAP_COIL_DRY = 18

PROPERTY_TYPES = {
    "adjust_temperature": "integer",
    "af_horizontal_direction": "integer",
    "af_horizontal_num_dir": "integer",
    "af_horizontal_swing": "boolean",
    "af_vertical_direction": "integer",
    "af_vertical_num_dir": "integer",
    "af_vertical_swing": "boolean",
    "auto_off_time": "integer",
    "auto_on_off_set_time": "integer",
    "auto_on_off_time": "integer",
    "auto_save_set_time": "integer",
    "auto_save_time": "integer",
    "building_name": "string",
    "child_lock_mode": "boolean",
    "child_lock_pin": "string",
    "coil_dry_mode": "boolean",
    "comm_version": "integer",
    "demand_control": "integer",
    "device_capabilities": "integer",
    "device_name": "string",
    "display_temperature": "integer",
    "economy_mode": "boolean",
    "error_code": "integer",
    "fan_speed": "integer",
    "filter_sign_reset_display": "boolean",
    "get_prop": "boolean",
    "human_det": "integer",
    "human_det_auto_off": "boolean",
    "human_det_auto_on_off": "boolean",
    "human_det_auto_save": "boolean",
    "indoor_fan_control": "boolean",
    "master_timer_on_off_1": "boolean",
    "master_timer_on_off_2": "boolean",
    "mcu_error": "integer",
    "mcu_fw_version": "string",
    "min_heat": "boolean",
    "model_name": "string",
    "op_status": "integer",
    "operation_mode": "integer",
    "outdoor_low_noise": "boolean",
    "outdoor_temperature": "integer",
    "powerful_mode": "boolean",
    "rc_prohibition": "integer",
    "reboot_range": "integer",
    "reboot_start": "integer",
    "refresh": "boolean",
    "service_contact_email": "string",
    "service_contact_name": "string",
    "service_contact_phone": "string",
    "service_function_address": "integer",
    "service_function_number": "integer",
    "service_function_setting": "integer",
    "service_mode": "boolean",
    "system_type": "integer",
    "test_run": "boolean",
    "wifi_led_enable": "boolean",
    "zone_1_num_outlets": "integer",
    "zone_2_num_outlets": "integer",
    "zone_3_num_outlets": "integer",
    "zone_4_num_outlets": "integer",
    "zone_5_num_outlets": "integer",
    "zone_6_num_outlets": "integer",
    "zone_7_num_outlets": "integer",
    "zone_8_num_outlets": "integer",
    "zone_function_setting": "integer",
    "zone_setting": "integer",
    "zone_temp_sensor_mode": "boolean",
    "zone_temp_sensor_select": "integer",
    "zone_use_opt_sensor_1": "boolean",
    "zone_use_opt_sensor_2": "boolean",
}

READ_ONLY = {
    "af_horizontal_num_dir",
    "af_vertical_num_dir",
    "auto_on_off_set_time",
    "auto_save_set_time",
    "child_lock_mode",
    "comm_version",
    "demand_control",
    "device_capabilities",
    "display_temperature",
    "error_code",
    "human_det",
    "mcu_fw_version",
    "op_status",
    "outdoor_temperature",
    "system_type",
    "wifi_led_enable",
}

# Never read, so they cannot end up in states, logs or diagnostics.
SENSITIVE = {
    "child_lock_pin",
    "service_contact_email",
    "service_contact_name",
    "service_contact_phone",
}

ALL_PROPERTIES = [name for name in PROPERTY_TYPES if name not in SENSITIVE]

# Polled every interval; everything else once an hour.
FAST_PROPERTIES = [
    "adjust_temperature",
    "af_horizontal_direction",
    "af_horizontal_swing",
    "af_vertical_direction",
    "af_vertical_swing",
    "display_temperature",
    "economy_mode",
    "error_code",
    "fan_speed",
    "min_heat",
    "op_status",
    "operation_mode",
    "outdoor_temperature",
    "powerful_mode",
]
