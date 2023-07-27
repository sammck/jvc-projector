#!/usr/bin/env python3

"""
PVC Projector known command codes and metadata.

This module contains the known command codes and metadata for the JVC projector protocol. The information in
this module is derived from JVC's documentation here:

https://support.jvc.com/consumer/support/documents/DILAremoteControlGuide.pdf

There is no protocol implementation here; only metadata about the protocol.
"""
from __future__ import annotations

from ..internal_types import *

CommandCode = bytes


power_status_map: Dict[bytes, str] = {
    b"\x30": "Standby",
    b"\x31": "On",
    b"\x32": "Cooling",
    b"\x33": "Warming",   # Not documented; determined empirically
    b"\x34": "Emergency",
  }
"""Response payloads for power_status.query command, and the projector power states they correspond to."""

input_status_map: Dict[bytes, str] = {
    b"\x30": "S-Video",
    b"\x31": "Video",
    b"\x32": "Component",
    b"\x33": "PC",
    b"\x36": "HDMI 1",
    b"\x37": "HDMI 2",
  }
"""Response payloads for input_status.query command, and the projector input states they correspond to."""

gamma_table_status_map: Dict[bytes, str] = {
    b"\x30": "Normal",
    b"\x31": "A",
    b"\x32": "B",
    b"\x33": "C",
    b"\x34": "Custom 1",
    b"\x35": "Custom 2",
    b"\x36": "Custom 3",
  }
"""Response payloads for gamma_table_status.query command, and the projector gamma table states they correspond to."""

gamma_value_status_map: Dict[bytes, str] = {
    b"\x30": "1.8",
    b"\x31": "1.9",
    b"\x32": "2.0",
    b"\x33": "2.1",
    b"\x34": "2.2",
    b"\x35": "2.3",
    b"\x36": "2.4",
    b"\x37": "2.5",
    b"\x38": "2.6",
  }
"""Response payloads for gamma_value_status.query command, and the projector gamma value states they correspond to."""

source_status_map: Dict[bytes, str] = {
    b"\x00": "JVC Logo",
    b"\x30": "No Signal",
    b"\x31": "Signal OK",
  }
"""Response payloads for source_status.query command, and the projector source states they correspond to."""

model_status_list_map: Dict[bytes, List[str]] = {
    b"ILAFPJ -- B5A1": [ "DLA-NZ9", "DLA-RS4100" ],   # Undocumented; discovered empirically
    b"ILAFPJ -- B5A2": [ "DLA-NZ8", "DLA-RS3100" ],   # Undocumented; discovered empirically
    b"ILAFPJ -- B5A3": [ "DLA-NZ7", "DLA-RS2100" ],   # Undocumented; discovered empirically
    b"ILAFPJ -- -XH4": [ "DLA-HD350" ],
    b"ILAFPJ -- -XH7": [ "DLA-RS10" ],
    b"ILAFPJ -- -XH5": [ "DLA-HD750", "DLA-RS20" ],
    b"ILAFPJ -- -XH8": [ "DLA-HD550" ],
    b"ILAFPJ -- -XHA": [ "DLA-RS15" ],
    b"ILAFPJ -- -XH9": [ "DLA-HD950", "DLA-HD990", "DLA-RS25", "DLA-RS35" ],
    b"ILAFPJ -- -XHB": [ "DLA-X3", "DLA-RS40" ],
    b"ILAFPJ -- -XHC": [ "DLA-X7", "DLA-X9", "DLA-RS50", "DLA-RS60" ],
    b"ILAFPJ -- -XHE": [ "DLA-X30", "DLA-RS45" ],
    b"ILAFPJ -- -XHF": [ "DLA-X70R", "DLA-X90R", "DLA-RS55", "DLA-RS65" ],
  }
"""Response payloads for model_status.query command, and the list of projector models they correspond to.
   The model codes are 14 bytes long; the first 10 bytes are always b'ILAFPJ -- '.
"""

model_status_map: Dict[bytes, str] = dict((k, ",".join(v)) for k, v in model_status_list_map.items())
"""Response payloads for model_status.query command, and the comma-delimited projector models they correspond to.
   The model codes are 14 bytes long; the first 10 bytes are always b'ILAFPJ -- '.
"""

class CommandGroupMeta:
    """Metadata for a group of commands with a common command code prefix as described in the documentation"""
    name: str
    """Name of the command group"""

    command_code: CommandCode
    """two-byte command code common to all commands in the group. May be the same as other groups."""

    group_prefix: bytes
    """byte string immediately following command_code common to all commands in the group."""

    is_advanced: bool
    """True iff all commands in the group are advanced commands that receive an advanced response."""

    command_prefix_length: int
    """Length of command prefix which is unique to each command and follows the group_prefix,
       but is the same length for all commands in the group."""

    payload_length: Optional[int]
    """Fixed length of the payload of the command, which follows the command_prefix, if known. Zero if there is no
       payload. None if the payload is variable in size."""

    response_payload_length: Optional[int]
    """Fixed length of the payload of the advanced response, if known.  0 for basic commands. None if the payload
       is variable in size."""

    commands: Dict[str, CommandMeta]
    """Set of commands in this group, indexed by command name unique within the group."""

    def __init__(
            self,
            name: str,
            command_code_and_group_prefix: bytes,
            commands: List[CommandMeta],
            is_advanced: bool=False,
            payload_length: Optional[int]=0,
            response_payload_length: Optional[int]=0,
          ):
        self.name = name
        self.command_code = command_code_and_group_prefix[:2]
        self.group_prefix = command_code_and_group_prefix[2:]
        self.is_advanced = is_advanced or response_payload_length is None or response_payload_length > 0
        self.payload_length = payload_length
        self.response_payload_length = response_payload_length
        self.commands = {}
        assert len(commands) > 0
        for i, command in enumerate(commands):
            if i == 0:
                self.command_prefix_length = len(command.command_prefix)
            else:
                assert len(command.command_prefix) == self.command_prefix_length
            assert not command in self.commands
            command.command_group = self
            self.commands[command.name] = command
