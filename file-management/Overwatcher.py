from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from FileManager import FileManager

class DirectoryMonitor:
    def __init__(self, shared_folder, local_indexer):
        self.shared_folder = shared_folder # Path to the shared folder
        self.local_indexer = local_indexer # FileIndexer object
        self.event_handler = self.ChangeHandler(self.local_indexer) # Event handler to change the index file
        self.observer = Observer() # Observer to monitor the shared folder
        self.file_manager = FileManager(shared_folder) # File manager object

    class ChangeHandler(FileSystemEventHandler): # Override the FileSystemEventHandler class
        def __init__(self, indexer):
            self.indexer = indexer

        def on_created(self, event):
            if not event.is_directory:
                print("Created:", event.src_path)
                print("Indexing new file and sending an update message to peers...") 
                try:
                    self.file_manager.share_file(event.src_path)
                except Exception as e:
                    print(f"Error sharing file: {e}")

        def on_deleted(self, event):
            if not event.is_directory:
                print("Deleted:", event.src_path)
                print("Removing file from index and sending an update message to peers...")
                try:
                     self.file_manager.remove_file(event.src_path)
                except Exception as e:
                    print(f"Error removing file: {e}")


    def start(self):
        self.observer.schedule(self.event_handler, self.shared_folder, recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
