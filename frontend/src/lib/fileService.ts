/**
 * File Service
 * 
 * Handles file metadata operations.
 * 
 * REPLACES MOCK DATA IN:
 * - FileTransfer.tsx: File selection and metadata
 * - ChunkProgress.tsx: Chunk status tracking
 * 
 * API ENDPOINTS:
 * - GET /api/v1/files/ - List user's files
 * - POST /api/v1/files/ - Create file metadata
 * - GET /api/v1/files/<id>/ - Get file details
 * - DELETE /api/v1/files/<id>/ - Delete file
 * - GET /api/v1/files/<id>/chunks/ - Get file chunks
 * - GET /api/v1/files/<id>/progress/ - Get transfer progress
 */

import api, { API_BASE_URL, getAccessToken, handleApiError } from './api';

// Types
export interface FileOwner {
  id: number;
  username: string;
  email: string;
}

export interface File {
  id: number;
  uuid: string;
  name: string;
  original_name: string;
  size: number;
  size_formatted: string;
  mime_type: string;
  checksum: string | null;
  is_encrypted: boolean;
  encryption_algorithm: string;
  owner: FileOwner;
  uploaded_at: string;
  extension: string;
}

export interface FileListItem {
  id: number;
  uuid: string;
  original_name: string;
  size: number;
  size_formatted: string;
  mime_type: string;
  owner_username: string;
  uploaded_at: string;
}

export interface FileChunk {
  id: number;
  file_id: number;
  chunk_number: number;
  total_chunks: number;
  size: number;
  offset: number;
  checksum: string | null;
  status: 'pending' | 'transferring' | 'completed' | 'failed';
  created_at: string;
  completed_at: string | null;
  progress_percentage: number;
}

export interface FileProgress {
  file_id: number;
  file_name: string;
  total_chunks: number;
  completed_chunks: number;
  failed_chunks: number;
  pending_chunks: number;
  transferring_chunks: number;
  progress_percentage: number;
  status: string;
}

export interface CreateFileData {
  original_name: string;
  size: number;
  mime_type: string;
  checksum?: string;
  is_encrypted?: boolean;
}

export interface FileListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: FileListItem[];
}

const getWebCrypto = () => {
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1' && !window.isSecureContext) {
    alert("Running in insecure context. Switching to fallback crypto.");
  }

  const cryptoObj = window.crypto || (window as any).msCrypto;

  if (!cryptoObj || !cryptoObj.subtle) {
    throw new Error("Web Crypto API not available");
  }

  return cryptoObj;
};

const base64ToBytes = (base64Value: string): Uint8Array => {
  if (!base64Value?.trim()) {
    throw new Error('Base64 missing');
  }

  const cleaned = base64Value.trim().replace(/\s+/g, '').replace(/-/g, '+').replace(/_/g, '/');
  const padded = cleaned.padEnd(Math.ceil(cleaned.length / 4) * 4, '=');
  const decodeBase64 = globalThis.atob;

  if (!decodeBase64) {
    throw new Error('Base64 decoder not available');
  }

  let binary = '';

  try {
    binary = decodeBase64(padded);
  } catch {
    throw new Error('Invalid base64 value');
  }

  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }

  return bytes;
};

const importAesKey = async (keyValue: string): Promise<CryptoKey> => {
  const cryptoObj = getWebCrypto();

  if (!keyValue?.trim()) {
    throw new Error('Encryption key missing');
  }

  const keyBytes = base64ToBytes(keyValue.trim());
  if (!keyBytes || keyBytes.byteLength === 0) {
    throw new Error('Missing key');
  }
  if (keyBytes.length !== 32) {
    throw new Error("Invalid AES-256 key length");
  }

  const cryptoKey = await cryptoObj.subtle.importKey(
    'raw',
    keyBytes as BufferSource,
    { name: 'AES-GCM' },
    false,
    ['decrypt']
  );

  return cryptoKey;
};

const bytesToBase64 = (bytes: Uint8Array): string => {
  const encodeBase64 = globalThis.btoa;

  if (!encodeBase64) {
    throw new Error('Base64 encoder not available');
  }

  let binary = '';
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });

  return encodeBase64(binary);
};

const readJsonErrorMessage = async (response: Response): Promise<string> => {
  const errorContentType = response.headers.get('content-type')?.toLowerCase() ?? '';

  if (errorContentType.includes('application/json')) {
    const errorData = await response.json() as { message?: string; detail?: string };
    return errorData.message || errorData.detail || 'Download failed.';
  }

  const errorText = await response.text();
  return errorText || `Download failed with status ${response.status}.`;
};

const throwDownloadError = async (response: Response, fileId: number): Promise<never> => {
  const responseMessage = await readJsonErrorMessage(response);
  const endpoint = `/api/v1/files/${fileId}/download/`;

  if (response.status === 403) {
    const message = `403 Forbidden while downloading from ${endpoint}. Auth/session issue. ${responseMessage}`;
    console.error(message);
    throw new Error(message);
  }

  if (response.status === 404) {
    const message = `404 Not Found while downloading from ${endpoint}. Wrong fileId or no encrypted content. ${responseMessage}`;
    console.error(message);
    throw new Error(message);
  }

  const message = `Download failed with ${response.status} from ${endpoint}. ${responseMessage}`;
  console.error(message);
  throw new Error(message);
};

