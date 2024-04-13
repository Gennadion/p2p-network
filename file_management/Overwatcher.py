from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
class DirectoryMonitor:
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    def __init__(self, shared_folder, local_indexer, file_manager):
        self.logger = logging.getLogger(__name__)
        logging.info(f"Initializing DirectoryMonitor for {shared_folder}")
        self.shared_folder = shared_folder
        self.local_indexer = local_indexer
        self.file_manager = file_manager
        self.event_handler = self.ChangeHandler(self.local_indexer, self.file_manager, self.logger)
        self.observer = Observer()

    class ChangeHandler(FileSystemEventHandler):
        def __init__(self, indexer, file_manager, logger):
            self.logger = logger
            self.indexer = indexer
            self.file_manager = file_manager

        def on_created(self, event):
            if not event.is_directory:
                logging.info(f"File created: {event.src_path}. Indexing and notifying peers.")
                try:
                    self.file_manager.share_file_index(event.src_path)
                    logging.info(f"Successfully shared file index for: {event.src_path}")
                except Exception as e:
                    logging.error(f"Error sharing file index for {event.src_path}: {e}")

        def on_deleted(self, event):
            if not event.is_directory:
                logging.info(f"File deleted: {event.src_path}. Removing from index and notifying peers.")
                try:
                    self.file_manager.unshare_file_index(event.src_path)
                    logging.info(f"Successfully unshared file index for: {event.src_path}")
                except Exception as e:
                    logging.error(f"Error removing file index for {event.src_path}: {e}")

    def start(self):
        logging.info("Starting directory monitoring.")
        self.observer.schedule(self.event_handler, self.shared_folder, recursive=True)
        self.observer.start()

    def stop(self):
        logging.info("Stopping directory monitoring.")
        self.observer.stop()
        self.observer.join()
