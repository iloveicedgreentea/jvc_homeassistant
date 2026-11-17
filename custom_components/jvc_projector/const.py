"""Constants for the jvc_projector integration."""

from ._vendor.jvcprojector import const

NAME = "JVC Projector"
DOMAIN = "jvc_projector"
MANUFACTURER = "JVC"

REMOTE_COMMANDS = {
    "menu": const.REMOTE_MENU,
    "up": const.REMOTE_UP,
    "down": const.REMOTE_DOWN,
    "left": const.REMOTE_LEFT,
    "right": const.REMOTE_RIGHT,
    "ok": const.REMOTE_OK,
    "back": const.REMOTE_BACK,
    "mpc": const.REMOTE_MPC,
    "hide": const.REMOTE_HIDE,
    "hide_on": const.REMOTE_HIDE_ON,
    "hide_off": const.REMOTE_HIDE_OFF,
    "info": const.REMOTE_INFO,
    "input": const.REMOTE_INPUT,
    "cmd": const.REMOTE_CMD,
    "advanced_menu": const.REMOTE_ADVANCED_MENU,
    "picture_mode": const.REMOTE_PICTURE_MODE,
    "color_profile": const.REMOTE_COLOR_PROFILE,
    "lens_control": const.REMOTE_LENS_CONTROL,
    "setting_memory": const.REMOTE_SETTING_MEMORY,
    "gamma_settings": const.REMOTE_GAMMA_SETTINGS,
    "hdmi_1": const.REMOTE_HDMI_1,
    "hdmi_2": const.REMOTE_HDMI_2,
    "mode_1": const.REMOTE_MODE_1,
    "mode_2": const.REMOTE_MODE_2,
    "mode_3": const.REMOTE_MODE_3,
    "mode_4": const.REMOTE_MODE_4,
    "mode_5": const.REMOTE_MODE_5,
    "mode_6": const.REMOTE_MODE_6,
    "mode_7": const.REMOTE_MODE_7,
    "mode_8": const.REMOTE_MODE_8,
    "mode_9": const.REMOTE_MODE_9,
    "mode_10": const.REMOTE_MODE_10,
    "hdr10": const.REMOTE_HDR10,
    "hdr10_plus": const.REMOTE_HDR10_PLUS,
    "hlg": const.REMOTE_HLG,
    "filmmaker": const.REMOTE_FILMMAKER,
    "lens_ap": const.REMOTE_LENS_AP,
    "gamma": const.REMOTE_GAMMA,
    "color_temp": const.REMOTE_COLOR_TEMP,
    "natural": const.REMOTE_NATURAL,
    "cinema": const.REMOTE_CINEMA,
    "anamo": const.REMOTE_ANAMO,
    "3d_format": const.REMOTE_3D_FORMAT,
}
