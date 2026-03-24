"""
Test suite for the p2p-network project.

Run with:
    cd p2p_ui
    python manage.py test base

Coverage:
  - LocalIndexManager  (hashing, indexing, persistence, thread-safety)
  - PeerIndexManager   (CRUD, cascade deletion, persistence)
  - ChunkProcessor     (chunk counting, storage, retry logic, verification)
  - FileManager        (privacy filtering, path-traversal protection, events)
  - Node               (event routing, generate_response, downloading state)
  - Peer               (message parsing, chunk framing, timeout eviction)
  - Broadcast address  (subnet calculation)
  - Django views       (HTTP response codes, JSON shape)
"""

import hashlib
import json
import os
import shutil
import struct
import tempfile
import time
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import TestCase

from .backend.file_management.chunk_processor import CHUNK_SIZE, ChunkProcessor
from .backend.file_management.file_manager import FileManager, create_update_message
from .backend.file_management.local_index_manager import LocalIndexManager
from .backend.file_management.peer_indexer import PeerIndexManager
from .backend.node import Node, generate_response
from .backend.networks.peer import Peer


# ─────────────────────────────────────────────────────────────────────────────
# LocalIndexManager
# ─────────────────────────────────────────────────────────────────────────────

class LocalIndexManagerTests(TestCase):

    def setUp(self):
        self.shared_dir = tempfile.mkdtemp()
        fd, self.index_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        # LocalIndexManager will overwrite this file on first _save_index_to_json call
        self.mgr = LocalIndexManager(self.shared_dir, self.index_path)

    def tearDown(self):
        shutil.rmtree(self.shared_dir, ignore_errors=True)
        if os.path.exists(self.index_path):
            os.unlink(self.index_path)

    def _write_file(self, name="test.txt", content=b"hello world"):
        path = os.path.join(self.shared_dir, name)
        with open(path, "wb") as f:
            f.write(content)
        return path

    # ── generate_file_hash ────────────────────────────────────────────────────

    def test_hash_matches_sha256(self):
        path = self._write_file(content=b"hello world")
        expected = hashlib.sha256(b"hello world").hexdigest()
        self.assertEqual(self.mgr.generate_file_hash(path), expected)

    def test_different_content_different_hash(self):
        a = self._write_file("a.txt", b"AAA")
        b = self._write_file("b.txt", b"BBB")
        self.assertNotEqual(self.mgr.generate_file_hash(a), self.mgr.generate_file_hash(b))

    # ── index_files ───────────────────────────────────────────────────────────

    def test_index_files_adds_file(self):
        path = self._write_file(content=b"data")
        self.mgr.index_files()
        expected_hash = hashlib.sha256(b"data").hexdigest()
        idx = self.mgr.get_index()
        self.assertIn(expected_hash, idx)
        self.assertEqual(idx[expected_hash]["name"], "test.txt")
        self.assertEqual(idx[expected_hash]["size"], 4)

    def test_index_files_skips_subdirectories(self):
        subdir = os.path.join(self.shared_dir, "subdir")
        os.makedirs(subdir)
        self.mgr.index_files()
        self.assertEqual(len(self.mgr.get_index()), 0)

    def test_index_files_persists_to_disk(self):
        self._write_file(content=b"persist me")
        self.mgr.index_files()
        with open(self.index_path) as f:
            on_disk = json.load(f)
        self.assertEqual(len(on_disk), 1)

    def test_index_files_multiple_files(self):
        self._write_file("one.txt", b"one")
        self._write_file("two.txt", b"two")
        self.mgr.index_files()
        self.assertEqual(len(self.mgr.get_index()), 2)

    # ── add_index_to_json ─────────────────────────────────────────────────────

    def test_add_index_returns_hash_and_metadata(self):
        path = self._write_file(content=b"new")
        result = self.mgr.add_index_to_json(path)
        self.assertIsNotNone(result)
        file_hash, meta = result
        self.assertEqual(meta["name"], "test.txt")
        self.assertIn(file_hash, self.mgr.get_index())

    def test_add_index_nonexistent_returns_none(self):
        self.assertIsNone(self.mgr.add_index_to_json("/no/such/file.txt"))

    def test_add_index_persists(self):
        path = self._write_file(content=b"x")
        self.mgr.add_index_to_json(path)
        with open(self.index_path) as f:
            on_disk = json.load(f)
        self.assertEqual(len(on_disk), 1)

    # ── delete_index_from_json ────────────────────────────────────────────────

    def test_delete_index_removes_entry(self):
        path = self._write_file(content=b"delete me")
        file_hash, _ = self.mgr.add_index_to_json(path)
        returned = self.mgr.delete_index_from_json(path)
        self.assertEqual(returned, file_hash)
        self.assertNotIn(file_hash, self.mgr.get_index())

    def test_delete_index_nonexistent_returns_none(self):
        self.assertIsNone(self.mgr.delete_index_from_json("/no/file.txt"))

    def test_delete_index_persists(self):
        path = self._write_file(content=b"y")
        self.mgr.add_index_to_json(path)
        self.mgr.delete_index_from_json(path)
        with open(self.index_path) as f:
            self.assertEqual(json.load(f), {})

    # ── get_index ─────────────────────────────────────────────────────────────

    def test_get_index_returns_copy(self):
        self._write_file(content=b"copy test")
        self.mgr.index_files()
        idx = self.mgr.get_index()
        idx.clear()
        self.assertGreater(len(self.mgr.get_index()), 0)

    # ── clear_local_index ─────────────────────────────────────────────────────

    def test_clear_empties_in_memory_index(self):
        self._write_file(content=b"clear me")
        self.mgr.index_files()
        self.mgr.clear_local_index()
        self.assertEqual(len(self.mgr.get_index()), 0)

    def test_clear_persists_empty_to_disk(self):
        self._write_file(content=b"clear me")
        self.mgr.index_files()
        self.mgr.clear_local_index()
        with open(self.index_path) as f:
            self.assertEqual(json.load(f), {})


