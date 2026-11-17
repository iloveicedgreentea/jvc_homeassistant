"""Device constants for a JVC Projector."""

from typing import Final

POWER: Final = "power"
OFF: Final = "off"
STANDBY: Final = "standby"
ON: Final = "on"
WARMING: Final = "warming"
COOLING: Final = "cooling"
ERROR: Final = "error"
NORMAL: Final = "normal"
LOW: Final = "low"
MEDIUM: Final = "medium"
HIGH: Final = "high"
AUTO: Final = "auto"

SIGNAL: Final = "signal"
NOSIGNAL: Final = "no_signal"

INPUT: Final = "input"
HDMI1 = "hdmi1"
HDMI2 = "hdmi2"

REMOTE_MENU: Final = "732E"
REMOTE_UP: Final = "7301"
REMOTE_DOWN: Final = "7302"
REMOTE_LEFT: Final = "7336"
REMOTE_RIGHT: Final = "7334"
REMOTE_OK: Final = "732F"
REMOTE_BACK: Final = "7303"
REMOTE_MPC: Final = "73F0"
REMOTE_HIDE: Final = "731D"
REMOTE_INFO: Final = "7374"
REMOTE_INPUT: Final = "7308"
REMOTE_ADVANCED_MENU: Final = "7373"
REMOTE_PICTURE_MODE: Final = "73F4"
REMOTE_COLOR_PROFILE: Final = "7388"
REMOTE_LENS_CONTROL: Final = "7330"
REMOTE_SETTING_MEMORY: Final = "73D4"
REMOTE_GAMMA_SETTINGS: Final = "73F5"
REMOTE_CMD: Final = "738A"
REMOTE_MODE_1: Final = "73D8"
REMOTE_MODE_2: Final = "73D9"
REMOTE_MODE_3: Final = "73DA"
REMOTE_HDMI_1: Final = "7370"
REMOTE_HDMI_2: Final = "7371"
REMOTE_LENS_AP: Final = "7320"
REMOTE_ANAMO: Final = "73C5"
REMOTE_GAMMA: Final = "7375"
REMOTE_COLOR_TEMP: Final = "7376"
REMOTE_3D_FORMAT: Final = "73D6"
REMOTE_PIC_ADJ: Final = "7372"
REMOTE_NATURAL: Final = "736A"
REMOTE_CINEMA: Final = "7368"
REMOTE_HIDE_ON: Final = "73D0"
REMOTE_HIDE_OFF: Final = "73D1"
REMOTE_MODE_4: Final = "73E5"
REMOTE_MODE_5: Final = "73E6"
REMOTE_MODE_6: Final = "73E7"
REMOTE_MODE_7: Final = "73E8"
REMOTE_MODE_8: Final = "73E9"
REMOTE_MODE_9: Final = "73EA"
REMOTE_MODE_10: Final = "73EB"
REMOTE_HDR10: Final = "73ED"
REMOTE_HDR10_PLUS: Final = "73F9"
REMOTE_HLG: Final = "73E1"
REMOTE_FILMMAKER: Final = "73FB"

# HDR Processing modes
HDR_10PLUS: Final = "hdr10_plus"
HDR_STATIC: Final = "static"
HDR_FRAME_BY_FRAME: Final = "frame_by_frame"
HDR_SCENE_BY_SCENE: Final = "scene_by_scene"

# HDR Content types
HDR_CONTENT_SDR: Final = "sdr"
HDR_CONTENT_HDR10: Final = "hdr10"
HDR_CONTENT_HDR10PLUS: Final = "hdr10_plus"
HDR_CONTENT_HLG: Final = "hlg"
HDR_CONTENT_NONE: Final = "none"

# Anamorphic modes
ANAMORPHIC_A: Final = "a"
ANAMORPHIC_B: Final = "b"
ANAMORPHIC_C: Final = "c"
ANAMORPHIC_D: Final = "d"

# Laser dimming modes
AUTO1: Final = "auto1"
AUTO2: Final = "auto2"
AUTO3: Final = "auto3"

# Aspect Ratio
ASPECT_RATIO_ZOOM: Final = "zoom"
ASPECT_RATIO_NATIVE: Final = "native"

