"""
File transfer implementation for LAN Communication Application.

Handles chunked file upload/download with integrity verification and progress tracking.
"""

import os
import hashlib
import uuid
import threading
import time
from typing import Dict, Optional, Callable, Set
from dataclasses import dataclass
from pathlib import Path
from utils.logger import setup_logger
from utils.config import config, TEMP_FILES_DIR

logger = setup_logger(__name__)

@dataclass
class FileTransferInfo:
    """Information about a file transfer."""
    file_id: str
    filename: str
    file_size: int
    chunk_size: int = 65536  # 64KB chunks
    total_chunks: int = 0
    uploaded_chunks: Set[int] = None
    checksum: str = ""  # SHA-256
    uploader: str = ""
    created_at: float = 0.0
    
    def __post_init__(self):
        if self.uploaded_chunks is None:
            self.uploaded_chunks = set()
        if self.total_chunks == 0:
            self.total_chunks = (self.file_size + self.chunk_size - 1) // self.chunk_size
        if self.created_at == 0.0:
            self.created_at = time.time()

class FileTransferManager:
    """
    Manages file uploads and downloads with chunked transfer and integrity verification.
    """
    
    def __init__(self, client=None):
        """Initialize file transfer manager."""
        self.client = client
        
        # Active transfers
        self.active_uploads: Dict[str, FileTransferInfo] = {}
        self.active_downloads: Dict[str, FileTransferInfo] = {}
        self.transfers_lock = threading.Lock()
        
        # Progress callbacks
        self.upload_progress_callbacks: Dict[str, Callable] = {}
        self.download_progress_callbacks: Dict[str, Callable] = {}
        
        # Retry tracking
        self.chunk_retry_counts: Dict[str, Dict[int, int]] = {}  # file_id -> {chunk_index: retry_count}
        self.max_chunk_retries = 3
        self.retry_delay = 1.0  # seconds
        
        # Network error tracking
        self.transfer_errors: Dict[str, int] = {}  # file_id -> error_count
        self.max_transfer_errors = 10
        
        # Ensure temp directory exists
        TEMP_FILES_DIR.mkdir(exist_ok=True)
        
        logger.info("FileTransferManager initialized")
    
    def upload_file(self, file_path: str, mode: str = "broadcast", targets: list = None) -> Optional[str]:
        """
        Start file upload.
        
        Args:
            file_path: Path to file to upload
            mode: Communication mode (broadcast, multicast, unicast)
            targets: Target users for multicast/unicast
            
        Returns:
            File ID if upload started successfully, None otherwise
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return None
            
            if not file_path.is_file():
                logger.error(f"Path is not a file: {file_path}")
                return None
            
            # Generate file ID
            file_id = str(uuid.uuid4())
            
            # Get file info
            file_size = file_path.stat().st_size
            filename = file_path.name
            
            # Calculate checksum
            logger.info(f"Calculating checksum for {filename}...")
            checksum = self._calculate_file_checksum(file_path)
            
            # Create transfer info
            transfer_info = FileTransferInfo(
                file_id=file_id,
                filename=filename,
                file_size=file_size,
                checksum=checksum,
                uploader=self.client.username if self.client else "unknown"
            )
            
            with self.transfers_lock:
                self.active_uploads[file_id] = transfer_info
            
            # Start upload in background thread
            upload_thread = threading.Thread(
                target=self._upload_file_chunks,
                args=(file_path, transfer_info, mode, targets or []),
                daemon=True
            )
            upload_thread.start()
            
            logger.info(f"Started upload for {filename} (ID: {file_id})")
            return file_id
            
        except Exception as e:
            logger.error(f"Failed to start file upload: {e}")
            return None
    
    def _upload_file_chunks(self, file_path: Path, transfer_info: FileTransferInfo, mode: str, targets: list):
        """Upload file in chunks with retry logic and network error recovery."""
        try:
            # Initialize retry tracking for this file
            with self.transfers_lock:
                self.chunk_retry_counts[transfer_info.file_id] = {}
                self.transfer_errors[transfer_info.file_id] = 0
            
            # First, send file offer message
            if self.client:
                self.client.send_file_offer(
                    transfer_info.file_id,
                    transfer_info.filename,
                    transfer_info.file_size,
                    mode,
                    targets
                )
            
            # Read and send file chunks with retry logic
            with open(file_path, 'rb') as f:
                chunk_index = 0
                
                while chunk_index < transfer_info.total_chunks:
                    # Check if we should skip already uploaded chunks (for resume)
                    if chunk_index in transfer_info.uploaded_chunks:
                        f.seek((chunk_index + 1) * transfer_info.chunk_size)
                        chunk_index += 1
                        continue
                    
                    # Read chunk
                    f.seek(chunk_index * transfer_info.chunk_size)
                    chunk_data = f.read(transfer_info.chunk_size)
                    if not chunk_data:
                        break
                    
                    # Attempt to send chunk with retry logic
                    success = self._send_chunk_with_retry(transfer_info, chunk_index, chunk_data)
                    
                    if success:
                        # Update progress
                        with self.transfers_lock:
                            transfer_info.uploaded_chunks.add(chunk_index)
                        
                        # Call progress callback
                        if transfer_info.file_id in self.upload_progress_callbacks:
                            progress = len(transfer_info.uploaded_chunks) / transfer_info.total_chunks
                            self.upload_progress_callbacks[transfer_info.file_id](progress)
                        
                        chunk_index += 1
                    else:
                        # Check if we should abort the transfer
                        with self.transfers_lock:
                            error_count = self.transfer_errors.get(transfer_info.file_id, 0)
                            if error_count >= self.max_transfer_errors:
                                logger.error(f"Upload aborted due to too many errors: {transfer_info.filename}")
                                self._report_transfer_error(transfer_info.file_id, "Upload failed due to network errors")
                                return
                        
                        # Wait before retrying the same chunk
                        time.sleep(self.retry_delay)
                    
                    # Small delay to prevent overwhelming the network
                    time.sleep(0.01)
            
            # Send completion message
            if self.client:
                completion_message = {
                    "type": "file_complete",
                    "file_id": transfer_info.file_id,
                    "checksum": transfer_info.checksum
                }
                self.client._send_tcp_message(completion_message)
                logger.info(f"File upload completed: {transfer_info.filename}")
            
            # Store transfer state for potential resume
            self._save_transfer_state(transfer_info.file_id, transfer_info)
            
            # Clean up
            with self.transfers_lock:
                if transfer_info.file_id in self.active_uploads:
                    del self.active_uploads[transfer_info.file_id]
                if transfer_info.file_id in self.upload_progress_callbacks:
                    del self.upload_progress_callbacks[transfer_info.file_id]
                if transfer_info.file_id in self.chunk_retry_counts:
                    del self.chunk_retry_counts[transfer_info.file_id]
                if transfer_info.file_id in self.transfer_errors:
                    del self.transfer_errors[transfer_info.file_id]
                    
        except Exception as e:
            logger.error(f"File upload error: {e}")
            self._report_transfer_error(transfer_info.file_id, f"Upload error: {str(e)}")
            # Clean up on error
            with self.transfers_lock:
                if transfer_info.file_id in self.active_uploads:
                    del self.active_uploads[transfer_info.file_id]
    
    def download_file(self, file_id: str, save_path: str) -> bool:
        """
        Start file download.
        
        Args:
            file_id: ID of file to download
            save_path: Path where to save the file
            
        Returns:
            True if download started successfully, False otherwise
        """
        try:
            save_path = Path(save_path)
            
            # Check if we have space
            if not self._check_disk_space(save_path.parent, 0):  # We don't know size yet
                logger.error("Insufficient disk space")
                return False
            
            # Create download info
            download_info = FileTransferInfo(
                file_id=file_id,
                filename=save_path.name,
                file_size=0,  # Will be updated when we receive chunks
                uploader="unknown"
            )
            
            with self.transfers_lock:
                self.active_downloads[file_id] = download_info
            
            # Send download request
            if self.client:
                request_message = {
                    "type": "file_request",
                    "file_id": file_id,
                    "from_user": self.client.username
                }
                self.client._send_tcp_message(request_message)
                logger.info(f"Requesting download for file ID: {file_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start file download: {e}")
            return False
    
    def handle_download_chunk(self, file_id: str, chunk_index: int, chunk_data: bytes):
        """Handle received download chunk."""
        try:
            with self.transfers_lock:
                if file_id not in self.active_downloads:
                    logger.warning(f"Received chunk for unknown download: {file_id}")
                    return
                
                download_info = self.active_downloads[file_id]
                
                # Store chunk data (we'll assemble later)
                if not hasattr(download_info, 'chunks'):
                    download_info.chunks = {}
                
                download_info.chunks[chunk_index] = chunk_data
                download_info.uploaded_chunks.add(chunk_index)
                
                # Update progress callback
                if file_id in self.download_progress_callbacks:
                    if download_info.total_chunks > 0:
                        progress = len(download_info.uploaded_chunks) / download_info.total_chunks
                        self.download_progress_callbacks[file_id](progress)
                
                logger.debug(f"Received download chunk {chunk_index} for {file_id}")
                
        except Exception as e:
            logger.error(f"Error handling download chunk: {e}")
    
    def handle_download_complete(self, file_id: str):
        """Handle download completion."""
        try:
            with self.transfers_lock:
                if file_id not in self.active_downloads:
                    logger.warning(f"Received completion for unknown download: {file_id}")
                    return
                
                download_info = self.active_downloads[file_id]
                
                # Assemble file from chunks
                if hasattr(download_info, 'chunks'):
                    # Create download file path
                    download_path = Path.cwd() / f"download_{download_info.filename}"
                    
                    # Write chunks to file
                    with open(download_path, 'wb') as f:
                        for chunk_index in sorted(download_info.chunks.keys()):
                            f.write(download_info.chunks[chunk_index])
                    
                    logger.info(f"Download completed: {download_path}")
                    
                    # Clean up
                    del self.active_downloads[file_id]
                    if file_id in self.download_progress_callbacks:
                        # Call final progress update
                        self.download_progress_callbacks[file_id](1.0)
                        del self.download_progress_callbacks[file_id]
                
        except Exception as e:
            logger.error(f"Error handling download completion: {e}")
    
    def get_transfer_progress(self, file_id: str) -> float:
        """
        Get transfer progress for a file.
        
        Args:
            file_id: File ID
            
        Returns:
            Progress as float between 0.0 and 1.0
        """
        with self.transfers_lock:
            # Check uploads
            if file_id in self.active_uploads:
                transfer_info = self.active_uploads[file_id]
                return len(transfer_info.uploaded_chunks) / transfer_info.total_chunks
            
            # Check downloads
            if file_id in self.active_downloads:
                transfer_info = self.active_downloads[file_id]
                return len(transfer_info.uploaded_chunks) / transfer_info.total_chunks
        
        return 0.0
    
    def cancel_transfer(self, file_id: str):
        """Cancel a file transfer."""
        with self.transfers_lock:
            if file_id in self.active_uploads:
                del self.active_uploads[file_id]
                logger.info(f"Cancelled upload: {file_id}")
            
            if file_id in self.active_downloads:
                del self.active_downloads[file_id]
                logger.info(f"Cancelled download: {file_id}")
            
            # Clean up callbacks
            if file_id in self.upload_progress_callbacks:
                del self.upload_progress_callbacks[file_id]
            if file_id in self.download_progress_callbacks:
                del self.download_progress_callbacks[file_id]
    
    def set_upload_progress_callback(self, file_id: str, callback: Callable[[float], None]):
        """Set progress callback for upload."""
        self.upload_progress_callbacks[file_id] = callback
    
    def set_download_progress_callback(self, file_id: str, callback: Callable[[float], None]):
        """Set progress callback for download."""
        self.download_progress_callbacks[file_id] = callback
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file."""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            # Read file in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    def _check_disk_space(self, directory: Path, required_bytes: int) -> bool:
        """Check if there's enough disk space."""
        try:
            stat = os.statvfs(directory)
            available_bytes = stat.f_bavail * stat.f_frsize
            return available_bytes >= required_bytes
        except (OSError, AttributeError):
            # On Windows, statvfs might not be available
            try:
                import shutil
                _, _, free_bytes = shutil.disk_usage(directory)
                return free_bytes >= required_bytes
            except Exception:
                # If we can't check, assume we have space
                logger.warning("Could not check disk space")
                return True
    
    def get_active_uploads(self) -> Dict[str, FileTransferInfo]:
        """Get dictionary of active uploads."""
        with self.transfers_lock:
            return self.active_uploads.copy()
    
    def get_active_downloads(self) -> Dict[str, FileTransferInfo]:
        """Get dictionary of active downloads."""
        with self.transfers_lock:
            return self.active_downloads.copy()
    
    def _send_chunk_with_retry(self, transfer_info: FileTransferInfo, chunk_index: int, chunk_data: bytes) -> bool:
        """
        Send a file chunk with retry logic.
        
        Args:
            transfer_info: Transfer information
            chunk_index: Index of the chunk
            chunk_data: Chunk data to send
            
        Returns:
            True if chunk was sent successfully, False otherwise
        """
        file_id = transfer_info.file_id
        
        # Get current retry count for this chunk
        with self.transfers_lock:
            if file_id not in self.chunk_retry_counts:
                self.chunk_retry_counts[file_id] = {}
            retry_count = self.chunk_retry_counts[file_id].get(chunk_index, 0)
        
        if retry_count >= self.max_chunk_retries:
            logger.error(f"Chunk {chunk_index} failed after {retry_count} retries")
            return False
        
        try:
            # Send chunk via TCP control channel
            if self.client:
                chunk_message = {
                    "type": "file_chunk",
                    "file_id": file_id,
                    "chunk_index": chunk_index,
                    "total_chunks": transfer_info.total_chunks,
                    "data": chunk_data.hex(),  # Convert to hex string for JSON
                    "checksum": transfer_info.checksum,
                    "retry_count": retry_count
                }
                
                self.client._send_tcp_message(chunk_message)
                logger.debug(f"Sent chunk {chunk_index}/{transfer_info.total_chunks} for {transfer_info.filename} (retry {retry_count})")
                return True
            
        except Exception as e:
            logger.warning(f"Failed to send chunk {chunk_index} (attempt {retry_count + 1}): {e}")
            
            # Increment retry count and error count
            with self.transfers_lock:
                self.chunk_retry_counts[file_id][chunk_index] = retry_count + 1
                self.transfer_errors[file_id] = self.transfer_errors.get(file_id, 0) + 1
            
            return False
        
        return False
    
    def _save_transfer_state(self, file_id: str, transfer_info: FileTransferInfo):
        """Save transfer state for resume capability."""
        try:
            if hasattr(self.client, 'session_state'):
                # Save upload state
                if file_id in self.active_uploads:
                    if 'active_uploads' not in self.client.session_state:
                        self.client.session_state['active_uploads'] = {}
                    
                    self.client.session_state['active_uploads'][file_id] = {
                        'filename': transfer_info.filename,
                        'file_size': transfer_info.file_size,
                        'uploaded_chunks': list(transfer_info.uploaded_chunks),
                        'total_chunks': transfer_info.total_chunks,
                        'checksum': transfer_info.checksum,
                        'uploader': transfer_info.uploader
                    }
                
                # Save download state
                if file_id in self.active_downloads:
                    if 'active_downloads' not in self.client.session_state:
                        self.client.session_state['active_downloads'] = {}
                    
                    self.client.session_state['active_downloads'][file_id] = {
                        'filename': transfer_info.filename,
                        'file_size': transfer_info.file_size,
                        'uploaded_chunks': list(transfer_info.uploaded_chunks),
                        'total_chunks': transfer_info.total_chunks,
                        'checksum': transfer_info.checksum
                    }
                    
        except Exception as e:
            logger.error(f"Error saving transfer state: {e}")
    
    def _report_transfer_error(self, file_id: str, error_message: str):
        """Report transfer error to error manager."""
        try:
            from utils.error_manager import error_manager, ErrorCategory, ErrorSeverity
            
            error_manager.report_error(
                ErrorCategory.FILE_TRANSFER,
                'transfer_failed',
                ErrorSeverity.ERROR,
                'file_transfer',
                error_message,
                {'file_id': file_id}
            )
        except Exception as e:
            logger.error(f"Error reporting transfer error: {e}")
    
    def resume_upload(self, file_id: str, transfer_state: dict) -> bool:
        """
        Resume an interrupted upload.
        
        Args:
            file_id: File ID to resume
            transfer_state: Saved transfer state
            
        Returns:
            True if resume was initiated successfully
        """
        try:
            # Recreate transfer info from saved state
            transfer_info = FileTransferInfo(
                file_id=file_id,
                filename=transfer_state['filename'],
                file_size=transfer_state['file_size'],
                total_chunks=transfer_state['total_chunks'],
                checksum=transfer_state['checksum'],
                uploader=transfer_state['uploader']
            )
            
            # Restore uploaded chunks
            transfer_info.uploaded_chunks = set(transfer_state['uploaded_chunks'])
            
            with self.transfers_lock:
                self.active_uploads[file_id] = transfer_info
            
            logger.info(f"Resuming upload: {transfer_info.filename} ({len(transfer_info.uploaded_chunks)}/{transfer_info.total_chunks} chunks completed)")
            
            # Find the original file path (this is a limitation - we need to ask user)
            # For now, log that manual intervention is needed
            logger.warning(f"Upload resume requires original file path for {transfer_info.filename}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error resuming upload: {e}")
            return False
    
    def resume_download(self, file_id: str, transfer_state: dict) -> bool:
        """
        Resume an interrupted download.
        
        Args:
            file_id: File ID to resume
            transfer_state: Saved transfer state
            
        Returns:
            True if resume was initiated successfully
        """
        try:
            # Recreate transfer info from saved state
            transfer_info = FileTransferInfo(
                file_id=file_id,
                filename=transfer_state['filename'],
                file_size=transfer_state['file_size'],
                total_chunks=transfer_state['total_chunks'],
                checksum=transfer_state.get('checksum', '')
            )
            
            # Restore downloaded chunks
            transfer_info.uploaded_chunks = set(transfer_state['uploaded_chunks'])
            
            with self.transfers_lock:
                self.active_downloads[file_id] = transfer_info
            
            logger.info(f"Resuming download: {transfer_info.filename} ({len(transfer_info.uploaded_chunks)}/{transfer_info.total_chunks} chunks completed)")
            
            # Request remaining chunks from server
            if self.client:
                resume_request = {
                    "type": "file_resume_request",
                    "file_id": file_id,
                    "completed_chunks": list(transfer_info.uploaded_chunks),
                    "from_user": self.client.username
                }
                self.client._send_tcp_message(resume_request)
            
            return True
            
        except Exception as e:
            logger.error(f"Error resuming download: {e}")
            return False


