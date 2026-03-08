import asyncio
import re
import subprocess

import decky
from env import env

log = decky.logger


def _find_alsa_cards_with_master():
    """Find ALSA card numbers that have a Master control."""
    cards = []
    try:
        result = subprocess.run(
            ['cat', '/proc/asound/cards'],
            capture_output=True, text=True, check=True
        )
        card_nums = re.findall(r'^\s*(\d+)\s+\[', result.stdout, re.MULTILINE)
        for card in card_nums:
            try:
                subprocess.run(
                    ['amixer', '-c', card, 'get', 'Master'],
                    capture_output=True, text=True, check=True
                )
                cards.append(card)
            except subprocess.CalledProcessError:
                pass
    except Exception:
        pass
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


def _set_alsa_volume(cards, volume_fraction, muted):
    """Set ALSA Master volume on the given cards.

    volume_fraction: 0.0–1.0+ from PipeWire (clamped to 0–100%).
    muted: whether to mute ALSA Master.
    """
    pct = max(0, min(100, round(volume_fraction * 100)))
    for card in cards:
        try:
            subprocess.run(
                ['amixer', '-c', card, 'set', 'Master', f'{pct}%'],
                capture_output=True, text=True
            )
            # Handle mute/unmute
            toggle = 'mute' if muted else 'unmute'
            subprocess.run(
                ['amixer', '-c', card, 'set', 'Master', toggle],
                capture_output=True, text=True
            )
        except Exception:
            pass


class VolumeForwarder:
    """Forwards PipeWire volume changes on jamesdsp_sink to ALSA hardware.

    When JamesDSP's virtual sink is the default PipeWire sink, the system
    volume slider only adjusts the virtual sink's PipeWire volume — but
    null-audio-sink monitor ports don't apply that volume to the audio data.
    This class listens for volume changes via `pactl subscribe` and applies
    them to the real ALSA Master mixer so the user hears the change.
    """

    def __init__(self):
        self._task = None
        self._proc = None
        self._last_volume = None
        self._last_muted = None
        self._cards = _find_alsa_cards_with_master()

    async def start(self):
        """Start the volume forwarding background task."""
        if self._task and not self._task.done():
            return
        self._task = asyncio.ensure_future(self._monitor())
        log.info(f'Volume forwarder started (ALSA cards: {self._cards})')

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
            volume, muted = await asyncio.get_event_loop().run_in_executor(
                None, _get_sink_volume
            )
            if volume is None:
                return

            if volume != self._last_volume or muted != self._last_muted:
                self._last_volume = volume
                self._last_muted = muted
                await asyncio.get_event_loop().run_in_executor(
                    None, _set_alsa_volume, self._cards, volume, muted
                )
        except Exception:
            pass