MODEL_MAP = {
    "B8A1": "NZ900",
    "B8A2": "NZ800",
    "B5A1": "NZ9",
    "B5A2": "NZ8",
    "B5A3": "NZ7",
    "A2B1": "NX9",
    "A2B2": "NX7",
    "A2B3": "NX5",
    "B2A1": "NX9",
    "B2A2": "NX7",
    "B2A3": "NX5",
    "B5B1": "NP5",
    "XHR1": "X570R",
    "XHR3": "X770R||X970R",
    "XHP1": "X5000",
    "XHP2": "XC6890",
    "XHP3": "X7000||X9000",
    "XHK1": "X500R",
    "XHK2": "RS4910",
    "XHK3": "X700R||X900R",
}

# Key names
KEY_MODEL: Final = "model"
KEY_MAC: Final = "mac"
KEY_VERSION: Final = "version"
KEY_POWER: Final = "power"
KEY_INPUT: Final = "input"
KEY_SOURCE: Final = "source"
KEY_PICTURE_MODE: Final = "picture_mode"
KEY_LOW_LATENCY: Final = "low_latency"
KEY_INSTALLATION_MODE: Final = "installation_mode"
KEY_ANAMORPHIC: Final = "anamorphic"
KEY_HDR: Final = "hdr"
KEY_HDMI_INPUT_LEVEL: Final = "hdmi_input_level"
KEY_HDMI_COLOR_SPACE: Final = "hdmi_color_space"
KEY_COLOR_PROFILE: Final = "color_profile"
KEY_GRAPHICS_MODE: Final = "graphics_mode"
KEY_COLOR_SPACE: Final = "color_space"
KEY_ESHIFT: Final = "eshift"
KEY_LASER_DIMMING: Final = "laser_dimming"
KEY_LASER_VALUE: Final = "laser_value"
KEY_LASER_POWER: Final = "laser_power"
KEY_LASER_TIME: Final = "laser_time"
KEY_MOTION_ENHANCE: Final = "motion_enhance"
KEY_CLEAR_MOTION_DRIVE: Final = "clear_motion_drive"
KEY_HDR_PROCESSING: Final = "hdr_processing"
KEY_HDR_CONTENT_TYPE: Final = "hdr_content_type"
KEY_RESOLUTION: Final = "resolution"
KEY_ALLM: Final = "allm"
KEY_DEEP_BLACK: Final = "deep_black"
KEY_FILMMAKER_AUTO: Final = "filmmaker_auto"
KEY_DEEP_COLOR: Final = "deep_color"
KEY_COLORIMETRY: Final = "colorimetry"
KEY_HIGHLIGHT_COLOR: Final = "highlight_color"
KEY_SMOOTHER: Final = "smoother"


