import logging
import threading
import time

from bot import LOGGER, app, download_dict, download_dict_lock, STOP_DUPLICATE_MIRROR

from ..status_utils.telegram_download_status import TelegramDownloadStatus
from .download_helper import DownloadHelper
from bot.helper.telegram_helper.message_utils import sendMarkup, sendStatusMessage
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper

global_lock = threading.Lock()
GLOBAL_GID = set()

logging.getLogger("pyrogram").setLevel(logging.WARNING)


class TelegramDownloadHelper(DownloadHelper):
    def __init__(self, listener):
        super().__init__()
        self.__listener = listener
        self.__resource_lock = threading.RLock()
        self.__name = ""
        self.__start_time = time.time()
        self.__gid = ""
        self.__user_bot = app
        self.__is_cancelled = False

    @property
    def gid(self):
        with self.__resource_lock:
            return self.__gid

    @property
    def download_speed(self):
        with self.__resource_lock:
            return self.downloaded_bytes / (time.time() - self.__start_time)

    def __onDownloadStart(self, name, size, file_id):
        with download_dict_lock:
            download_dict[self.__listener.uid] = TelegramDownloadStatus(
                self, self.__listener
            )
        with global_lock:
            GLOBAL_GID.add(file_id)
        with self.__resource_lock:
            self.name = name
            self.size = size
            self.__gid = file_id
        self.__listener.onDownloadStarted()

    def __onDownloadProgress(self, current, total):
        if self.__is_cancelled:
            self.__onDownloadError("Cancelled by user!")
            self.__user_bot.stop_transmission()
            return
        with self.__resource_lock:
            self.downloaded_bytes = current
            try:
                self.progress = current / self.size * 100
            except ZeroDivisionError:
                self.progress = 0

    def __onDownloadError(self, error):
        with global_lock:
            try:
                GLOBAL_GID.remove(self.gid)
            except KeyError:
                pass
        self.__listener.onDownloadError(error)

    def __onDownloadComplete(self):
        with global_lock:
            GLOBAL_GID.remove(self.gid)
        self.__listener.onDownloadComplete()

    def __download(self, message, path):
        download = self._bot.download_media(
            message,
            progress=self.__onDownloadProgress,
            file_name=path
        )
        if download is not None:
            self.__onDownloadComplete()
        elif not self.__is_cancelled:
            self.__onDownloadError("Internal error occurred")

    def add_download(self, message, path, filename):
        _message = self.__user_bot.get_messages(message.chat.id, message.message_id)
        media = None
        media_array = [_message.document, _message.video, _message.audio]
        for i in media_array:
            if i is not None:
                media = i
                break
        if media is not None:
            with global_lock:
                # For avoiding locking the thread lock for long time unnecessarily
                download = media.file_id not in GLOBAL_GID
            if filename == "":
                name = media.file_name
            else:
                name = filename
                path = path + name

            if download:
                if STOP_DUPLICATE_MIRROR:
                    LOGGER.info('Checking File/Folder if already in Drive...')
                    if self.__listener.isTar:
                        name = name + ".tar"
                    if self.__listener.extract:
                        smsg = None
                    else:
                        gd = GoogleDriveHelper()
                        smsg, button = gd.drive_list(name)
                    if smsg:
                        sendMarkup("File/Folder is already available in Drive.\nHere are the search results:", self.__listener.bot, self.__listener.update, button)
                        return
                self.__onDownloadStart(name, media.file_size, media.file_id)
                LOGGER.info(f"Downloading Telegram file with id: {media.file_id}")
                threading.Thread(target=self.__download, args=(_message, path)).start()
            else:
                self.__onDownloadError("File already being downloaded!")
        else:
            self.__onDownloadError("No document in the replied message")

    def cancel_download(self):
        LOGGER.info(f"Cancelling download on user request: {self.gid}")
        self.__is_cancelled = True
