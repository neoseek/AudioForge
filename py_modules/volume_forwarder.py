import asyncio
import math
import re
import subprocess
from dataclasses import dataclass
from typing import List

import decky
from env import env

log = decky.logger


# Fallback when the real dB range cannot be determined.
_DEFAULT_DB_FLOOR = 60.0

# ALSA simple-mixer control names to try, in priority order.
# "Master" is standard for built-in codecs; "PCM" is common for HDMI/DP;
# "Headphone" and "Speaker" appear on some USB DACs or split-control codecs.
_ALSA_CONTROL_CANDIDATES = ['Master', 'PCM', 'Headphone', 'Speaker']


@dataclass
class _CardInfo:
    """Resolved ALSA card + control information."""
    card: str          # ALSA card number as a string
    control: str       # Simple-mixer control name (e.g. "Master", "PCM")
    db_floor: float    # Absolute dB range of the control


def _get_db_range(card, control):
    """Query the dB range of *control* Playback Volume on ALSA *card*.

    Uses ``amixer -c <card> cget name='<control> Playback Volume'`` which
    prints a line like::

        ; type=INTEGER,...  | dBscale-min=-64.50dB,step=0.75dB,mute=0

    Returns the absolute value of dBscale-min (e.g. 64.5), or
    ``_DEFAULT_DB_FLOOR`` if the value cannot be determined.
    """
    try:
        result = subprocess.run(
            ['amixer', '-c', card, 'cget', f"name='{control} Playback Volume'"],
            capture_output=True, text=True, check=True
        )
        match = re.search(r'dBscale-min=(-?\d+\.?\d*)dB', result.stdout)
        if match:
            db_min = float(match.group(1))
            val = abs(db_min)
            if val > 0:
                return val
    except Exception:
        pass
    return _DEFAULT_DB_FLOOR


def _find_alsa_control(card):
    """Find the first usable playback volume control on ALSA *card*.

    Tries each name in ``_ALSA_CONTROL_CANDIDATES`` and returns the first
    one that exists, or ``None`` if none are found.
    """
    for name in _ALSA_CONTROL_CANDIDATES:
        try:
            subprocess.run(
                ['amixer', '-c', card, 'get', name],
                capture_output=True, text=True, check=True
            )
            return name
        except subprocess.CalledProcessError:
            continue
    return None


def _discover_alsa_cards() -> List[_CardInfo]:
    """Enumerate ALSA cards and return info for those with a volume control.

    Reads ``/proc/asound/cards`` to find card numbers, probes each for a
    usable playback control (Master, PCM, Headphone, Speaker), and queries
    the hardware dB range of the matched control.
    """
    cards: List[_CardInfo] = []
    try:
        result = subprocess.run(
            ['cat', '/proc/asound/cards'],
            capture_output=True, text=True, check=True
        )
        card_nums = re.findall(r'^\s*(\d+)\s+\[', result.stdout, re.MULTILINE)
        for card in card_nums:
            control = _find_alsa_control(card)
            if control is None:
                continue
            db_floor = _get_db_range(card, control)
            cards.append(_CardInfo(card=card, control=control, db_floor=db_floor))
            log.info(f'Discovered ALSA card {card}: '
                     f'control "{control}", dB floor {db_floor}')
    except Exception as e:
        log.warning(f'Failed to enumerate ALSA cards: {e}')
    return cards


def _get_sink_volume():
    """Read PipeWire volume and mute state for the default audio sink.

    Returns (volume_float, is_muted) or (None, None) on failure.
    """
    try:
        result = subprocess.run(
            ['wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@'],
            capture_output=True, text=True, env=env
        )
        # Output format: "Volume: 0.50" or "Volume: 0.50 [MUTED]"
        match = re.search(r'Volume:\s+(\d+\.?\d*)', result.stdout)
        if match:
            volume = float(match.group(1))
            muted = '[MUTED]' in result.stdout
            return volume, muted
    except Exception:
        pass
    return None, None