# Command constants
CMD_POWER = "PW"
CMD_INPUT = "IP"
CMD_SOURCE = "SC"
CMD_MODEL = "MD"
CMD_REMOTE = "RC"
CMD_VERSION = "IFSV"
CMD_PICTURE_MODE = "PMPM"
CMD_PICTURE_MODE_INTELLIGENT_APERTURE = "PMDI"
CMD_LASER_DIMMING = "PMDC"
CMD_PICTURE_MODE_COLOR_PROFILE = "PMPR"
CMD_PICTURE_MODE_COLOR_TEMP = "PMCL"
CMD_PICTURE_MODE_COLOR_CORRECTION = "PMCC"
CMD_PICTURE_MODE_GAMMA_TABLE = "PMGT"
CMD_PICTURE_MODE_COLOR_MANAGEMENT = "PMCB"
CMD_PICTURE_MODE_LOW_LATENCY = "PMLL"
CMD_PICTURE_MODE_8K_ESHIFT = "PMUS"
CMD_PICTURE_MODE_CLEAR_MOTION_DRIVE = "PMCM"
CMD_PICTURE_MODE_LASER_VALUE = "PMCV"
CMD_PICTURE_MODE_MOTION_ENHANCE = "PMME"
CMD_PICTURE_MODE_LASER_POWER = "PMLP"
CMD_PICTURE_MODE_GRAPHICS_MODE = "PMGM"
CMD_INPUT_SIGNAL_HDMI_INPUT_LEVEL = "ISIL"
CMD_INPUT_SIGNAL_HDMI_COLOR_SPACE = "ISHS"
CMD_INPUT_SIGNAL_HDMI_2D_3D = "IS3D"
CMD_INPUT_SIGNAL_ASPECT = "ISAS"
CMD_INPUT_SIGNAL_MASK = "ISMA"
CMD_INSTALLATION_MODE = "INML"
# Deprecated compatibility constant; absent from the verified specifications.
# It is deliberately excluded from command decoding and named operations.
CMD_INSTALLATION_LENS_CONTROL = "INLC"
# Directional continuous motor operations, verified for these model families.
# Values are ASCII 1 (start) and 0 (stop), unlike single-step lens commands.
LENS_COMMANDS: Final = {
    "focus_near": "INFN",
    "focus_far": "INFF",
    "zoom_tele": "INZT",
    "zoom_wide": "INZW",
    "shift_left": "INSL",
    "shift_right": "INSR",
    "shift_up": "INSU",
    "shift_down": "INSD",
}
# Single-shot operations take no data parameter (not the continuous start flag).
LENS_STEP_COMMANDS: Final = {
    "focus_near": "IN1N",
    "focus_far": "IN1F",
    "zoom_tele": "IN1T",
    "zoom_wide": "IN1W",
    "shift_left": "IN1L",
    "shift_right": "IN1R",
    "shift_up": "IN1U",
    "shift_down": "IN1D",
}
LENS_MODELS: Final = {"NZ7", "NZ8", "NZ9", "NP5", "NZ800", "NZ900"}
CMD_INSTALLATION_LENS_IMAGE_PATTERN = "INIP"
CMD_INSTALLATION_LENS_LOCK = "INLL"
CMD_INSTALLATION_SCREEN_ADJUST = "INSC"
CMD_INSTALLATION_STYLE = "INIS"
CMD_INSTALLATION_ANAMORPHIC = "INVS"
CMD_DISPLAY_BACK_COLOR = "DSBC"
CMD_DISPLAY_MENU_POSITION = "DSMP"
CMD_DISPLAY_SOURCE_DISPLAY = "DSSD"
CMD_DISPLAY_LOGO = "DSLO"
CMD_FUNCTION_TRIGGER = "FUTR"
CMD_FUNCTION_OFF_TIMER = "FUOT"
CMD_FUNCTION_ECO_MODE = "FUEM"
CMD_FUNCTION_CONTROL4 = "FUCF"
CMD_FUNCTION_INPUT = "IFIN"
CMD_FUNCTION_SOURCE = "IFIS"
CMD_FUNCTION_DEEP_COLOR = "IFDC"
CMD_FUNCTION_COLOR_SPACE = "IFXV"
CMD_FUNCTION_COLORIMETRY = "IFCM"
CMD_FUNCTION_HDR = "IFHR"
CMD_FUNCTION_LASER_TIME = "IFLT"
CMD_PICTURE_MODE_HDR_LEVEL = "PMHL"
CMD_PICTURE_MODE_HDR_PROCESSING = "PMHP"
CMD_PICTURE_MODE_HDR_CONTENT_TYPE = "PMCT"
CMD_PICTURE_MODE_THEATER_OPTIMIZER = "PMNM"
CMD_PICTURE_MODE_THEATER_OPTIMIZER_LEVEL = "PMNL"
CMD_PICTURE_MODE_THEATER_OPTIMIZER_PROCESSING = "PMNP"
CMD_PICTURE_MODE_DEEP_BLACK = "PMBK"
CMD_PICTURE_MODE_HIGHLIGHT_COLOR = "PMBE"
CMD_PICTURE_MODE_SMOOTHER = "PMST"
CMD_INPUT_SIGNAL_ALLM = "ISAL"
CMD_INPUT_SIGNAL_FILMMAKER_AUTO = "ISFS"
CMD_LAN_SETUP_DHCP = "LSDS"
CMD_LAN_SETUP_MAC_ADDRESS = "LSMA"
CMD_LAN_SETUP_IP_ADDRESS = "LSIP"