_G = CommandGroupMeta

class CommandMeta:
    """Metadata for a single command in a command group"""
    command_group: CommandGroupMeta
    name: str
    command_prefix: bytes
    description: Optional[str]
    response_map: Optional[Dict[bytes, str]]

    def __init__(self, name: str, command_prefix: bytes, description: Optional[str]=None, response_map: Optional[Dict[bytes, str]]=None):
        self.name = name
        self.command_prefix = command_prefix
        self.description = description
        self.response_map = response_map

_C = CommandMeta

# The following is an exhaustive list of all known commands and their metadata, as described in the JVC documentation.
_group_metas: List[CommandGroupMeta] = [
    _G("power", b'\x50\x57', commands=[
        _C("on", b'\x31', "Power - On"),
        _C("off", b'\x30', "Power - Off"),
      ]),
    _G("set_input", b'\x49\x50', commands=[
        _C("hdmi_1", b'\x36', "Input - HDMI 1"),
        _C("hdmi_2", b'\x37', "Input - HDMI 2"),
        _C("component", b'\x32', "Input - Component"),
        _C("s_video", b'\x30', "Input - S-Video"),
        _C("video", b'\x31', "Input - Video"),
        _C("pc", b'\x33', "Input - PC"),
        _C("next", b'\x2B', "Input + (Go to next highest input)"),
        _C("previous", b'\x2D', "Input - (Go to next lowest input)"),
      ]),
    _G("test_pattern", b'\x54\x53', commands=[
        _C("off", b'\x30', "Test Pattern - Off"),
        _C("colour_bars", b'\x31', "Test Pattern - Colour Bars"),
        _C("stair_step_black_and_white", b'\x36', "Test Pattern - Stair step (black and white)"),
        _C("stair_step_red", b'\x37', "Test Pattern - Stair step (red)"),
        _C("stair_step_green", b'\x38', "Test Pattern - Stair step (green)"),
        _C("stair_step_blue", b'\x39', "Test Pattern - Stair step (blue)"),
        _C("crosshatch_green", b'\x41', "Test Pattern - Crosshatch (green)"),
      ]),
    _G("gamma", b'\x47\x54', commands=[
        _C("normal", b'\x30', "Gamma - Normal"),
        _C("a", b'\x31', "Gamma - A"),
        _C("b", b'\x32', "Gamma - B"),
        _C("c", b'\x33', "Gamma - C"),
        _C("d", b'\x37', "Gamma - D"),
        _C("custom_1", b'\x34', "Gamma - Custom 1"),
        _C("custom_2", b'\x35', "Gamma - Custom 2"),
        _C("custom_3", b'\x36', "Gamma - Custom 3"),
      ]),
    _G("gamma_value", b'\x47\x50', commands=[
        _C("1_8", b'\x30', "Gamma Correction Value - 1.8"),
        _C("1_9", b'\x31', "Gamma Correction Value - 1.9"),
        _C("2_0", b'\x32', "Gamma Correction Value - 2.0"),
        _C("2_1", b'\x33', "Gamma Correction Value - 2.1"),
        _C("2_2", b'\x34', "Gamma Correction Value - 2.2 (Default)"),
        _C("2_3", b'\x35', "Gamma Correction Value - 2.3"),
        _C("2_4", b'\x36', "Gamma Correction Value - 2.4"),
        _C("2_5", b'\x37', "Gamma Correction Value - 2.5"),
        _C("2_6", b'\x38', "Gamma Correction Value - 2.6"),
      ]),
    _G("off_timer", b'\x46\x55\x4F\x54', commands=[
        _C("off", b'\x30', "Off Timer - Off"),
        _C("1_hour", b'\x31', "Off Timer - Set 1 hour"),
        _C("2_hours", b'\x32', "Off Timer - Set 2 hours"),
        _C("3_hours", b'\x33', "Off Timer - Set 3 hours"),
        _C("4_hours", b'\x34', "Off Timer - Set 4 hours"),
      ]),
    _G("lamp_power", b'\x50\x4D\x4C\x50', commands=[
        _C("normal", b'\x30', "Lamp Power - Normal"),
        _C("high", b'\x31', "Lamp Power - High"),
      ]),
    _G("infrared_remote_code", b'\x53\x55\x52\x43', commands=[
        _C("a", b'\x30', "Remote Code - A - hex code 73"),
        _C("b", b'\x31', "Remote Code - B - hex code 63"),
      ]),
    _G("trigger_output_set", b'\x46\x55\x54\x52', commands=[
        _C("off", b'\x30', "Trigger - Off"),
        _C("on_power", b'\x31', "Trigger - On (Power)"),
        _C("on_anamorphic", b'\x32', "Trigger - On (Anamorphic)"),
      ]),
    _G("clear_motion_drive", b'\x50\x4D\x43\x4D', commands=[
        _C("off", b'\x30', "Clear Motion Drive - Off"),
        _C("mode_1", b'\x31', "Clear Motion Drive - Mode 1 (Low - HD550/950/990)"),
        _C("mode_2", b'\x32', "Clear Motion Drive - Mode 2 (High - HD550/950/990)"),
        _C("mode_3", b'\x33', "Clear Motion Drive - Mode 3 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("mode_4", b'\x34', "Clear Motion Drive - Mode 4 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("inverse_telecine", b'\x35', "Clear Motion Drive - Inverse Telecine (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
      ]),
    _G("anamorphic", b'\x49\x4E\x56\x53', commands=[
        _C("off", b'\x30', "Anamorphic - Off"),
        _C("a", b'\x31', "Anamorphic - A"),
        _C("b", b'\x32', "Anamorphic - B"),
      ]),
    # Picture mode commands are overloaded and depend
    # on the projector model:
    #   v1 is for for X30/X70/X90/RS45/55/65
    #   v2 is for X3/X7/X9/RS40/50/60
    #   v3 is for HD350/750/550/950/990/RS10/20/15/25/35
    _G("picture_mode_v1", b'\x50\x4D\x50\x4D', commands=[
        # v1 is for for X30/X70/X90/RS45/55/65
        _C("film", b'\x30\x30', "Picture Mode - Film"),
        _C("cinema", b'\x30\x31', "Picture Mode - Cinema"),
        _C("animation", b'\x30\x32', "Picture Mode - Animation"),
        _C("natural", b'\x30\x33', "Picture Mode - Natural"),
        _C("stage", b'\x30\x34', "Picture Mode - Stage"),
        _C("thx", b'\x30\x36', "Picture Mode - THX (X70/X90/RS55/65)"),
        _C("3d", b'\x30\x42', "Picture Mode - 3D"),
        _C("user_1", b'\x30\x43', "Picture Mode - User 1"),
        _C("user_2", b'\x30\x44', "Picture Mode - User 2"),
        _C("user_3", b'\x30\x45', "Picture Mode - User 3"),
        _C("user_4", b'\x30\x46', "Picture Mode - User 4"),
        _C("user_5", b'\x31\x30', "Picture Mode - User 5"),
      ]),
    _G("picture_mode_v2", b'\x50\x4D\x50\x4D', commands=[
        # v2 is for X3/X7/X9/RS40/50/60
        _C("film", b'\x30', "Picture Mode - Film"),
        _C("cinema", b'\x31', "Picture Mode - Cinema"),
        _C("animation", b'\x32', "Picture Mode - Animation"),
        _C("natural", b'\x33', "Picture Mode - Natural"),
        _C("stage", b'\x34', "Picture Mode - Stage"),
        _C("3d", b'\x45', "Picture Mode - 3D"),
        _C("user_1", b'\x36', "Picture Mode - User 1"),
        _C("user_2", b'\x37', "Picture Mode - User 2"),
        _C("thx", b'\x39', "Picture Mode - THX (X7/X9/RS50/60)"),
      ]),
    _G("picture_mode_v3", b'\x50\x4D\x50\x4D', commands=[
         # v3 is for HD350/750/550/950/990/RS10/20/15/25/35
        _C("cinema_1", b'\x30', "Picture Mode - Cinema 1"),
        _C("cinema_2", b'\x31', "Picture Mode - Cinema 2"),
        _C("cinema_3", b'\x32', "Picture Mode - Cinema 3"),
        _C("natural", b'\x33', "Picture Mode - Natural"),
        _C("stage", b'\x34', "Picture Mode - Stage"),
        _C("user_1", b'\x36', "Picture Mode - User 1"),
        _C("user_2", b'\x37', "Picture Mode - User 2"),
        _C("thx", b'\x39', "Picture Mode - THX (HD750/950/990/RS20/25/35)"),
      ]),
    _G("colour_profile", b'\x50\x4D\x50\x52', commands=[
        _C("off", b'\x30\x30', "Colour Profile - Off"),
        _C("film_1", b'\x30\x31', "Colour Profile - Film 1 (in Film mode)"),
        _C("film_2", b'\x30\x32', "Colour Profile - Film 2 (in Film mode)"),
        _C("standard", b'\x30\x33', "Colour Profile - Standard (in Cinema, Natural, Stage & 3D modes)"),
        _C("cinema_1", b'\x30\x34', "Colour Profile - Cinema 1 (in Cinema mode)"),
        _C("cinema_2", b'\x30\x35', "Colour Profile - Cinema 2 (in Cinema mode)"),
        _C("anime_1", b'\x30\x36', "Colour Profile - Anime 1 (in Animation mode)"),
        _C("anime_2", b'\x30\x37', "Colour Profile - Anime 2 (in Animation mode)"),
        _C("video", b'\x30\x38', "Colour Profile - Video (in Natural mode)"),
        _C("vivid", b'\x30\x39', "Colour Profile - Vivid (in Natural & 3D modes)"),
        _C("adobe", b'\x31\x41', "Colour Profile - Adobe (in Natural mode)"),
        _C("stage", b'\x31\x42', "Colour Profile - Stage (in Stage mode)"),
        _C("3d", b'\x31\x43', "Colour Profile - 3D (in 3D mode)"),
        _C("thx", b'\x31\x44', "Colour Profile - THX (in THX mode)"),
      ]),
    _G("3d_format", b'\x49\x53\x33\x44', commands=[
        _C("off", b'\x30', "3D Format - Off (2D)"),
        _C("auto", b'\x31', "3D Format - Auto"),
        _C("frame_packing", b'\x32', "3D Format - Frame Packing"),
        _C("side_by_side", b'\x33', "3D Format - Side by Side"),
        _C("top_and_bottom", b'\x34', "3D Format - Top and Bottom"),
      ]),
    _G("2d_to_3d_conversion", b'\x49\x53\x33\x43', commands=[
        _C("off", b'\x30', "2D to 3D Conversion - Off"),
        _C("on", b'\x31', "2D to 3D Conversion - On"),
      ]),
    _G("3d_subtitle_correction", b'\x49\x53\x33\x54', commands=[
        _C("off", b'\x31', "3D Subtitle Correction - Off"),
        _C("on", b'\x30', "3D Subtitle Correction - On"),
      ]),
    _G("lens_memory", b'\x49\x4E\x4D', commands=[
        _C("save_1", b'\x53\x30', "Lens Memory Save - Memory 1"),
        _C("save_2", b'\x53\x31', "Lens Memory Save - Memory 2"),
        _C("save_3", b'\x53\x32', "Lens Memory Save - Memory 3"),
        _C("select_1", b'\x4C\x30', "Lens Memory Select - Memory 1"),
        _C("select_2", b'\x4C\x31', "Lens Memory Select - Memory 2"),
        _C("select_3", b'\x4C\x32', "Lens Memory Select - Memory 3"),
      ]),
    _G("test_command", b'\x01\x00', commands=[
        _C("null_command", b'\x00', "Null Command (to check communication)"),
      ]),
    _G("remote_control", b'\x52\x43\x37\x33', commands=[
        # Infrared remote control commands... These commands perform the same action as pressing the corresponding
        # button on the remote control.
        # The following list is auto-generated from CSV file derived from doc PDF by import_ir_remote_codes.py. Do not
        # hand-edit.

        # {{ begin_ir_code_list }}
        _C("3d_setting", b'\x44\x35', "3D Setting - Direct access to 3D Setting menu (X30/X70/X90/RS45/55/65)"),
        _C("3d_format_next", b'\x44\x36', "3D Format - Cycles through all available 3D formats (X30/X70/X90/RS45/55/65)"),
        _C("advanced_picture_adjust", b'\x37\x33', "Advanced - Direct access to Picture Adjust > Advanced menu (HD550/950/990/X3/X7/X9/ X30/X70/X90/RS15/25/35/40/50/60/45/55/65)"),

        # overload
        _C("anamorphic_off", b'\x32\x34', "Anamorphic - Off (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65) Vertical Stretch - Off (HD350/750/950/990/RS10/20/25/35)"),
        _C("vertical_stretch_off", b'\x32\x34', "Vertical Stretch - Off (HD350/550/750/950/990/RS10/15/20/25/35) Anamorphic - Off (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),

        # overload
        _C("anamorphic_a", b'\x32\x33', "Anamorphic - A (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65) Vertical Stretch - On (HD350/750/950/990/RS10/20/25/35)"),
        _C("vertical_stretch_on", b'\x32\x33', "Vertical Stretch - On (HD350/550/750/950/990/RS10/15/20/25/35) Anamorphic - A (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),

        _C("anamorphic_b", b'\x32\x42', "Anamorphic - B (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("anamorphic_next", b'\x43\x35', "Anamorphic - Cycles through Off/A/B (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("aspect_16_9", b'\x32\x36', "Aspect - 16:9"),
        _C("aspect_4_3", b'\x32\x35', "Aspect - 4:3"),
        _C("aspect_zoom", b'\x32\x37', "Aspect - Zoom"),
        _C("aspect_auto", b'\x41\x45', "Aspect (PC) - Auto (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("aspect_pc_full", b'\x42\x30', "Aspect (PC) - Full (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("aspect_pc_just", b'\x41\x46', "Aspect (PC) - Just (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("aspect_up", b'\x37\x37', "Aspect + (cycles through all available modes)"),
        _C("auto_align", b'\x31\x33', "Auto Align (PC input on HD750/950/990/X7/X9/ X70/X90/RS20/25/35/50/60/55/65)"),
        _C("auto_lens_centre", b'\x43\x39', "Auto Lens Centre (X3/X7/X9/X70/X90/RS50/60/45/55/65)"),
        _C("back", b'\x30\x33', "Back - Steps backwards through menus and removes any OSD messages"),
        _C("bnr_off", b'\x31\x30', "BNR (Block Noise Reduction) - Off"),
        _C("bnr_on", b'\x30\x46', "BNR (Block Noise Reduction) - On"),
        _C("bright_level_down", b'\x41\x33', "Bright Level - (X7/X9/X70/X90/RS50/60/55/65)"),
        _C("bright_level_up", b'\x41\x32', "Bright Level + (X7/X9/X70/X90/RS50/60/55/65)"),
        _C("brightness_down", b'\x37\x42', "Brightness \u2013"),
        _C("brightness_up", b'\x37\x41', "Brightness +"),
        _C("brightness_adj", b'\x30\x39', "Brightness Adj. (Adjustment Bar On/Off toggle)"),
        _C("cec_off", b'\x35\x37', "CEC - Off"),
        _C("cec_on", b'\x35\x36', "CEC - On"),
        _C("cmd_next", b'\x38\x41', "Clear Motion Drive - Cycles through: Off/ Mode 1/Mode 2/Mode 3/Mode 4/Inverse Telecine (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("cmd_off", b'\x34\x37', "Clear Motion Drive - Off (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("cmd_mode_1", b'\x43\x45', "Clear Motion Drive - Mode 1 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("cmd_mode_2", b'\x43\x46', "Clear Motion Drive - Mode 2 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("cmd_mode_3", b'\x34\x38', "Clear Motion Drive - Mode 3 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("cmd_mode_4", b'\x34\x39', "Clear Motion Drive - Mode 4 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("cmd_inverse_telecine", b'\x34\x41', "Clear Motion Drive - Inverse Telecine (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("colour_down", b'\x37\x44', "Colour \u2013"),
        _C("colour_up", b'\x37\x43', "Colour +"),
        _C("colour_adj", b'\x31\x35', "Colour Adj. (Adjustment Bar On/Off toggle)"),
        _C("colour_management_off", b'\x36\x30', "Colour Management - Off (HD750/950/990/ X7/X9/RS20/25/35/50/60/55/65)"),
        _C("colour_management_custom_1", b'\x36\x31', "Colour Management - Custom 1 (HD750/950/ 990/X7/X9/RS20/25/35/50/60/55/65)"),
        _C("colour_management_custom_2", b'\x36\x32', "Colour Management - Custom 2 (HD750/950/ 990/X7/X9/RS20/25/35/50/60/55/65)"),
        _C("colour_management_custom_3", b'\x36\x33', "Colour Management - Custom 3 (HD750/950/ 990/X7/X9/RS20/25/35/50/60/55/65)"),
        _C("colour_management_next", b'\x38\x39', "Colour Management - Cycles through: Off/ Custom 1/Custom 2/Custom 3 (X7/X9/X70/X90/RS50/60/55/65)"),
        _C("colour_profile_next", b'\x38\x38', "Colour Profile - Cycles through all available Colour Profiles (X7/X9/X79/X90/RS50/60/55/65)"),
        _C("colour_space_next", b'\x43\x44', "Colour Space - Cycles through Standard/ Wide 1/Wide 2 (X3/X30/RS40/RS45)"),
        _C("colour_temp_5800k", b'\x34\x45', "Colour Temp. - 5800K (HD350/550/750/950/990/RS10/15/20/25/35)"),
        _C("colour_temp_6500k", b'\x34\x46', "Colour Temp. - 6500K"),
        _C("colour_temp_7500k", b'\x35\x30', "Colour Temp. - 7500K (HD350/550/750/950/990/RS10/15/20/25/35)"),
        _C("colour_temp_9300k", b'\x35\x31', "Colour Temp. - 9300K (HD350/550/750/950/990/RS10/15/20/25/35)"),
        _C("colour_temp_custom_1", b'\x35\x33', "Colour Temp. - Custom 1"),
        _C("colour_temp_custom_2", b'\x35\x34', "Colour Temp. - Custom 2"),
        _C("colour_temp_custom_3", b'\x35\x35', "Colour Temp. - Custom 3"),
        _C("colour_temp_high_bright", b'\x35\x32', "Colour Temp. - High Bright (HD350/550/750/ 950/990/X3/X30/RS10/15/20/25/35/40/45)"),
        _C("colour_temp_next", b'\x37\x36', "Colour Temp. + (cycles through all options)"),
        _C("colour_temperature_gain_blue_down", b'\x39\x31', "Colour Temperature Gain Blue \u2013 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("colour_temperature_gain_blue_up", b'\x39\x30', "Colour Temperature Gain Blue + (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("colour_temperature_gain_green_down", b'\x38\x46', "Colour Temperature Gain Green \u2013 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("colour_temperature_gain_green_up", b'\x38\x45', "Colour Temperature Gain Green + (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("colour_temperature_gain_red_down", b'\x38\x44', "Colour Temperature Gain Red \u2013 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("colour_temperature_gain_red_up", b'\x38\x43', "Colour Temperature Gain Red + (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("colour_temperature_offset_blue_down", b'\x39\x37', "Colour Temperature Offset Blue \u2013 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("colour_temperature_offset_blue_up", b'\x39\x36', "Colour Temperature Offset Blue + (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("colour_temperature_offset_green_down", b'\x39\x35', "Colour Temperature Offset Green \u2013 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("colour_temperature_offset_green_up", b'\x39\x34', "Colour Temperature Offset Green + (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("colour_temperature_offset_red_down", b'\x39\x33', "Colour Temperature Offset Red \u2013 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("colour_temperature_offset_red_up", b'\x39\x32', "Colour Temperature Offset Red + (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("contrast_down", b'\x37\x39', "Contrast \u2013"),
        _C("contrast_up", b'\x37\x38', "Contrast +"),
        _C("contrast_adj", b'\x30\x41', "Contrast Adj. (Adjustment Bar On/Off toggle)"),
        _C("cti_off", b'\x35\x43', "CTI (Colour Transient Improvement) - Off (HD350/550/750/950/990/RS10/15/20/25/35)"),
        _C("cti_low", b'\x35\x44', "CTI (Colour Transient Improvement) - Low (HD350/550/750/950/990/RS10/15/20/25/35)"),
        _C("cti_middle", b'\x35\x45', "CTI (Colour Transient Improvement) - Middle (HD350/550/750/950/990/RS10/15/20/25/35)"),
        _C("cti_high", b'\x35\x46', "CTI (Colour Transient improvement) - High (HD350/550/750/950/990/RS10/15/20/25/35)"),
        _C("cursor_down", b'\x30\x32', "Cursor Down \u25bc"),
        _C("cursor_left", b'\x33\x36', "Cursor Left \u25c4"),
        _C("cursor_right", b'\x33\x34', "Cursor Right \u25ba"),
        _C("cursor_up", b'\x30\x31', "Cursor Up \u25b2"),
        _C("dark_level_down", b'\x41\x35', "Dark Level \u2013 (X7/X9/X70/X90/RS50/60/55/65)"),
        _C("dark_level_up", b'\x41\x34', "Dark Level + (X7/X9/X70/X90/RS50/60/55/65)"),
        _C("detail_enhance_down", b'\x31\x32', "Detail Enhance \u2013"),
        _C("detail_enhance_up", b'\x31\x31', "Detail Enhance +"),
        _C("picture_tone_blue_down", b'\x41\x31', "Picture Tone Blue \u2013 (X7/X9/RS50/60 - Film Mode Only) (X70/X90/RS55/65 - All Modes)"),
        _C("picture_tone_blue_up", b'\x41\x30', "Picture Tone Blue + (X7/X9/RS50/60 - Film Mode Only) (X70/X90/RS55/65 - All Modes)"),
        _C("picture_tone_green_down", b'\x39\x46', "Picture Tone Green \u2013 (X7/X9/RS50/60 - Film Mode Only) (X70/X90/RS55/65 - All Modes)"),
        _C("picture_tone_green_up", b'\x39\x45', "Picture Tone Green + (X7/X9/RS50/60 - Film Mode Only) (X70/X90/RS55/65 - All Modes)"),
        _C("picture_tone_red_down", b'\x39\x44', "Picture Tone Red \u2013 (X7/X9/RS50/60 - Film Mode Only) (X70/X90/RS55/65 - All Modes)"),
        _C("picture_tone_red_up", b'\x39\x43', "Picture Tone Red + (X7/X9/RS50/60 - Film Mode Only) (X70/X90/RS55/65 - All Modes)"),
        _C("picture_tone_white_down", b'\x39\x42', "Picture Tone White \u2013 (X7/X9/RS50/60 - Film Mode Only) (X70/X90/RS55/65 - All Modes)"),
        _C("picture_tone_white_up", b'\x39\x41', "Picture Tone White + (X7/X9/RS50/60 - Film Mode Only) (X70/X90/RS55/65 - All Modes)"),
        _C("gamma_a", b'\x33\x39', "Gamma - A"),
        _C("gamma_b", b'\x33\x41', "Gamma - B"),
        _C("gamma_c", b'\x33\x42', "Gamma - C"),
        _C("gamma_custom_1", b'\x33\x43', "Gamma - Custom 1"),
        _C("gamma_custom_2", b'\x33\x44', "Gamma - Custom 2"),
        _C("gamma_custom_3", b'\x33\x45', "Gamma - Custom 3"),
        _C("gamma_d", b'\x33\x46', "Gamma - D (HD550/950/990/X3/X7/X9/ X30/X70/X90/RS15/25/35/40/50/60/45/55/65)"),
        _C("gamma_normal", b'\x33\x38', "Gamma - Normal"),
        _C("gamma_next", b'\x37\x35', "Gamma + (cycles through all options)"),
        _C("hide_off", b'\x44\x31', "Hide - Off (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("hide_on", b'\x44\x30', "Hide - On (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("hide", b'\x31\x44', "Hide (On/Off toggle)"),
        _C("horizontal_position_down", b'\x41\x42', "Horizontal Position \u2013 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("horizontal_position_up", b'\x41\x41', "Horizontal Position + (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("information", b'\x37\x34', "Information (displays Information tab of menu)"),
        _C("input_component", b'\x34\x44', "Input - Component"),
        _C("input_hdmi_1", b'\x37\x30', "Input - HDMI 1"),
        _C("input_hdmi_2", b'\x37\x31', "Input - HDMI 2"),
        _C("input_pc", b'\x34\x36', "Input - PC (HD750/950/990/X7/X9/X70/X90 RS20/25/35/50/60/55/65)"),
        _C("input_s_video", b'\x34\x43', "Input - S-Video (HD350/550/750/950/990)"),
        _C("input_video", b'\x34\x42', "Input - Video (HD350/550/750/950/990)"),
        _C("input_next", b'\x30\x38', "Input + (cycles through all available inputs)"),
        _C("isf_day", b'\x36\x34', "ISF - Day (X7/X9/X70/X90/RS50/60/55/65)"),
        _C("isf_night", b'\x36\x35', "ISF - Night (X7/X9/X70/X90/RS50/60/55/65)"),
        _C("isf_off", b'\x35\x41', "ISF - Off (HD950/990/X7/X9/X70/X90/ RS25/35/50/60/55/65)"),
        _C("isf_on", b'\x35\x42', "ISF - On (HD950/990/X7/X9/X70/X90/ RS25/35/50/60/55/65)"),
        _C("keystone_correction_horizontal_down", b'\x34\x31', "Keystone Correction Horizontal \u2013"),
        _C("keystone_correction_horizontal_up", b'\x34\x30', "Keystone Correction Horizontal +"),
        _C("keystone_correction_vertical_down", b'\x31\x43', "Keystone Correction Vertical \u2013"),
        _C("keystone_correction_vertical_up", b'\x31\x42', "Keystone Correction Vertical +"),
        _C("lens_aperture_1", b'\x32\x38', "Lens Aperture - 1 (HD350/HD550)"),
        _C("lens_aperture_2", b'\x32\x39', "Lens Aperture - 2 (HD350/HD550)"),
        _C("lens_aperture_3", b'\x32\x41', "Lens Aperture - 3 (HD350/HD550)"),
        _C("lens_aperture_down", b'\x31\x46', "Lens Aperture \u2013 If Lens Aperture Gauge is not displayed - displays gauge. If Lens Aperture Gauge is already displayed - Lens Aperture is decreased (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("lens_aperture_up", b'\x31\x45', "Lens Aperture + If Lens Aperture Gauge is not displayed - displays gauge. If Lens Aperture Gauge is already displayed - Lens Aperture is increased (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("lens_aperture_adj", b'\x32\x30', "Lens Aperture Adj. (HD350/750/950/990/ RS10/20/25/35 - Adjustment Bar On/Off toggle) (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65 - Displays Adjustment Bar) (HD550/RS15 - Cycles through all options)"),
        _C("lens_control_next", b'\x33\x30', "Lens Control (cycles through all options)"),
        _C("lens_focus_down", b'\x33\x32', "Lens Focus \u2013"),
        _C("lens_focus_up", b'\x33\x31', "Lens Focus +"),
        _C("lens_memory_next", b'\x44\x34', "Lens Memory - Cycles through Lens Memory Pages: Select/Save/Name Edit (X30/X70/X90/RS45/55/65)"),
        _C("lens_memory_1", b'\x44\x38', "Lens Memory 1 (X30/X70/X90/RS45/55/65)"),
        _C("lens_memory_2", b'\x44\x39', "Lens Memory 2 (X30/X70/X90/RS45/55/65)"),
        _C("lens_memory_3", b'\x44\x41', "Lens Memory 3 (X30/X70/X90/RS45/55/65)"),
        _C("lens_shift_down", b'\x32\x32', "Lens Shift - Down"),
        _C("lens_shift_left", b'\x34\x34', "Lens Shift - Left"),
        _C("lens_shift_right", b'\x34\x33', "Lens Shift - Right"),
        _C("lens_shift_up", b'\x32\x31', "Lens Shift - Up"),
        _C("lens_zoom_in", b'\x33\x35', "Lens Zoom - In"),
        _C("lens_zoom_out", b'\x33\x37', "Lens Zoom - Out"),
        _C("mask_bottom_down", b'\x42\x38', "Mask Bottom \u2013 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("mask_bottom_up", b'\x42\x37', "Mask Bottom + (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("mask_left_down", b'\x42\x32', "Mask Left \u2013 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("mask_left_up", b'\x42\x31', "Mask Left + (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("mask_right_down", b'\x42\x34', "Mask Right \u2013 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("mask_right_up", b'\x42\x33', "Mask Right + (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("mask_top_down", b'\x42\x36', "Mask Top \u2013 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("mask_top_up", b'\x42\x35', "Mask Top + (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("menu", b'\x32\x45', "Menu (On/Off toggle)"),
        _C("menu_position", b'\x34\x32', "Menu Position (HD550/950/990/X3/X7/X9/ X30/X70/X90/RS15/25/35/40/50/60/45/55/65)"),
        _C("mnr_down", b'\x30\x45', "MNR (Mosquito Noise Reduction) \u2013"),
        _C("mnr_up", b'\x30\x44', "MNR (Mosquito Noise Reduction) +"),
        _C("nr", b'\x31\x38', "NR (toggles display of RNR/MNR) (HD350/550/750/950/990/RS10/15/20/25/35)"),
        _C("ok", b'\x32\x46', "OK (to accept currently selected option)"),
        _C("phase_down", b'\x41\x39', "Phase (PC Input) \u2013 (X7/X9/X70/X90/RS50/60/55/65)"),
        _C("phase_up", b'\x41\x38', "Phase (PC Input) + (X7/X9/X70/X90/RS50/60/55/65)"),
        _C("picture_adjust", b'\x37\x32', "Picture Adjust (HD550/750/990/X3/X7/X9/ X30/X70/X90/RS15/25/35/40/50/60/45/55/65)"),
        _C("picture_mode_3d", b'\x38\x37', "Picture Mode - 3D (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("picture_mode_cinema_1", b'\x36\x39', "Picture Mode - Cinema 1 (X3/X7/X9/X30/X70/ X90/RS40/50/60/45/55/65 - Film Mode)"),
        _C("picture_mode_cinema_2", b'\x36\x38', "Picture Mode - Cinema 2 (X3/X7/X9/X30/X70/ X90/RS40/50/60/45/55/65 - Cinema Mode)"),
        _C("picture_mode_cinema_3", b'\x36\x36', "Picture Mode - Cinema 3 (HD550/750/990/ RS15/25/35) (X3/X7/X9/X30/X70/X90/ RS40/50/60/45/55/65 - Animation Mode)"),
        _C("picture_mode_dynamic", b'\x36\x42', "Picture Mode - Dynamic (HD350/550/750/950/990)"),
        _C("picture_mode_natural", b'\x36\x41', "Picture Mode - Natural"),
        _C("picture_mode_stage", b'\x36\x37', "Picture Mode - Stage"),
        _C("picture_mode_thx", b'\x36\x46', "Picture Mode - THX (HD750/950/990/X7/X9/ X70/X90/RS20/25/35/50/60/55/65)"),
        _C("picture_mode_user_1", b'\x36\x43', "Picture Mode - User 1"),
        _C("picture_mode_user_2", b'\x36\x44', "Picture Mode - User 2"),
        _C("picture_mode_user_3", b'\x36\x45', "Picture Mode - User 3 (HD550/750/950/990/ X3/X30/RS20/25/35/40/45)"),
        _C("picture_mode_user_4", b'\x43\x41', "Picture Mode - User 4 (X30/X70/X90/RS45/55/65)"),
        _C("picture_mode_user_5", b'\x43\x42', "Picture Mode - User 5 (X30/X70/X90/RS45/55/65)"),
        _C("pixel_shift_horizontal_blue_down", b'\x42\x45', "Pixel Shift - Horizontal Blue \u2013 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("pixel_shift_horizontal_blue_up", b'\x42\x44', "Pixel Shift - Horizontal Blue + (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("pixel_shift_horizontal_green_down", b'\x42\x43', "Pixel Shift - Horizontal Green \u2013 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("pixel_shift_horizontal_green_up", b'\x42\x42', "Pixel Shift - Horizontal Green + (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("pixel_shift_horizontal_red_down", b'\x42\x41', "Pixel Shift - Horizontal Red \u2013 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("pixel_shift_horizontal_red_up", b'\x42\x39', "Pixel Shift - Horizontal Red + (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("pixel_shift_vertical_blue_down", b'\x43\x34', "Pixel Shift - Vertical Blue \u2013 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("pixel_shift_vertical_blue_up", b'\x43\x33', "Pixel Shift - Vertical Blue + (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("pixel_shift_vertical_green_down", b'\x43\x32', "Pixel Shift - Vertical Green \u2013 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("pixel_shift_vertical_green_up", b'\x43\x31', "Pixel Shift - Vertical Green + (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("pixel_shift_vertical_red_down", b'\x43\x30', "Pixel Shift - Vertical Red \u2013 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("pixel_shift_vertical_red_up", b'\x42\x46', "Pixel Shift - Vertical Red + (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("power_off", b'\x30\x36', "Power - Off (send twice with short delay between to switch off)"),
        _C("power_on", b'\x30\x35', "Power - On"),
        _C("rnr_down", b'\x30\x43', "RNR (Random Noise Reduction) \u2013"),
        _C("rnr_up", b'\x30\x42', "RNR (Random Noise Reduction) +"),
        _C("screen_adjust_off", b'\x38\x30', "Screen Adjust - Off (X3/X30/RS40/45)"),
        _C("screen_adjust_a", b'\x38\x31', "Screen Adjust - A (X3/X30/RS40/45)"),
        _C("screen_adjust_b", b'\x38\x32', "Screen Adjust - B (X3/X30/RS40/45)"),
        _C("screen_adjust_c", b'\x38\x33', "Screen Adjust - C (X3/X30/RS40/45)"),
        _C("sharpness_down", b'\x37\x46', "Sharpness \u2013"),
        _C("sharpness_up", b'\x37\x45', "Sharpness +"),
        _C("sharpness_adj", b'\x31\x34', "Sharpness Adj. (Adjustment Bar On/Off toggle)"),
        _C("shutter_close", b'\x31\x39', "Shutter - Close (HD550/950/990/X3/X7/X9/ X30/X70/X90/RS15/25/35/40/50/60/45/55/65)"),
        _C("shutter_open", b'\x31\x41', "Shutter - Open (HD550/950/990/X3/X7/X9/ X30/X70/X90/RS15/25/35/40/50/60/45/55/65)"),
        _C("shutter_off", b'\x32\x44', "Shutter - Off - Un-synchronises shutter with \u201cHide\u201d function (HD550/950/990/X3/X7/X9/ X30/X70/X90/RS15/25/35/40/50/60/45/55/65)"),
        _C("shutter_on", b'\x32\x43', "Shutter - On - Synchronises shutter with \u201cHide\u201d function (HD550/950/990/X3/X7/X9/ X30/X70/X90/RS15/25/35/40/50/60/45/55/65)"),
        _C("test_pattern_next", b'\x35\x39', "Test Pattern (cycles through all patterns) (HD350/550/750/950/990/RS10/15/20/25/35)"),
        _C("thx_bright", b'\x38\x35', "THX - Bright (X7/X9/X70/X90/RS50/60/55/65)"),
        _C("thx_dark", b'\x38\x36', "THX - Dark (X7/X9/X70/X90/RS50/60/55/65)"),
        _C("thx_off", b'\x43\x37', "THX - Off (X7/X9/X70/X90/RS50/60/55/65)"),
        _C("thx_on", b'\x43\x38', "THX - On (X7/X9/X70/X90/RS50/60/55/65)"),
        _C("tint_down", b'\x39\x39', "Tint \u2013 (X3/X7/X9/X30/X70/X90/RS40/ 50/60/45/55/65)"),
        _C("tint_up", b'\x39\x38', "Tint + (X3/X7/X9/X30/X70/X90/RS40/ 50/60/45/55/65)"),
        _C("tint_adj", b'\x31\x36', "Tint Adj. (Adjustment Bar On/Off toggle)"),
        _C("tracking_down", b'\x41\x37', "Tracking \u2013 (PC Input) (X7/X9/X70/X90/RS50/60/55/65)"),
        _C("tracking_up", b'\x41\x36', "Tracking + (PC Input) (X7/X9/X70/X90/RS50/60/55/65)"),
        _C("user_next", b'\x44\x37', "User - Cycles through User 1 - User 5 Picture Modes (X30/X70/X90/RS45/55/65)"),
        _C("vertical_position_down", b'\x41\x44', "Vertical Position \u2013 (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        _C("vertical_position_up", b'\x41\x43', "Vertical Position + (X3/X7/X9/X30/X70/X90/RS40/50/60/45/55/65)"),
        # {{ end_ir_code_list }}
      ]),

      # the remaining command groups are advanced commands with advanced response payloads

      _G("power_status", b'\x50\x57', [
              _C("query", b'', "Query Power status", response_map=power_status_map),
            ],
            response_payload_length=1,
        ),
      _G("input_status", b'\x49\x50', [
              _C("query", b'', "Query current video input", response_map=input_status_map),
            ],
            response_payload_length=1,
        ),
      _G("gamma_table_status", b'\x47\x54', [
              _C("query", b'', "Query current gamma table selection", response_map=gamma_table_status_map),
            ],
            response_payload_length=1,
        ),
      _G("gamma_value_status", b'\x47\x50', [
              _C("query", b'', "Query current gamma value", response_map=gamma_value_status_map),
            ],
            response_payload_length=1,
        ),
      _G("source_status", b'\x47\x50', [
              _C("query", b'', "Query current video source status", response_map=source_status_map),
            ],
            response_payload_length=1,
        ),
      _G("model_status", b'\x47\x50', [
              _C("query", b'', "Query current model code", response_map=model_status_map),
            ],
            response_payload_length=14,
        ),
  ]

command_metas: Dict[str, CommandMeta] = {}
for _group in _group_metas:
    for _command in _group.commands.values():
        _cmd_name = f"{_group.name}.{_command.name}"
        assert not _cmd_name in command_metas
        command_metas[_cmd_name] = _command