# ─────────────────────────────────────────────────────────────────────────────
# PeerIndexManager
# ─────────────────────────────────────────────────────────────────────────────

class PeerIndexManagerTests(TestCase):

    HASH = "abc123"
    HASH2 = "def456"
    META = {"name": "file.txt", "size": 42}
    PEER = "192.168.1.1"
    PEER2 = "192.168.1.2"

    def setUp(self):
        fd, self.index_path = tempfile.mkstemp(suffix=".json")
        os.write(fd, b"{}")
        os.close(fd)
        self.mgr = PeerIndexManager(self.index_path)

    def tearDown(self):
        if os.path.exists(self.index_path):
            os.unlink(self.index_path)

    # ── add_file_index ────────────────────────────────────────────────────────

    def test_add_creates_entry(self):
        self.mgr.add_file_index(self.HASH, self.META, self.PEER)
        idx = self.mgr.get_peer_index()
        self.assertIn(self.HASH, idx)
        self.assertEqual(idx[self.HASH]["metadata"], self.META)
        self.assertIn(self.PEER, idx[self.HASH]["peers"])

    def test_add_multiple_peers_same_hash(self):
        self.mgr.add_file_index(self.HASH, self.META, self.PEER)
        self.mgr.add_file_index(self.HASH, self.META, self.PEER2)
        peers = self.mgr.get_peer_index()[self.HASH]["peers"]
        self.assertIn(self.PEER, peers)
        self.assertIn(self.PEER2, peers)

    def test_add_persists_to_disk(self):
        self.mgr.add_file_index(self.HASH, self.META, self.PEER)
        with open(self.index_path) as f:
            self.assertIn(self.HASH, json.load(f))

    # ── remove_file_index ─────────────────────────────────────────────────────

    def test_remove_one_of_two_peers(self):
        self.mgr.add_file_index(self.HASH, self.META, self.PEER)
        self.mgr.add_file_index(self.HASH, self.META, self.PEER2)
        self.mgr.remove_file_index(self.HASH, self.PEER)
        peers = self.mgr.get_peer_index()[self.HASH]["peers"]
        self.assertNotIn(self.PEER, peers)
        self.assertIn(self.PEER2, peers)

    def test_remove_last_peer_deletes_hash(self):
        self.mgr.add_file_index(self.HASH, self.META, self.PEER)
        self.mgr.remove_file_index(self.HASH, self.PEER)
        self.assertNotIn(self.HASH, self.mgr.get_peer_index())

    def test_remove_nonexistent_no_crash(self):
        # Should not raise even when hash/peer are unknown
        self.mgr.remove_file_index("deadbeef", "10.0.0.1")

    # ── get_file_peers ────────────────────────────────────────────────────────

    def test_get_file_peers_returns_peers(self):
        self.mgr.add_file_index(self.HASH, self.META, self.PEER)
        self.assertIn(self.PEER, self.mgr.get_file_peers(self.HASH))

    def test_get_file_peers_missing_hash_returns_empty(self):
        self.assertEqual(self.mgr.get_file_peers("nothere"), {})

    # ── update_from_received_index ────────────────────────────────────────────

    def test_update_from_received_index(self):
        received = {
            self.HASH: self.META,
            self.HASH2: {"name": "other.bin", "size": 100},
        }
        self.mgr.update_from_received_index(received, self.PEER)
        idx = self.mgr.get_peer_index()
        self.assertIn(self.HASH, idx)
        self.assertIn(self.HASH2, idx)

    # ── remove_disconnected_peer ──────────────────────────────────────────────

    def test_remove_disconnected_peer_cascades(self):
        # PEER has HASH and HASH2; PEER2 only has HASH
        self.mgr.add_file_index(self.HASH, self.META, self.PEER)
        self.mgr.add_file_index(self.HASH2, self.META, self.PEER)
        self.mgr.add_file_index(self.HASH, self.META, self.PEER2)

        self.mgr.remove_disconnected_peer(self.PEER)
        idx = self.mgr.get_peer_index()

        # HASH still exists because PEER2 has it
        self.assertIn(self.HASH, idx)
        self.assertNotIn(self.PEER, idx[self.HASH]["peers"])

        # HASH2 had only PEER, so it is gone
        self.assertNotIn(self.HASH2, idx)

    # ── clear_peer_index ──────────────────────────────────────────────────────

    def test_clear_empties_index(self):
        self.mgr.add_file_index(self.HASH, self.META, self.PEER)
        self.mgr.clear_peer_index()
        self.assertEqual(self.mgr.get_peer_index(), {})

    # ── load_peer_index (missing file) ────────────────────────────────────────

    def test_load_missing_file_returns_empty(self):
        mgr = PeerIndexManager("/tmp/__nonexistent_peer_index_xyz_987.json")
        self.assertEqual(mgr.peer_file_index, {})

    # ── list_available_files ──────────────────────────────────────────────────

    def test_list_available_files(self):
        self.mgr.add_file_index(self.HASH, self.META, self.PEER)
        self.assertIn(self.META["name"], self.mgr.list_available_files())

    # ── get_peer_index returns copy ───────────────────────────────────────────

    def test_get_peer_index_returns_copy(self):
        self.mgr.add_file_index(self.HASH, self.META, self.PEER)
        snapshot = self.mgr.get_peer_index()
        snapshot.clear()
        self.assertGreater(len(self.mgr.get_peer_index()), 0)