# Map keys to commands to make sending commands simple
KEY_MAP_TO_COMMAND: Final = {
    KEY_POWER: CMD_POWER,
    KEY_INPUT: CMD_INPUT,
    KEY_SOURCE: CMD_SOURCE,
    KEY_PICTURE_MODE: CMD_PICTURE_MODE,
    KEY_INSTALLATION_MODE: CMD_INSTALLATION_MODE,
    KEY_ANAMORPHIC: CMD_INSTALLATION_ANAMORPHIC,
    KEY_HDR: CMD_FUNCTION_HDR,
    KEY_HDMI_INPUT_LEVEL: CMD_INPUT_SIGNAL_HDMI_INPUT_LEVEL,
    KEY_HDMI_COLOR_SPACE: CMD_INPUT_SIGNAL_HDMI_COLOR_SPACE,
    KEY_COLOR_PROFILE: CMD_PICTURE_MODE_COLOR_PROFILE,
    KEY_GRAPHICS_MODE: CMD_PICTURE_MODE_GRAPHICS_MODE,
    KEY_COLOR_SPACE: CMD_FUNCTION_COLOR_SPACE,
    KEY_ESHIFT: CMD_PICTURE_MODE_8K_ESHIFT,
    KEY_LASER_DIMMING: CMD_LASER_DIMMING,
    KEY_LASER_VALUE: CMD_PICTURE_MODE_LASER_VALUE,
    KEY_LASER_POWER: CMD_PICTURE_MODE_LASER_POWER,
    KEY_LASER_TIME: CMD_FUNCTION_LASER_TIME,
    KEY_MOTION_ENHANCE: CMD_PICTURE_MODE_MOTION_ENHANCE,
    KEY_CLEAR_MOTION_DRIVE: CMD_PICTURE_MODE_CLEAR_MOTION_DRIVE,
    KEY_HDR_PROCESSING: CMD_PICTURE_MODE_HDR_PROCESSING,
    KEY_HDR_CONTENT_TYPE: CMD_PICTURE_MODE_HDR_CONTENT_TYPE,
    KEY_ALLM: CMD_INPUT_SIGNAL_ALLM,
    KEY_DEEP_BLACK: CMD_PICTURE_MODE_DEEP_BLACK,
    KEY_FILMMAKER_AUTO: CMD_INPUT_SIGNAL_FILMMAKER_AUTO,
    KEY_DEEP_COLOR: CMD_FUNCTION_DEEP_COLOR,
    KEY_COLORIMETRY: CMD_FUNCTION_COLORIMETRY,
    KEY_HIGHLIGHT_COLOR: CMD_PICTURE_MODE_HIGHLIGHT_COLOR,
    KEY_SMOOTHER: CMD_PICTURE_MODE_SMOOTHER,
}

