# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Django web UI (primary interface)
python p2pUI/manage.py runserver

# Run headless node (no UI)
cd p2pUI/base/backend && python main.py

# Docker: build and start n peers
docker build -t peer .
./start.sh <n>          # starts n Docker containers on ports 8001..800n
./stop.sh               # stops all running peer containers
./trm.sh                # removes all peer containers
```

There is no test suite.

## Architecture

The project has two layers: a **Django web UI** (`p2pUI/`) and a **P2P networking backend** (`p2pUI/base/backend/`). The root-level `main.py`, `networks/`, and `file_management/` directories are an older CLI prototype and are not used by the web app.

### Core backend (`p2pUI/base/backend/`)

**`Node`** (`Node.py`) is the central coordinator. It owns all subsystems and routes events through `handle_event(event)` using a string-keyed `event_dictionary`. All inter-component communication goes through this event bus rather than direct calls.

**`Peer`** (`networks/peer.py`) manages network operations across four daemon threads:
- `alert` — UDP broadcast of `Imma here!` + RSA public key every 1s
- `discover_peers` — listens for broadcasts; identifies self by matching own public key
- `get_message` — accepts TCP connections; dispatches 10-byte-prefixed messages to handlers
- `kill_timeouts` — removes peers not seen in >60s

**`Messager`** (`networks/messager.py`) handles raw sockets: UDP broadcast socket bound to the broadcast address, TCP socket bound to the node's own IP. Both use port 9613.

**`FileManager`** (`file_management/FileManager.py`) wraps `LocalIndexManager` and `DirectoryMonitor`. It exposes only `name` and `size` (not `path`) to peers for privacy.

**`ChunkProcessor`** (`file_management/ChunkProcessor.py`) manages in-progress downloads. Files are split into 1024-byte chunks, requested from random peers (with retry across all peers), reassembled, and verified via SHA256. Only one download at a time (guarded by `Node.chunk_processor is None`).

**`LocalIndexManager`** indexes local shared folder files by SHA256 hash → `{name, size, path}`. Persisted as `index.json`.

**`PeerIndexManager`** maintains a map of file_hash → `{metadata, peers[]}`. Updated when peers connect (full index exchange) or when peers send add/delete updates. Persisted as `peer_index.json`.

**`DirectoryMonitor`** (`file_management/Overwatcher.py`) uses `watchdog` to watch the shared folder; triggers `share_file_index`/`unshare_file_index` on changes.

### Django layer (`p2pUI/base/`)

`views.py` initializes `Node` in a background thread on the first request to `/connect/`. Three additional daemon threads poll `Node` every 1s to update module-level globals (`local_files`, `network_files`, `active_peers`). Async views serve these globals as JSON.

**Key URL endpoints:**
- `GET /connect/` — initializes the node and renders the UI
- `GET /get-local-files/` — files in the local shared folder
- `GET /get-network-files/` — files available from peers
- `GET /get-active-peers/` — currently known peers
- `GET /get-file/<hash>/<name>/` — triggers a chunked download from peers

### Network message protocol

Messages are prefixed with a fixed 10-byte identifier:
| Prefix | Meaning |
|--------|---------|
| `I have dis` | Full file index (on new peer connection) |
| `Update dis` | Single file add/delete update |
| `Gimme dat!` | File chunk request |
| `Sendin dat` | File chunk response (2-byte length + chunk + JSON metadata) |
| `Imma here!` | Peer discovery broadcast (followed by RSA public key) |

### Configuration

Before running, the network settings must be hardcoded in `p2pUI/base/views.py` → `initialize_node()`: `local_address`, `mask`, `shared_folder`, `port` (default 9613). The Docker setup mounts `/Users/rert0/Desktop/p2p` as the shared folder (update `start.sh` for your path).