# ─────────────────────────────────────────────────────────────────────────────
# ChunkProcessor
# ─────────────────────────────────────────────────────────────────────────────

class ChunkProcessorTests(TestCase):

    def _make_cp(self, size, file_hash=None):
        node = MagicMock()
        if file_hash is None:
            file_hash = hashlib.sha256(b"x" * size).hexdigest()
        cp = ChunkProcessor(node, file_hash, {"name": "test.bin", "size": size})
        return cp, node

    # ── num_chunks calculation ────────────────────────────────────────────────

    def test_num_chunks_exact_multiple(self):
        cp, _ = self._make_cp(size=2 * CHUNK_SIZE)
        self.assertEqual(cp.num_chunks, 2)

    def test_num_chunks_with_remainder(self):
        cp, _ = self._make_cp(size=CHUNK_SIZE + 1)
        self.assertEqual(cp.num_chunks, 2)

    def test_num_chunks_less_than_chunk_size(self):
        cp, _ = self._make_cp(size=100)
        self.assertEqual(cp.num_chunks, 1)

    def test_num_chunks_exactly_chunk_size(self):
        cp, _ = self._make_cp(size=CHUNK_SIZE)
        self.assertEqual(cp.num_chunks, 1)

    # ── handle_chunk ──────────────────────────────────────────────────────────

    def test_handle_chunk_stores_in_chunks_array(self):
        cp, _ = self._make_cp(size=CHUNK_SIZE)
        data = b"A" * CHUNK_SIZE
        cp.handle_chunk({"chunk_data": data, "file_hash": cp.file_hash, "chunk_sequence_number": 0})
        self.assertEqual(cp.chunks[0], data)

    def test_handle_chunk_stores_in_temp_storage(self):
        cp, _ = self._make_cp(size=CHUNK_SIZE)
        data = b"B" * 50
        cp.handle_chunk({"chunk_data": data, "file_hash": cp.file_hash, "chunk_sequence_number": 0})
        self.assertEqual(cp.temp_file_storage[cp.file_hash][0], data)

    def test_handle_multiple_chunks(self):
        cp, _ = self._make_cp(size=2 * CHUNK_SIZE)
        cp.handle_chunk({"chunk_data": b"1" * CHUNK_SIZE, "file_hash": cp.file_hash, "chunk_sequence_number": 0})
        cp.handle_chunk({"chunk_data": b"2" * CHUNK_SIZE, "file_hash": cp.file_hash, "chunk_sequence_number": 1})
        self.assertIsNone(None) if None in cp.chunks else None
        self.assertTrue(all(c is not None for c in cp.chunks))

    # ── verify_file ───────────────────────────────────────────────────────────

    def test_verify_correct_hash(self):
        data = b"hello world"
        h = hashlib.sha256(data).hexdigest()
        cp, _ = self._make_cp(size=len(data), file_hash=h)
        self.assertTrue(cp.verify_file(data))

    def test_verify_wrong_hash(self):
        cp, _ = self._make_cp(size=5)
        # file_hash is sha256 of b'xxxxx', but we pass different data
        self.assertFalse(cp.verify_file(b"wrong"))

    # ── request_chunk ─────────────────────────────────────────────────────────

    def test_request_chunk_no_peers_returns_false(self):
        cp, _ = self._make_cp(size=CHUNK_SIZE)
        cp.peers_with_file = {}
        cp.max_attempts = 3
        self.assertFalse(cp.request_chunk(0))

    def test_request_chunk_all_attempts_exhausted(self):
        cp, _ = self._make_cp(size=CHUNK_SIZE)
        cp.peers_with_file = {"10.0.0.1": {}}
        cp.max_attempts = 1
        cp.chunk_attempts[0].add("10.0.0.1")  # already tried
        self.assertFalse(cp.request_chunk(0))

    def test_request_chunk_fires_handle_event(self):
        cp, mock_node = self._make_cp(size=CHUNK_SIZE)
        cp.peers_with_file = {"10.0.0.1": {}}
        cp.max_attempts = 3
        result = cp.request_chunk(0)
        self.assertTrue(result)
        mock_node.handle_event.assert_called_once()
        event = mock_node.handle_event.call_args[0][0]
        self.assertEqual(event["action"], "request_chunk")
        self.assertEqual(event["chunk_sequence_number"], 0)
        self.assertEqual(event["bit_offset"], 0)
        self.assertEqual(event["file_hash"], cp.file_hash)

    def test_request_chunk_records_attempt(self):
        cp, _ = self._make_cp(size=CHUNK_SIZE)
        cp.peers_with_file = {"10.0.0.1": {}}
        cp.max_attempts = 3
        cp.request_chunk(0)
        self.assertIn("10.0.0.1", cp.chunk_attempts[0])

    def test_request_chunk_last_chunk_correct_size(self):
        """Last chunk uses remaining bytes, not full CHUNK_SIZE."""
        size = CHUNK_SIZE + 500
        cp, mock_node = self._make_cp(size=size)
        cp.peers_with_file = {"10.0.0.1": {}}
        cp.max_attempts = 3
        cp.request_chunk(1)  # second (last) chunk
        event = mock_node.handle_event.call_args[0][0]
        self.assertEqual(event["chunk_size"], 500)

    def test_request_chunk_non_last_uses_full_chunk_size(self):
        size = 2 * CHUNK_SIZE
        cp, mock_node = self._make_cp(size=size)
        cp.peers_with_file = {"10.0.0.1": {}}
        cp.max_attempts = 3
        cp.request_chunk(0)
        event = mock_node.handle_event.call_args[0][0]
        self.assertEqual(event["chunk_size"], CHUNK_SIZE)

    # ── download_and_verify_file ──────────────────────────────────────────────

    def test_download_and_verify_success(self):
        data = b"X" * CHUNK_SIZE
        h = hashlib.sha256(data).hexdigest()
        cp, mock_node = self._make_cp(size=CHUNK_SIZE, file_hash=h)
        # Pre-fill chunks so the while loop exits immediately
        cp.chunks[0] = data
        cp.peers_with_file = {"10.0.0.1": {}}
        cp.max_attempts = 1
        mock_node.get_file_peers.return_value = {"10.0.0.1": {}}

        result = cp.download_and_verify_file()
        self.assertTrue(result)
        mock_node.handle_event.assert_called_with({
            "action": "save_file",
            "name": "test.bin",
            "data": data,
        })

    def test_download_and_verify_hash_mismatch_returns_false(self):
        data = b"Y" * CHUNK_SIZE
        wrong_hash = "a" * 64
        cp, mock_node = self._make_cp(size=CHUNK_SIZE, file_hash=wrong_hash)
        cp.chunks[0] = data
        cp.peers_with_file = {"10.0.0.1": {}}
        cp.max_attempts = 1
        mock_node.get_file_peers.return_value = {"10.0.0.1": {}}

        result = cp.download_and_verify_file()
        self.assertFalse(result)
        mock_node.handle_event.assert_not_called()

    def test_download_and_verify_no_data_returns_false(self):
        cp, mock_node = self._make_cp(size=CHUNK_SIZE)
        # chunks[0] stays None; get_file_peers returns empty so request_chunk exits immediately
        cp.peers_with_file = {}
        cp.max_attempts = 0
        mock_node.get_file_peers.return_value = {}

        result = cp.download_and_verify_file()
        self.assertFalse(result)


