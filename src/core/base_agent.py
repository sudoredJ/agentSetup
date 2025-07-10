import logging
import sys
import threading
import time
import functools  # Added for partial functions if needed
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

class ThreadSafeSocketModeHandler(SocketModeHandler):
    """A thread-safe version of the SocketModeHandler."""
    def __init__(self, app, app_token, logger=None):
        super().__init__(app=app, app_token=app_token)
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def start(self):
        """Connect without signal handlers."""
        attempt = 1
        self.logger.info("Connecting to Slack (attempt #1)…")
        self.connect()
        self.logger.info("Connected!")
        
        while True:
            try:
                if not self.client or not self.client.is_connected():
                    attempt += 1
                    self.logger.warning(f"WebSocket disconnected – reconnecting (attempt #{attempt})…")
                    time.sleep(5)
                    self.connect()
                    self.logger.info("Reconnected!")
                time.sleep(1)
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"WebSocket error: {e}", exc_info=True)
                time.sleep(5)

    def close(self):
        """Close connection."""
        if self.client and self.client.is_connected():
            self.client.close()

class BaseAgent:
    """A base agent with Slack connection capabilities."""
    
    def __init__(self, name: str, token: str):
        self.name = name
        self.logger = logging.getLogger(name)
        self.app = App(token=token, logger=self.logger)
        self.client = self.app.client
        
        # ------------------------------------------------------------------
        # Wrap Slack client's api_call with verbose logging for ALL methods
        # ------------------------------------------------------------------
        original_api_call = self.client.api_call

        def _logged_api_call(method, http_verb="POST", files=None, data=None,
                             params=None, json=None, **kwargs):
            """Proxy that logs full request/response for every Slack API call."""
            self.logger.debug(
                f"[{self.name}] ⇢ Slack API Call: method={method} http_verb={http_verb} "
                f"files={bool(files)} params={params or json or data or kwargs}"
            )
            start_t = time.time()
            try:
                resp = original_api_call(
                    method,
                    http_verb=http_verb,
                    files=files,
                    data=data,
                    params=params,
                    json=json,
                    **kwargs,
                )
                elapsed = (time.time() - start_t) * 1000
                self.logger.debug(
                    f"[{self.name}] ⇠ Slack API Response: method={method} ok={resp.get('ok')} "
                    f"status={getattr(resp, 'status_code', 'n/a')} elapsed={elapsed:.2f}ms body={resp}"
                )
                return resp
            except Exception as err:
                self.logger.error(
                    f"[{self.name}] Slack API Error on '{method}': {err}", exc_info=True
                )
                raise

        # Monkey-patch once so we don't wrap multiple times even if BaseAgent is re-initialized
        if not getattr(self.client, "_api_call_wrapped", False):
            self.client.api_call = _logged_api_call  # type: ignore
            self.client._api_call_wrapped = True  # type: ignore

        try:
            auth_info = self.client.auth_test()
            self.logger.debug(f"[{self.name}] Full auth_test response: {auth_info}")
            self.bot_user_id = auth_info["user_id"]
            self.bot_name = auth_info.get("user", name)
            self.logger.info(f"Initialized as '{self.bot_name}' (ID: {self.bot_user_id})")
        except Exception as e:
            self.logger.error(f"Auth failed: {e}")
            sys.exit(1)

    def start_in_thread(self, app_token: str):
        """Start the agent in a separate thread."""
        handler = ThreadSafeSocketModeHandler(self.app, app_token, logger=self.logger)
        # Expose handler for diagnostics
        self._socket_handler = handler
        thread = threading.Thread(target=handler.start, name=f"Thread-{self.name}")
        thread.daemon = True
        thread.start()
        return handler 