def _linear_to_alsa_pct(volume_fraction, db_floor):
    """Convert a PipeWire linear amplitude to an ALSA percentage.

    PipeWire reports volume as a linear amplitude multiplier, but ALSA's
    ``amixer`` percentage maps linearly across the hardware's **dB** range
    (e.g. 0 dB down to -64 dB on the Steam Deck's ALC257).  A naive
    ``round(linear * 100)`` produces a far-too-quiet ALSA level because
    50 % of the dB range is roughly -32 dB while 0.5 linear is only -6 dB.

    Conversion::

        dB   = 20 · log10(linear)
        pct  = clamp((1 + dB / db_floor) · 100,  0, 100)

    *db_floor* is the absolute dB range of the card's volume control,
    queried from ALSA hardware.
    """
    if volume_fraction <= 0.0:
        return 0
    clamped = min(volume_fraction, 1.0)
    db = 20.0 * math.log10(clamped)
    return max(0, min(100, round((1.0 + db / db_floor) * 100)))


def _set_alsa_volume(cards, volume_fraction, muted):
    """Set ALSA volume on all discovered hardware cards.

    *cards* is a list of ``_CardInfo`` from ``_discover_alsa_cards``.
    volume_fraction: 0.0-1.0+ linear amplitude from PipeWire.
    muted: whether to mute the control.
    """
    for info in cards:
        pct = _linear_to_alsa_pct(volume_fraction, info.db_floor)
        try:
            subprocess.run(
                ['amixer', '-c', info.card, 'set',
                 info.control, f'{pct}%'],
                capture_output=True, text=True
            )
            toggle = 'mute' if muted else 'unmute'
            subprocess.run(
                ['amixer', '-c', info.card, 'set',
                 info.control, toggle],
                capture_output=True, text=True
            )
        except Exception:
            pass


class VolumeForwarder:
    """Forwards PipeWire volume changes on jamesdsp_sink to ALSA hardware.

    When JamesDSP's virtual sink is the default PipeWire sink, the system
    volume slider only adjusts the virtual sink's PipeWire volume — but
    null-audio-sink monitor ports don't apply that volume to the audio data.
    This class listens for volume changes via ``pactl subscribe`` and applies
    them to the real ALSA hardware mixer so the user hears the change.

    ALSA cards with playback controls (Master, PCM, Headphone, Speaker)
    are discovered at startup.  The dB range is queried from hardware so
    the linear-to-percentage conversion is accurate per card.
    """

    def __init__(self):
        self._task = None
        self._proc = None
        self._last_volume = None
        self._last_muted = None
        self._cards = _discover_alsa_cards()

    async def start(self):
        """Start the volume forwarding background task."""
        if self._task and not self._task.done():
            return
        self._task = asyncio.ensure_future(self._monitor())
        log.info(f'Volume forwarder started (cards: {self._cards})')

    async def stop(self):
        """Stop the volume forwarding background task."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None
        log.info('Volume forwarder stopped')

    async def _monitor(self):
        """Subscribe to PipeWire sink events and forward volume changes."""
        while True:
            try:
                self._proc = await asyncio.create_subprocess_exec(
                    'pactl', 'subscribe',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                    env=env
                )
                # Do an initial sync on startup
                await self._check_and_forward()

                async for line in self._proc.stdout:
                    text = line.decode().strip()
                    # pactl subscribe outputs lines like:
                    #   Event 'change' on sink #42
                    if "'change'" in text and 'sink' in text:
                        await self._check_and_forward()

            except asyncio.CancelledError:
                if self._proc:
                    self._proc.terminate()
                raise
            except Exception as e:
                log.warning(f'Volume forwarder error: {e}, retrying...')
                await asyncio.sleep(2)

    async def _check_and_forward(self):
        """Read current sink volume and forward to ALSA if changed."""
        try:
            if not self._cards:
                return

            volume, muted = await asyncio.get_event_loop().run_in_executor(
                None, _get_sink_volume
            )
            if volume is None:
                return

            if volume != self._last_volume or muted != self._last_muted:
                self._last_volume = volume
                self._last_muted = muted
                cards = self._cards  # capture for executor
                await asyncio.get_event_loop().run_in_executor(
                    None, _set_alsa_volume, cards, volume, muted
                )
        except Exception:
            pass