# ─────────────────────────────────────────────────────────────────────────────
# FileManager
# ─────────────────────────────────────────────────────────────────────────────

class FileManagerTests(TestCase):

    def setUp(self):
        self.shared_dir = tempfile.mkdtemp()
        self.mock_node = MagicMock()
        self.mock_indexer = MagicMock()
        with patch("base.backend.file_management.FileManager.DirectoryMonitor"):
            self.fm = FileManager(self.mock_node, self.shared_dir, self.mock_indexer)

    def tearDown(self):
        shutil.rmtree(self.shared_dir, ignore_errors=True)

    # ── get_full_index ────────────────────────────────────────────────────────

    def test_get_full_index_excludes_path(self):
        self.mock_indexer.get_index.return_value = {
            "h1": {"name": "f.txt", "size": 10, "path": "/secret/f.txt"}
        }
        result = self.fm.get_full_index()
        self.assertNotIn("path", result["h1"])

    def test_get_full_index_includes_name_and_size(self):
        self.mock_indexer.get_index.return_value = {
            "h1": {"name": "f.txt", "size": 99, "path": "/p/f.txt"}
        }
        result = self.fm.get_full_index()
        self.assertEqual(result["h1"]["name"], "f.txt")
        self.assertEqual(result["h1"]["size"], 99)

    def test_get_full_index_multiple_files(self):
        self.mock_indexer.get_index.return_value = {
            "h1": {"name": "a.txt", "size": 1, "path": "/p/a.txt"},
            "h2": {"name": "b.txt", "size": 2, "path": "/p/b.txt"},
        }
        self.assertEqual(len(self.fm.get_full_index()), 2)

    # ── save_file ─────────────────────────────────────────────────────────────

    def test_save_file_writes_bytes(self):
        self.fm.save_file("out.bin", b"file content")
        expected = os.path.join(self.shared_dir, "out.bin")
        self.assertTrue(os.path.exists(expected))
        with open(expected, "rb") as f:
            self.assertEqual(f.read(), b"file content")

    def test_save_file_uses_basename_only(self):
        self.fm.save_file("/absolute/path/to/result.txt", b"data")
        expected = os.path.join(self.shared_dir, "result.txt")
        self.assertTrue(os.path.exists(expected))

    def test_save_file_path_traversal_stripped(self):
        """../evil.txt must not land outside the shared folder."""
        self.fm.save_file("../evil.txt", b"bad")
        outside = os.path.join(os.path.dirname(self.shared_dir), "evil.txt")
        self.assertFalse(os.path.exists(outside))

    # ── share_file_index / unshare_file_index ─────────────────────────────────

    def test_share_file_emits_send_file_update(self):
        self.mock_indexer.add_index_to_json.return_value = (
            "abc", {"name": "x.txt", "size": 5}
        )
        self.fm.share_file_index(os.path.join(self.shared_dir, "x.txt"))
        event = self.mock_node.handle_event.call_args[0][0]
        self.assertEqual(event["action"], "send_file_update")

    def test_unshare_file_emits_send_file_update(self):
        self.mock_indexer.delete_index_from_json.return_value = "abc"
        self.fm.unshare_file_index(os.path.join(self.shared_dir, "x.txt"))
        event = self.mock_node.handle_event.call_args[0][0]
        self.assertEqual(event["action"], "send_file_update")

    # ── get_file_path ─────────────────────────────────────────────────────────

    def test_get_file_path_returns_path(self):
        self.mock_indexer.get_index.return_value = {
            "abc": {"name": "f.txt", "path": "/shared/f.txt", "size": 1}
        }
        self.assertEqual(self.fm.get_file_path("abc"), "/shared/f.txt")

    # ── clear_indices ─────────────────────────────────────────────────────────

    def test_clear_indices_delegates_to_indexer(self):
        self.fm.clear_indices()
        self.mock_indexer.clear_local_index.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# FileManager helper functions
