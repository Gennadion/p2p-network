from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class DirectoryMonitor:
    def __init__(self, shared_folder, indexer):
        self.shared_folder = shared_folder # Path to the shared folder
        self.indexer = indexer # FileIndexer object
        self.event_handler = self.ChangeHandler(self.indexer) # Event handler to change the index file
        self.observer = Observer() # Observer to monitor the shared folder

    class ChangeHandler(FileSystemEventHandler): # Override the FileSystemEventHandler class
        def __init__(self, indexer):
            self.indexer = indexer

        def on_created(self, event):
            if not event.is_directory:
                print("Created:", event.src_path)
                self.indexer.add_index_to_json(event.src_path)

        def on_deleted(self, event):
            if not event.is_directory:
                print("Deleted:", event.src_path)
                self.indexer.delete_index_from_json(event.src_path)

    def start(self):
        self.observer.schedule(self.event_handler, self.shared_folder, recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