# Value constants
VAL_POWER = [STANDBY, ON, COOLING, WARMING, ERROR]
VAL_INPUT = {
    "0": "svideo",
    "1": "video",
    "2": "component",
    "3": "pc",
    "6": HDMI1,
    "7": HDMI2,
}
VAL_SOURCE = [NOSIGNAL, SIGNAL]
VAL_PICTURE_MODE = {
    "00": "film",
    "01": "cinema",
    "02": "animation",
    "03": "natural",
    "04": "hdr10",
    "06": "thx",
    "0B": "frameadapt_hdr",
    "0C": "user1",
    "0D": "user2",
    "0E": "user3",
    "0F": "user4",
    "10": "user5",
    "11": "user6",
    "14": "hlg",
    "15": "hdr10+",
    "16": "pana_pq",
    "17": "filmmaker",
    "18": "frameadapt_hdr2",
    "19": "frameadapt_hdr3",
    "1B": "vivid",
    "1C": "natural_ll",
    "1D": "hdr10_ll",
    "1E": "hlg_ll",
}
VAL_INTELLIGENT_APERTURE = [OFF, AUTO1, AUTO2]
VAL_LASER_DIMMING = [OFF, AUTO1, AUTO2, AUTO3]
VAL_COLOR_PROFILE = {
    "00": OFF,
    "01": "film1",
    "02": "film2",
    "03": "bt709",
    "04": "cinema",
    "05": "cinema2",
    "06": "anime",
    "07": "anime2",
    "08": "video",
    "09": "vivid",
    "0A": "hdr",
    "0B": "bt2020(wide)",
    "0C": "3d",
    "0D": "thx",
    "0E": "custom1",
    "0F": "custom2",
    "10": "custom3",
    "11": "custom4",
    "12": "custom5",
    "21": "dci",
    "22": "custom6",
    "24": "bt2020(normal)",
    "25": "off(wide)",
    "26": AUTO,
}
VAL_COLOR_TEMP = {
    "00": "5500k",
    "02": "6500k",
    "04": "7500k",
    "08": "9300k",
    "09": "high",
    "0A": "custom1",
    "0B": "custom2",
    "0C": "hdr10",
    "0D": "xenon1",
    "0E": "xenon2",
    "14": "hlg",
}
VAL_COLOR_CORRECTION = {
    "00": "5500k",
    "02": "6500k",
    "04": "7500k",
    "08": "9300k",
    "09": "high",
    "0D": "xenon1",
    "0E": "xenon2",
}
VAL_GAMMA_TABLE = {
    "00": "2.2",
    "01": "cinema1",
    "02": "cinema2",
    "04": "custom1",
    "05": "custom2",
    "06": "custom3",
    "07": "hdr_hlg",
    "08": "2.4",
    "09": "2.6",
    "0A": "film1",
    "0B": "film2",
    "0C": "hdr_pq",
    "0D": "pana_pq",
    "10": "thx",
    "15": "hdr_auto",
}
VAL_TOGGLE = [OFF, ON]
VAL_CLEAR_MOTION_DRIVE = [OFF, "none", LOW, HIGH, "inverse_telecine"]
VAL_MOTION_ENHANCE = [OFF, LOW, HIGH]
# note this order can't change due to how building comamands works. JVC historically did not have medium it was added with the NZ series. It is 2 for medium, 1 for high.
VAL_LASER_POWER = [
    LOW,
    HIGH,
    MEDIUM,
]
VAL_GRAPHICS_MODE = ["standard", "high-res", "high-res2", OFF]
VAL_HDMI_INPUT_LEVEL = ["standard", "enhanced", "super_white", AUTO]
VAL_HDMI_COLOR_SPACE = [AUTO, "ycbcr(4:4:4)", "ycbcr(4:2:2)", "rgb"]
VAL_HDMI_2D_3D = ["2d", AUTO, "none", "side_by_side", "top_bottom"]
VAL_ASPECT = ["none", "zoom", AUTO, "native"]
VAL_MASK = ["none", ON, OFF]
VAL_INSTALLATION_MODE = [f"mode{i}" for i in range(1, 11)]
VAL_LENS_CONTROL = ["stop", "start"]
VAL_INSTALLATION_STYLE = ["front", "front_ceiling", "rear", "rear_ceiling"]
VAL_ANAMORPHIC = [OFF, ANAMORPHIC_A, ANAMORPHIC_B, ANAMORPHIC_C, ANAMORPHIC_D]
VAL_BACK_COLOR = ["blue", "black"]
VAL_MENU_POSITION = [
    "left-top",
    "right-top",
    "center",
    "left-bottom",
    "right-bottom",
    "left",
    "right",
]
VAL_TRIGGER = [OFF, "power", "anamo"] + [f"ins{i}" for i in range(1, 11)]
VAL_OFF_TIMER = [OFF, "1hour", "2hour", "3hour", "4hour"]
VAL_FUNCTION_INPUT = [HDMI1, HDMI2]
VAL_FUNCTION_SOURCE = {
    "02": "480p",
    "03": "576p",
    "04": "720p50",
    "05": "720p60",
    "06": "1080i50",
    "07": "1080i60",
    "08": "1080p24",
    "09": "1080p50",
    "0A": "1080p60",
    "0B": "nosignal",
    "0C": "720p3d",
    "0D": "1080i3d",
    "0E": "1080p3d",
    "0F": "outofrange",
    "10": "4k(4096)60",
    "11": "4k(4096)50",
    "12": "4k(4096)30",
    "13": "4k(4096)25",
    "14": "4k(4096)24",
    "15": "4k(3840)60",
    "16": "4k(3840)50",
    "17": "4k(3840)30",
    "18": "4k(3840)25",
    "19": "4k(3840)24",
    "1C": "1080p25",
    "1D": "1080p30",
    "1E": "2048x1080p24",
    "1F": "2048x1080p25",
    "20": "2048x1080p30",
    "21": "2048x1080p50",
    "22": "2048x1080p60",
    "23": "3840x2160p120",
    "24": "4096x2160p120",
    "25": "vga(640x480)",
    "26": "svga(800x600)",
    "27": "xga(1024x768)",
    "28": "sxga(1280x1024)",
    "29": "wxga(1280x768)",
    "2A": "wxga+(1440x900)",
    "2B": "wsxga+(1680x1050)",
    "2C": "wuxga(1920x1200)",
    "2D": "wxga(1280x800)",
    "2E": "fwxga(1366x768)",
    "2F": "wxga++(1600x900)",
    "30": "uxga(1600x1200)",
    "31": "qxga",
    "32": "wqxga",
    "34": "4096x2160_100hz",
    "35": "3840x2160_100hz",
    "36": "1080p100",
    "37": "1080p120",
    "38": "7680x4320_60hz",
    "39": "7680x4320_50hz",
    "3A": "7680x4320_30hz",
    "3B": "7680x4320_25hz",
    "3C": "7680x4320_24hz",
    "3D": "wqhd60",
    "3E": "wqhd120",
    "3F": "7680x4320_48hz",
}
VAL_DEEP_COLOR = ["8bit", "10bit", "12bit"]
VAL_COLOR_SPACE = ["rgb", "yuv"]
VAL_COLORIMETRY = [
    "nodata",
    "bt601",
    "bt709",
    "xvycc601",
    "xvycc709",
    "sycc601",
    "adobe_ycc601",
    "adobe_rgb",
    "bt2020(constant_luminance)",
    "bt2020(non-constant_luminance)",
    "srgb",
    "dci_p3_d65",
    "dci_p3_theater",
]
VAL_HDR_MODES = [
    HDR_CONTENT_SDR,
    KEY_HDR,
    "smpte_st_2084",
    "hybrid_log",
    "none",
    HDR_CONTENT_HDR10PLUS,
]
VAL_HDR = {
    "0": VAL_HDR_MODES[0],
    "1": VAL_HDR_MODES[1],
    "2": VAL_HDR_MODES[2],
    "3": VAL_HDR_MODES[3],
    "4": HDR_CONTENT_HDR10PLUS,
    "F": VAL_HDR_MODES[4],
}
VAL_HDR_LEVEL = [AUTO, "-2", "-1", "0", "1", "2", "auto_wide"]
VAL_HDR_PROCESSING = [HDR_CONTENT_HDR10PLUS, "static", "frame", "scene"]
VAL_HDR_CONTENT_TYPE = [
    AUTO,
    HDR_CONTENT_SDR,
    HDR_CONTENT_HDR10PLUS,
    HDR_CONTENT_HDR10,
    HDR_CONTENT_HLG,
]
VAL_THEATER_OPTIMIZER_LEVEL = ["reserved", LOW, MEDIUM, HIGH]
VAL_THEATER_OPTIMIZER_PROCESSING = ["-", "start"]
VAL_FILMMAKER_AUTO = ["manual", AUTO]
VAL_HIGHLIGHT_COLOR = [LOW, MEDIUM, HIGH]
VAL_SMOOTHER = {"0000": ON, "0001": OFF}