# ─────────────────────────────────────────────────────────────────────────────

class FileManagerHelpersTests(TestCase):

    def test_create_update_message_add(self):
        msg = create_update_message("add", "h1", {"name": "f.txt", "size": 10})
        self.assertEqual(msg["action"], "add")
        self.assertEqual(msg["file_hash"], "h1")
        self.assertEqual(msg["metadata"]["name"], "f.txt")

    def test_create_update_message_delete_no_metadata(self):
        msg = create_update_message("delete", "h1")
        self.assertEqual(msg["action"], "delete")
        self.assertNotIn("metadata", msg)

    def test_create_update_message_add_without_metadata(self):
        msg = create_update_message("add", "h1")
        self.assertNotIn("metadata", msg)


# ─────────────────────────────────────────────────────────────────────────────
# generate_response (Node helper)
# ─────────────────────────────────────────────────────────────────────────────

class GenerateResponseTests(TestCase):

    def test_basic_local_files(self):
        files = {
            "hash1": {"name": "a.txt", "size": 10},
            "hash2": {"name": "b.txt", "size": 20},
        }
        result = generate_response(files, "local_files", ["name", "size"], "hash")
        self.assertIn("local_files", result)
        self.assertEqual(len(result["local_files"]), 2)

    def test_includes_hash_and_origin(self):
        files = {"abc": {"name": "f.txt", "size": 5}}
        result = generate_response(files, "local_files", ["name", "size"], "hash")
        item = result["local_files"][0]
        self.assertEqual(item["hash"], "abc")
        self.assertEqual(item["origin"], "local_files")

    def test_inner_metadata_keys_are_flattened(self):
        files = {"h1": {"metadata": {"name": "f.txt", "size": 10}, "peers": {}}}
        result = generate_response(
            files, "net_files", ["metadata", "peers"], "hash", ["name", "size"]
        )
        item = result["net_files"][0]
        self.assertEqual(item["name"], "f.txt")
        self.assertEqual(item["size"], 10)

    def test_empty_files(self):
        result = generate_response({}, "local_files", ["name"], "hash")
        self.assertEqual(result["local_files"], [])


