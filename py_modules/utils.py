import asyncio
import logging
import os
import subprocess
from typing import List
import decky

from env import env


def get_loggers(jdsp_log_dir, jdsp_log, decky_plugin: decky):
    jdsp_log_dir = os.path.join(decky_plugin.DECKY_PLUGIN_LOG_DIR, "jdsp")
    if not os.path.exists(jdsp_log_dir):
        os.makedirs(jdsp_log_dir)

    jdsp_formatter = logging.Formatter()
    jdsp_handler = logging.FileHandler(jdsp_log)
    jdsp_handler.setFormatter(jdsp_formatter)
    jdsp_logger = logging.getLogger("decksp_jdsp")
    jdsp_logger.setLevel(logging.INFO)
    jdsp_logger.addHandler(jdsp_handler)
    jdsp_logger.propagate = False

    return {"plugin_logger": decky_plugin.logger, "jdsp_logger": jdsp_logger}


def flatpak_CMD(args: List[str], noCheck=False):
    return subprocess.run(args=['flatpak'] + args, check=not noCheck, capture_output=True, text=True, env=env)

def get_xauthority():
    try:
        result = subprocess.run(['systemctl', '--user', 'show-environment'], capture_output=True, text=True, check=True, env=env)
        for line in result.stdout.split("\n"):
            if line.startswith("XAUTHORITY="):
                return line.split("=", 1)[1]
    except subprocess.CalledProcessError as e:
        return
    
def compare_versions(version1, version2):
    def normalize(v):
        return [int(x) for x in v.split("-")[0].split(".")]
    
    v1 = normalize(version1)
    v2 = normalize(version2)
    
    for i in range(max(len(v1), len(v2))):
        part_v1 = v1[i] if i < len(v1) else 0
        part_v2 = v2[i] if i < len(v2) else 0
        
        if part_v1 < part_v2:
            return -1
        elif part_v1 > part_v2:
            return 1
    return 0

class SettingDef:
    @classmethod
    def defaults(cls):
        return {
            getattr(cls, attr): getattr(cls.Defaults, attr)
            for attr in dir(cls.Defaults)
            if not attr.startswith("__")
        }
        
def wrap_error(e):
    return { 'error': str(e) }

def set_alsa_master_volume():
    """Set ALSA Master volume to 100% on all cards that have a Master control.

    When JamesDSP's virtual sink is the default PipeWire sink, PipeWire volume
    changes only affect the virtual sink and no longer control the ALSA Master.
    The ALSA Master resets to the kernel driver default on every boot (e.g. 69%
    for ALC257), so we need to max it out when JamesDSP takes over.
    """
    log = decky.logger
    try:
        result = subprocess.run(
            ['cat', '/proc/asound/cards'],
            capture_output=True, text=True, check=True
        )
        card_nums = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line and line[0].isdigit():
                card_nums.append(line.split()[0])

        for card in card_nums:
            try:
                subprocess.run(
                    ['amixer', '-c', card, 'set', 'Master', '100%'],
                    capture_output=True, text=True, check=True
                )
                log.info(f'Set ALSA Master to 100% on card {card}')
            except subprocess.CalledProcessError:
                pass  # Card has no Master control, skip
    except Exception as e:
        log.warning(f'Failed to set ALSA Master volume: {e}')

async def restart_wireplumber(timeout: float, post_delay: float):
    try:
        subprocess.run(['systemctl', '--user', 'restart', 'wireplumber'], capture_output=True, text=True, check=True, env=env)
    except subprocess.CalledProcessError as e:
        raise Exception(f'wireplumber restart failed: {e}')
    
    async def check_sink():
        try:
            dump = subprocess.check_output(["pw-dump"], text=True, env=env)
        except subprocess.CalledProcessError as e:
            raise Exception(f"pw-dump failed: {e}")
        
        try:
            result = subprocess.run(
                [
                    'jq', '-c',
                    '.[] '
                    '| select(.type == "PipeWire:Interface:Node") '
                    '| select(.info.props["media.class"] == "Audio/Sink") '
                    '| select(.info.props["node.description"] != null) '
                    '| {id: .id, desc: .info.props["node.description"]}'
                ],
                input=dump,
                capture_output=True, 
                text=True,
                check=True,
                env=env
            )
            return bool(result.stdout.strip())
            
        except subprocess.CalledProcessError as e:
            raise Exception(f'jq failed to parse pw-dump: {e}')

    async def poll():
        while not await check_sink():
            await asyncio.sleep(0.5)
    try:
        await asyncio.wait_for(poll(), timeout=timeout)
        await asyncio.sleep(post_delay)
    except asyncio.TimeoutError:
        raise Exception(f'Failed to find default pipewire sink within time limit')
