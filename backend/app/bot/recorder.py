"""Chunked audio recording on top of Pycord's WaveSink.

Per project risk #3: we use `discord.sinks.WaveSink` exactly as designed and
read finished audio from `sink.audio_data` in the recording-finished
callback. We do NOT subclass WaveSink or re-implement PCM/WAV handling.

Per project risk #4: a multi-hour session must not accumulate one giant
in-memory buffer per user. We bound memory by never letting a single
WaveSink run for the whole session - every `chunk_minutes`, the current
recording is stopped (which flushes that chunk to disk from inside the
finished callback) and a fresh WaveSink is started for the next chunk.

Ordering detail that matters here (verified against the installed py-cord
2.6.1 source): VoiceClient.recv_audio() runs in a background thread and, only
after its capture loop notices `recording` has gone False, calls
`self.sink.cleanup()` (finalizing that sink's WAV headers) and *then*
schedules the finished-callback coroutine. If we called `start_recording()`
again immediately after `stop_recording()` - i.e. from a concurrent timer -
`self.sink` could already have been reassigned to the *new* sink by the time
the old thread reaches `self.sink.cleanup()`, corrupting the old chunk.
To avoid that race, the periodic timer only ever calls `stop_recording()`;
the *next* `start_recording()` call is made from inside the finished
callback of the chunk it's replacing, which is only ever invoked after that
chunk's own cleanup has already completed.
"""
import asyncio
import logging
from pathlib import Path

import discord

logger = logging.getLogger(__name__)


class VoiceRecorder:
    def __init__(self, storage_dir: Path, session_log_id: int, chunk_minutes: int):
        self.storage_dir = storage_dir / f"session_{session_log_id}"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_minutes = chunk_minutes
        self._chunk_index = 0
        self._voice_client: discord.VoiceClient | None = None
        self._timer_task: asyncio.Task | None = None
        self._stopping = False

    def start(self, voice_client: discord.VoiceClient) -> None:
        self._voice_client = voice_client
        self._stopping = False
        self._chunk_index = 0
        self._start_chunk()
        self._timer_task = asyncio.create_task(self._chunk_timer())

    async def stop(self) -> None:
        """Stops recording for good, flushing the final (possibly partial)
        chunk to disk.
        """
        self._stopping = True
        if self._timer_task is not None:
            self._timer_task.cancel()
            self._timer_task = None
        if self._voice_client is not None and self._voice_client.recording:
            self._voice_client.stop_recording()

    def _start_chunk(self) -> None:
        assert self._voice_client is not None
        sink = discord.sinks.WaveSink()
        self._voice_client.start_recording(sink, self._on_chunk_finished, self._chunk_index)
        logger.info("Recording chunk %d started", self._chunk_index)

    async def _chunk_timer(self) -> None:
        try:
            while not self._stopping:
                await asyncio.sleep(self.chunk_minutes * 60)
                if self._stopping:
                    break
                if self._voice_client is not None and self._voice_client.recording:
                    # Only requests the stop; _on_chunk_finished starts the
                    # next chunk once this one has actually finished flushing.
                    self._voice_client.stop_recording()
        except asyncio.CancelledError:
            pass

    async def _on_chunk_finished(self, sink: discord.sinks.WaveSink, chunk_index: int) -> None:
        for user_id, audio in sink.audio_data.items():
            filename = self.storage_dir / f"user_{user_id}_chunk_{chunk_index:04d}.wav"
            audio.file.seek(0)
            with open(filename, "wb") as out_file:
                out_file.write(audio.file.read())
            logger.info("Saved chunk %d for discord user %s -> %s", chunk_index, user_id, filename)

        if not self._stopping:
            self._chunk_index += 1
            self._start_chunk()