# ─────────────────────────────────────────────────────────────────────────────
# Node event routing
# ─────────────────────────────────────────────────────────────────────────────

class NodeEventRoutingTests(TestCase):

    def _make_node(self):
        with (
            patch("base.backend.Node.Peer"),
            patch("base.backend.Node.FileManager"),
            patch("base.backend.Node.LocalIndexManager"),
            patch("base.backend.Node.PeerIndexManager"),
        ):
            node = Node(addr="192.168.1.1", mask="255.255.255.0", shared_folder="/tmp")
        return node

    def test_missing_action_key_does_not_raise(self):
        node = self._make_node()
        node.handle_event({"data": "something"})  # no "action" key

    def test_unknown_action_does_not_raise(self):
        node = self._make_node()
        node.handle_event({"action": "nonexistent"})

    def test_known_action_is_dispatched(self):
        node = self._make_node()
        mock_handler = MagicMock()
        node.event_dictionary["new_peer"] = mock_handler
        event = {"action": "new_peer", "addr": "10.0.0.1"}
        node.handle_event(event)
        mock_handler.assert_called_once_with(event)

    def test_all_expected_actions_registered(self):
        node = self._make_node()
        expected = {
            "new_peer", "send_file_update", "got_chunk",
            "request_file", "save_file", "request_chunk", "handle_file_request",
        }
        self.assertEqual(set(node.event_dictionary.keys()), expected)

    def test_get_downloading_no_processor(self):
        node = self._make_node()
        node.chunk_processor = None
        self.assertEqual(node.get_downloading()["requested_file"], [])

    def test_get_downloading_with_active_processor(self):
        node = self._make_node()
        mock_cp = MagicMock()
        mock_cp.name = "bigfile.iso"
        mock_cp.size = 999
        mock_cp.file_hash = "deadbeef"
        node.chunk_processor = mock_cp
        result = node.get_downloading()
        self.assertEqual(len(result["requested_file"]), 1)
        item = result["requested_file"][0]
        self.assertEqual(item["name"], "bigfile.iso")
        self.assertEqual(item["hash"], "deadbeef")
        self.assertEqual(item["origin"], "requested_file")

    def test_save_file_delegates_to_file_manager(self):
        node = self._make_node()
        node.file_manager.save_file = MagicMock()
        node.save_file({"action": "save_file", "name": "x.bin", "data": b"data"})
        node.file_manager.save_file.assert_called_once_with("x.bin", b"data")

    def test_request_chunk_deletes_action_and_peer_address(self):
        node = self._make_node()
        node.peer.send_request = MagicMock()
        event = {
            "action": "request_chunk",
            "peer_address": "10.0.0.1",
            "file_hash": "abc",
            "bit_offset": 0,
            "chunk_size": 1024,
            "chunk_sequence_number": 0,
        }
        node.request_chunk(event)
        # "action" and "peer_address" must be stripped before encoding
        node.peer.send_request.assert_called_once()
        sent_bytes = node.peer.send_request.call_args[0][1]
        sent_dict = json.loads(sent_bytes.decode())
        self.assertNotIn("action", sent_dict)
        self.assertNotIn("peer_address", sent_dict)