# Modern HDMI receivers identify the YCbCr subsampling explicitly. Older
# models report only RGB/YUV, so the projector applies this map by model.
VAL_COLOR_SPACE_MODERN = {"0": "rgb", "1": "ycbcr422", "2": "ycbcr444", "3": "ycbcr420"}

MODERN_MODELS = {"NZ800", "NZ900"}
# These newer models changed several wire values and labels. Keep their
# tables separate so legacy projectors retain their original interpretation.
MODERN_COMMAND_VALUES = {
    CMD_PICTURE_MODE: {
        code: VAL_PICTURE_MODE[code]
        for code in (
            "00",
            "01",
            "03",
            "04",
            "0B",
            "0C",
            "0D",
            "0E",
            "0F",
            "10",
            "11",
            "14",
            "15",
            "17",
            "18",
            "19",
            "1B",
            "1C",
            "1D",
            "1E",
        )
    },
    CMD_PICTURE_MODE_COLOR_PROFILE: {
        **{
            code: VAL_COLOR_PROFILE[code]
            for code in (
                "00",
                "01",
                "02",
                "03",
                "04",
                "06",
                "08",
                "0B",
                "0E",
                "0F",
                "10",
                "11",
                "21",
                "24",
                "25",
            )
        },
        "23": "vivid",
        "26": AUTO,
    },
    CMD_LASER_DIMMING: {"0": OFF, "1": LOW, "2": HIGH, "3": "balanced"},
    CMD_PICTURE_MODE_CLEAR_MOTION_DRIVE: {
        "0": OFF,
        "3": LOW,
        "4": HIGH,
        "5": "inverse_telecine",
    },
    CMD_PICTURE_MODE_GRAPHICS_MODE: {
        "0": "standard",
        "1": "high-res",
        "2": "high-res2",
        "F": OFF,
    },
    CMD_PICTURE_MODE_THEATER_OPTIMIZER_LEVEL: {
        "0": AUTO,
        "1": "-2",
        "2": "-1",
        "3": "0",
        "4": "1",
        "5": "2",
        "6": "auto_wide",
    },
    CMD_INPUT_SIGNAL_ASPECT: {"2": "zoom", "3": AUTO, "4": "native"},
    CMD_INPUT_SIGNAL_MASK: {"1": ON, "2": OFF},
    CMD_INPUT_SIGNAL_HDMI_2D_3D: {
        "0": "2d",
        "1": AUTO,
        "3": "side_by_side",
        "4": "top_bottom",
    },
    CMD_FUNCTION_COLOR_SPACE: VAL_COLOR_SPACE_MODERN,
}
