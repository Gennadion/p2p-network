import json
import unittest
import os
from unittest.mock import Mock

from file_management.FileIndexer import FileIndexer


class TestFileIndexer(unittest.TestCase):

    def setUp(self):
        self.index_file = 'test_index.json'
        self.file_indexer = FileIndexer('.', index_file_name=self.index_file)

    def tearDown(self):
        # Remove the test index file after testing
        if os.path.exists(f"../../file_management/{self.index_file}"):
            os.remove(f"../../file_management/{self.index_file}")

    def test_generate_file_hash(self):
        # Arrange
        test_file_path = 'test_file.txt'
        with open(test_file_path, 'w') as f:
            f.write('test')

        shared_folder = '.'
        file_indexer = FileIndexer(shared_folder)

        # Act
        actual_hash = file_indexer.generate_file_hash(test_file_path)

        # Assert
        expected_hash = '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08'
        self.assertEqual(actual_hash, expected_hash)

        # Clean up
        os.remove(test_file_path)

    def test_index_files(self):
        # Mock the generate_file_hash method
        mock_generate_file_hash = Mock(return_value='mocked_hash')
        self.file_indexer.generate_file_hash = mock_generate_file_hash

        # Act
        self.file_indexer.index_files()

        # Assert
        self.assertTrue(self.file_indexer.file_hashes)

    def test_save_index_to_json(self):
        # Arrange
        self.file_indexer.file_hashes = {
            'hash1': {'name': 'file1.txt', 'path': '/path/to/file1.txt', 'size': 100},
            'hash2': {'name': 'file2.txt', 'path': '/path/to/file2.txt', 'size': 150}
        }

        # Act
        self.file_indexer.save_index_to_json()

        # Assert file
        self.assertTrue(os.path.exists(f"../../file_management/{self.index_file}"))

        # Assert content
        with open(f"../../file_management/{self.index_file}", 'r') as f:
            saved_index = json.load(f)

        expected_index = {
            'hash1': {'name': 'file1.txt', 'path': '/path/to/file1.txt', 'size': 100},
            'hash2': {'name': 'file2.txt', 'path': '/path/to/file2.txt', 'size': 150}
        }
        self.assertEqual(saved_index, expected_index)

    def test_add_index_to_json(self):
        # Mock the generate_file_hash method
        mock_generate_file_hash = Mock(return_value='mocked_hash')
        self.file_indexer.generate_file_hash = mock_generate_file_hash

        # Sample data for testing
        file_path = 'test_file.txt'
        with open(file_path, 'w') as f:
            f.write('test')

        # Act
        self.file_indexer.add_index_to_json(file_path)

        # Assert
        expected_file_hashes = {
            'mocked_hash': {
                'name': 'test_file.txt',
                'path': 'test_file.txt',
                'size': 4
            }
        }
        self.assertEqual(self.file_indexer.file_hashes, expected_file_hashes)

    def test_delete_index(self):
        # File is created on runtime
        # Act
        self.file_indexer.delete_index()

        # Assert
        self.assertFalse(os.path.exists(self.index_file))