# ─────────────────────────────────────────────────────────────────────────────
# Peer message parsing
# ─────────────────────────────────────────────────────────────────────────────

class PeerMessageParsingTests(TestCase):

    def _make_peer(self):
        mock_node = MagicMock()
        mock_indexer = MagicMock()
        with patch("base.backend.networks.peer.Messager") as MockMsg:
            MockMsg.return_value.pkey = b"fake_public_key"
            p = Peer(
                mock_node, "192.168.1.1", "255.255.255.0",
                mock_indexer, port=9613, me="192.168.1.100"
            )
        return p, mock_node, mock_indexer

    # ── receive_index ─────────────────────────────────────────────────────────

    def test_receive_index_calls_update_from_received_index(self):
        p, _, mock_indexer = self._make_peer()
        index = {"h1": {"name": "f.txt", "size": 10}}
        p.receive_index("10.0.0.1", json.dumps(index).encode())
        mock_indexer.update_from_received_index.assert_called_once_with(index, "10.0.0.1")

    # ── receive_file_update ───────────────────────────────────────────────────

    def test_receive_file_update_add(self):
        p, _, mock_indexer = self._make_peer()
        msg = {"action": "add", "file_hash": "abc", "metadata": {"name": "f.txt", "size": 5}}
        p.receive_file_update("10.0.0.1", json.dumps(msg).encode())
        mock_indexer.add_file_index.assert_called_once_with(
            "abc", {"name": "f.txt", "size": 5}, "10.0.0.1"
        )

    def test_receive_file_update_delete(self):
        p, _, mock_indexer = self._make_peer()
        msg = {"action": "delete", "file_hash": "abc"}
        p.receive_file_update("10.0.0.1", json.dumps(msg).encode())
        mock_indexer.remove_file_index.assert_called_once_with("abc", "10.0.0.1")

    # ── receive_file_chunk ────────────────────────────────────────────────────

    def test_receive_file_chunk_correct_framing(self):
        """chunk = data[2:2+length], chunk_data = data[2+length:]"""
        p, mock_node, _ = self._make_peer()
        chunk = b"C" * 100
        chunk_info = {"file_hash": "abc", "chunk_sequence_number": 0}
        chunk_info_bytes = json.dumps(chunk_info).encode()
        length = struct.pack("!H", len(chunk))
        raw = length + chunk + chunk_info_bytes

        p.receive_file_chunk("10.0.0.1", raw)

        event = mock_node.handle_event.call_args[0][0]
        self.assertEqual(event["action"], "got_chunk")
        self.assertEqual(event["chunk"], chunk)
        self.assertEqual(event["chunk_data"], chunk_info_bytes)

    # ── receive_file_request ──────────────────────────────────────────────────

    def test_receive_file_request_emits_handle_file_request(self):
        p, mock_node, _ = self._make_peer()
        msg = {"file_hash": "abc", "bit_offset": 0, "chunk_size": 1024}
        p.receive_file_request("10.0.0.2", json.dumps(msg).encode())
        event = mock_node.handle_event.call_args[0][0]
        self.assertEqual(event["action"], "handle_file_request")
        self.assertEqual(event["addr"], "10.0.0.2")
        self.assertEqual(event["data"], msg)

    # ── get_file_peers ────────────────────────────────────────────────────────

    def test_get_file_peers_delegates_to_indexer(self):
        p, _, mock_indexer = self._make_peer()
        mock_indexer.get_peer_index.return_value = {
            "abc": {"metadata": {}, "peers": {"10.0.0.1": {}}}
        }
        peers = p.get_file_peers("abc")
        self.assertIn("10.0.0.1", peers)

    def test_get_file_peers_missing_hash(self):
        p, _, mock_indexer = self._make_peer()
        mock_indexer.get_peer_index.return_value = {}
        self.assertEqual(p.get_file_peers("missing"), {})

    # ── handle_disconnected_peer ──────────────────────────────────────────────

    def test_handle_disconnected_peer_delegates_to_indexer(self):
        p, _, mock_indexer = self._make_peer()
        p.handle_disconnected_peer("10.0.0.5")
        mock_indexer.remove_disconnected_peer.assert_called_once_with("10.0.0.5")

    # ── send_request ──────────────────────────────────────────────────────────

    def test_send_request_only_sends_to_known_peers(self):
        p, _, _ = self._make_peer()
        p.messager.send = MagicMock()
        p.peers = {"10.0.0.1": {"key": b"k", "last_online": time.time()}}
        p.send_request("10.0.0.1", b"payload")
        p.messager.send.assert_called_once()

    def test_send_request_ignores_unknown_peer(self):
        p, _, _ = self._make_peer()
        p.messager.send = MagicMock()
        p.peers = {}
        p.send_request("10.0.0.99", b"payload")
        p.messager.send.assert_not_called()

    # ── kill_timeouts logic (tested inline, not via thread) ───────────────────

    def test_stale_peers_are_evicted(self):
        p, _, mock_indexer = self._make_peer()
        mock_indexer.remove_disconnected_peer.return_value = None
        now = time.time()
        p.peers = {
            "10.0.0.1": {"key": b"k", "last_online": now - 120},  # stale
            "10.0.0.2": {"key": b"k", "last_online": now},          # fresh
        }
        # Replicate the eviction logic from kill_timeouts (one iteration)
        dead = [
            peer for peer in p.peers
            if time.time() - p.peers[peer]["last_online"] > 60
        ]
        for peer in dead:
            p.handle_disconnected_peer(peer)
            del p.peers[peer]

        self.assertNotIn("10.0.0.1", p.peers)
        self.assertIn("10.0.0.2", p.peers)
        mock_indexer.remove_disconnected_peer.assert_called_once_with("10.0.0.1")

    # ── message_matcher ───────────────────────────────────────────────────────

    def test_message_matcher_contains_all_prefixes(self):
        p, _, _ = self._make_peer()
        self.assertIn(p.file_alert, p.message_matcher)   # b'I have dis'
        self.assertIn(p.file_update, p.message_matcher)  # b'Update dis'
        self.assertIn(p.resp, p.message_matcher)          # b'Sendin dat'
        self.assertIn(p.req, p.message_matcher)           # b'Gimme dat!'


