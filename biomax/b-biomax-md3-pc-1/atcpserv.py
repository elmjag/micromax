import asyncio
from queue import Queue
from threading import Thread


class AsyncTCPServer:
    def __init__(self, port, new_connection_callback):
        self._port = port
        self._new_connection_callback = new_connection_callback

    def start(self):
        backchannel = Queue()
        self._thread = Thread(target=lambda: asyncio.run(self._run(backchannel)))
        self._thread.start()

        #
        # wait until _run() is finished with setting up socket serving stuff,
        # _run() signals that it is ready by sending event loop and exit event objects,
        # which we can use for stopping the serving thread
        #
        self._loop, self._exit_event = backchannel.get()

    def stop(self):
        self._loop.call_soon_threadsafe(self._exit_event.set)
        self._thread.join()

    async def _run(self, backchannel: Queue):
        server = await asyncio.start_server(
            self._new_connection_callback, host="0.0.0.0", port=self._port
        )
        asyncio.create_task(server.serve_forever())

        loop = asyncio.get_running_loop()
        exit_event = asyncio.Event()
        backchannel.put((loop, exit_event))

        await exit_event.wait()