# ============================================================================
# Server-side File Storage Manager
# ============================================================================

class ServerFileManager:
    """
    Server-side file storage and management.
    
    Handles file chunk reception, assembly, and storage.
    """
    
    def __init__(self):
        """Initialize server file manager."""
        self.stored_files: Dict[str, FileTransferInfo] = {}
        self.file_chunks: Dict[str, Dict[int, bytes]] = {}  # file_id -> {chunk_index: data}
        self.files_lock = threading.Lock()
        
        # Ensure temp directory exists
        TEMP_FILES_DIR.mkdir(exist_ok=True)
        
        logger.info("ServerFileManager initialized")
    
    def handle_file_offer(self, file_id: str, filename: str, file_size: int, checksum: str, uploader: str):
        """Handle file offer from client."""
        transfer_info = FileTransferInfo(
            file_id=file_id,
            filename=filename,
            file_size=file_size,
            checksum=checksum,
            uploader=uploader
        )
        
        with self.files_lock:
            self.stored_files[file_id] = transfer_info
            self.file_chunks[file_id] = {}
        
        logger.info(f"Received file offer: {filename} from {uploader}")
    
    def handle_file_chunk(self, file_id: str, chunk_index: int, chunk_data: bytes) -> bool:
        """
        Handle received file chunk.
        
        Returns:
            True if chunk was processed successfully, False otherwise
        """
        try:
            with self.files_lock:
                if file_id not in self.file_chunks:
                    logger.warning(f"Received chunk for unknown file: {file_id}")
                    return False
                
                # Store chunk
                self.file_chunks[file_id][chunk_index] = chunk_data
                
                # Check if file is complete
                transfer_info = self.stored_files[file_id]
                received_chunks = len(self.file_chunks[file_id])
                
                if received_chunks == transfer_info.total_chunks:
                    # File is complete, assemble it
                    self._assemble_file(file_id)
                    return True
            
            logger.debug(f"Received chunk {chunk_index} for file {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling file chunk: {e}")
            return False
    
    def _assemble_file(self, file_id: str):
        """Assemble file from chunks and verify integrity."""
        try:
            transfer_info = self.stored_files[file_id]
            file_path = TEMP_FILES_DIR / f"{file_id}_{transfer_info.filename}"
            
            # Assemble file from chunks
            with open(file_path, 'wb') as f:
                for chunk_index in range(transfer_info.total_chunks):
                    if chunk_index in self.file_chunks[file_id]:
                        f.write(self.file_chunks[file_id][chunk_index])
                    else:
                        logger.error(f"Missing chunk {chunk_index} for file {file_id}")
                        return False
            
            # Verify checksum
            calculated_checksum = self._calculate_file_checksum(file_path)
            if calculated_checksum != transfer_info.checksum:
                logger.error(f"Checksum mismatch for file {file_id}")
                file_path.unlink()  # Delete corrupted file
                return False
            
            logger.info(f"File assembled successfully: {transfer_info.filename}")
            
            # Clean up chunks from memory
            del self.file_chunks[file_id]
            
            return True
            
        except Exception as e:
            logger.error(f"Error assembling file: {e}")
            return False
    
    def get_file_path(self, file_id: str) -> Optional[Path]:
        """Get path to assembled file."""
        if file_id in self.stored_files:
            transfer_info = self.stored_files[file_id]
            file_path = TEMP_FILES_DIR / f"{file_id}_{transfer_info.filename}"
            if file_path.exists():
                return file_path
        return None
    
    def get_available_files(self) -> Dict[str, FileTransferInfo]:
        """Get dictionary of available files."""
        with self.files_lock:
            return {
                file_id: info for file_id, info in self.stored_files.items()
                if self.get_file_path(file_id) is not None
            }
    
    def cleanup_session_files(self):
        """Clean up temporary files for ended session."""
        try:
            with self.files_lock:
                for file_id in list(self.stored_files.keys()):
                    file_path = self.get_file_path(file_id)
                    if file_path and file_path.exists():
                        file_path.unlink()
                        logger.info(f"Cleaned up file: {file_path}")
                
                self.stored_files.clear()
                self.file_chunks.clear()
                
        except Exception as e:
            logger.error(f"Error cleaning up session files: {e}")
    