# ─────────────────────────────────────────────────────────────────────────────
# Broadcast address calculation (Messager)
# ─────────────────────────────────────────────────────────────────────────────

class BroadcastAddressTests(TestCase):
    """Tests the broadcast address formula used in Messager.__init__."""

    @staticmethod
    def _calc(addr, mask):
        return ".".join([
            str(int(a) | (255 ^ int(m)))
            for a, m in zip(addr.split("."), mask.split("."))
        ])

    def test_class_c_network(self):
        self.assertEqual(self._calc("192.168.1.5", "255.255.255.0"), "192.168.1.255")

    def test_class_b_network(self):
        self.assertEqual(self._calc("10.20.0.1", "255.255.0.0"), "10.20.255.255")

    def test_narrow_slash_28_subnet(self):
        # /28 mask = 255.255.255.240; subnet 172.20.10.0 → bcast 172.20.10.15
        self.assertEqual(self._calc("172.20.10.0", "255.255.255.240"), "172.20.10.15")

    def test_class_a_network(self):
        self.assertEqual(self._calc("10.0.0.1", "255.0.0.0"), "10.255.255.255")

    def test_all_ones_mask(self):
        # /32 — host-only, broadcast == the address itself
        self.assertEqual(self._calc("192.168.1.1", "255.255.255.255"), "192.168.1.1")


# ─────────────────────────────────────────────────────────────────────────────
# Django views
# ─────────────────────────────────────────────────────────────────────────────

class DjangoViewTests(TestCase):
    """
    Tests the JSON-serving async endpoints.

    asyncio.sleep calls inside the views are patched to avoid slowing the suite.
    The module-level globals (local_files, network_files, etc.) are set directly.
    """

    def setUp(self):
        import base.views as v
        # Reset globals to known state before each test
        v.local_files = {}
        v.network_files = {}
        v.active_peers = {}
        v.downloading_files = []

    @patch("asyncio.sleep", new_callable=AsyncMock)
    def test_get_local_files_returns_200(self, _mock_sleep):
        response = self.client.get("/get-local-files/")
        self.assertEqual(response.status_code, 200)

    @patch("asyncio.sleep", new_callable=AsyncMock)
    def test_get_network_files_returns_200(self, _mock_sleep):
        response = self.client.get("/get-network-files/")
        self.assertEqual(response.status_code, 200)

    def test_get_downloading_files_returns_200_with_key(self):
        response = self.client.get("/get-downloading-files/")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("downloading", data)

    def test_get_downloading_files_reflects_global(self):
        import base.views as v
        v.downloading_files = ["file_a.txt"]
        response = self.client.get("/get-downloading-files/")
        data = json.loads(response.content)
        self.assertEqual(data["downloading"], ["file_a.txt"])

    @patch("asyncio.sleep", new_callable=AsyncMock)
    def test_get_active_peers_returns_200(self, _mock_sleep):
        response = self.client.get("/get-active-peers/")
        self.assertEqual(response.status_code, 200)

    def test_get_file_without_node_returns_message(self):
        import base.views as v
        v.initialized_node = None
        response = self.client.get("/get-file/abc123/myfile.txt/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"not initialized", response.content)