// File service functions
export const fileService = {
  /**
   * Get all files owned by current user
   * 
   * @example
   * const files = await fileService.getFiles();
   */
  async getFiles(search?: string): Promise<FileListItem[]> {
    try {
      const params = new URLSearchParams();
      if (search) {
        params.append('search', search);
      }
      
      const response = await api.get<FileListResponse>(`/files/?${params.toString()}`);
      return response.data.results;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Create file metadata record
   * 
   * Call this before starting a P2P transfer to register the file.
   * 
   * REPLACES: Direct file handling in FileTransfer.tsx
   * 
   * @example
   * const browserFile = event.target.files[0];
   * const fileRecord = await fileService.createFile({
   *   original_name: browserFile.name,
   *   size: browserFile.size,
   *   mime_type: browserFile.type
   * });
   */
  async createFile(data: CreateFileData): Promise<File> {
    try {
      const response = await api.post<File>('/files/', data);
      return response.data;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Upload an encrypted file blob to backend storage before creating a transfer.
   * Returns the persisted fileId that must be attached to the transfer record.
   */
  async uploadEncryptedFile(params: {
    encryptedBlob: Blob;
    token: string;
    originalFilename: string;
  }): Promise<number> {
    const { encryptedBlob, token, originalFilename } = params;

    console.log('Uploading encrypted file...');

    if (!originalFilename?.trim()) {
      throw new Error('Original filename missing');
    }

    const formData = new FormData();
    formData.append('file', encryptedBlob, `${originalFilename}.enc`);

    const response = await fetch(`${API_BASE_URL}/files/upload/`, {
      method: 'POST',
      body: formData,
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const errorMessage = await readJsonErrorMessage(response);
      console.error('Encrypted file upload failed:', response.status, errorMessage);
      throw new Error(`Encrypted file upload failed with ${response.status}: ${errorMessage}`);
    }

    const data = await response.json() as { id?: number; fileId?: number };
    const fileId = data.id ?? data.fileId;

    if (!fileId) {
      throw new Error('Encrypted file upload succeeded but no fileId was returned.');
    }

    console.log('fileId:', fileId);
    return fileId;
  },

  /**
   * Get file details by ID
   */
  async getFileById(id: number): Promise<File> {
    try {
      const response = await api.get<File>(`/files/${id}/`);
      return response.data;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Get file by UUID (for sharing)
   */
  async getFileByUUID(uuid: string): Promise<File> {
    try {
      const response = await api.get<File>(`/files/uuid/${uuid}/`);
      return response.data;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Delete file
   */
  async deleteFile(id: number): Promise<void> {
    try {
      await api.delete(`/files/${id}/`);
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Get file chunks
   * 
   * REPLACES: Mock chunk data in ChunkProgress.tsx
   */
  async getFileChunks(fileId: number): Promise<FileChunk[]> {
    try {
      const response = await api.get<{ results: FileChunk[] }>(`/files/${fileId}/chunks/`);
      return response.data.results;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Create file chunk record
   */
  async createChunk(fileId: number, data: {
    chunk_number: number;
    total_chunks: number;
    size: number;
    offset: number;
    checksum?: string;
  }): Promise<FileChunk> {
    try {
      const response = await api.post<FileChunk>(`/files/${fileId}/chunks/`, data);
      return response.data;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Update chunk status
   */
  async updateChunkStatus(fileId: number, chunkId: number, status: string): Promise<FileChunk> {
    try {
      const response = await api.patch<FileChunk>(`/files/${fileId}/chunks/${chunkId}/`, { status });
      return response.data;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Get file transfer progress
   * 
   * REPLACES: Mock progress in ChunkProgress.tsx
   */
  async getFileProgress(fileId: number): Promise<FileProgress> {
    try {
      const response = await api.get<FileProgress>(`/files/${fileId}/progress/`);
      return response.data;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Securely download encrypted bytes, decrypt them on the client,
   * and force-save the original plaintext filename.
   */
  async downloadAndDecryptFile(params: {
    fileId: number;
    fileName: string;
    base64Key: string;
    base64IV: string;
    mimeType?: string;
  }): Promise<boolean> {
    const { fileId, fileName, base64Key, base64IV, mimeType = 'application/pdf' } = params;

    if (!fileId || !Number.isFinite(fileId) || fileId <= 0) {
      throw new Error('fileId missing');
    }

    if (!fileName?.trim()) {
      throw new Error('fileName missing');
    }

    if (!base64Key?.trim()) {
      throw new Error('key missing');
    }

    if (!base64IV?.trim()) {
      throw new Error('IV missing');
    }

    console.log('Starting download & decrypt...');
    console.log('fileId:', fileId);

    const accessToken = getAccessToken();
    if (!accessToken) {
      throw new Error('You must be logged in to download files.');
    }

    const response = await fetch(`${API_BASE_URL}/files/${fileId}/download/`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      await throwDownloadError(response, fileId);
    }

    const encryptedBuffer = await response.arrayBuffer();
    if (!encryptedBuffer || encryptedBuffer.byteLength === 0) {
      throw new Error('Missing data');
    }

    const cryptoObj = getWebCrypto();
    const keyBytes = base64ToBytes(base64Key);
    if (!keyBytes || keyBytes.byteLength === 0) {
      throw new Error('Missing key');
    }

    const ivBytes = base64ToBytes(base64IV);
    if (!ivBytes || ivBytes.byteLength === 0) {
      throw new Error('Missing IV');
    }
    if (ivBytes.length !== 12) {
      throw new Error('Invalid IV length');
    }

    const cryptoKey = await importAesKey(base64Key);
    const decrypted = await cryptoObj.subtle.decrypt(
      { name: 'AES-GCM', iv: ivBytes as BufferSource },
      cryptoKey,
      encryptedBuffer
    );

    const blob = new Blob([decrypted], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName || 'file.pdf';
    a.click();
    URL.revokeObjectURL(url);

    return true;
  },

  bytesToBase64,
};

export default fileService;
