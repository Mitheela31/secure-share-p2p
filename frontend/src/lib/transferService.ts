/**
 * Transfer Service
 * 
 * Handles file transfer operations between users.
 * 
 * REPLACES MOCK DATA IN:
 * - TransferHistory.tsx: Mock transfer records
 * - SenderDashboard.tsx: Sent transfers
 * - ReceiverDashboard.tsx: Incoming requests and received transfers
 * 
 * API ENDPOINTS:
 * - GET /api/v1/transfers/ - List all transfers
 * - POST /api/v1/transfers/ - Create new transfer
 * - GET /api/v1/transfers/<id>/ - Get transfer details
 * - PATCH /api/v1/transfers/<id>/ - Update transfer
 * - POST /api/v1/transfers/<id>/action/ - Perform action (accept/reject/cancel)
 * - GET /api/v1/transfers/sent/ - List sent transfers
 * - GET /api/v1/transfers/received/ - List received transfers
 * - GET /api/v1/transfers/pending/ - List pending incoming transfers
 * - GET /api/v1/transfers/active/ - List active transfers
 * - GET /api/v1/transfers/stats/ - Get transfer statistics
 */

import api, { handleApiError } from './api';

// Types
export interface TransferUser {
  id: number;
  username: string;
  email: string;
  is_online: boolean;
}

export interface TransferFile {
  id: number;
  uuid: string;
  original_name: string;
  size: number;
  size_formatted: string;
  mime_type: string;
  iv?: string | null;
}

export type TransferStatus = 
  | 'pending'
  | 'accepted'
  | 'rejected'
  | 'connecting'
  | 'key_exchange'
  | 'transferring'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface Transfer {
  id: number;
  uuid: string;
  sender: TransferUser;
  receiver: TransferUser;
  file: TransferFile;
  status: TransferStatus;
  status_display: string;
  progress: number;
  bytes_transferred: number;
  transfer_speed: number;
  speed_formatted: string;
  error_message: string | null;
  retry_count: number;
  connection_id: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  duration: number | null;
  file_name?: string | null;
  aes_key?: string | null;
  iv?: string | null;
  file_iv?: string | null;
  encrypted_aes_key?: string | null;
  key_iv?: string | null;
}

export interface TransferListItem {
  id: number;
  uuid: string;
  sender_username: string;
  receiver_username: string;
  file_name: string;
  file_size_formatted: string;
  status: TransferStatus;
  status_display: string;
  progress: number;
  created_at: string;
  completed_at: string | null;
}

export interface TransferDownloadContext {
  fileId: number;
  fileName: string;
  aesKey: string;
  iv: string;
  mimeType: string;
}

export interface TransferLog {
  id: number;
  transfer_id: number;
  event: string;
  event_display: string;
  old_status: string | null;
  new_status: string | null;
  message: string | null;
  metadata: Record<string, unknown> | null;
  timestamp: string;
}

export interface TransferStats {
  total_sent: number;
  total_received: number;
  completed: number;
  failed: number;
  pending: number;
  active: number;
  total_bytes_sent: number;
  total_bytes_received: number;
}

export interface CreateTransferData {
  receiver_id: number;
  file_id: number;
  file_name: string;
  aes_key: string;
  iv: string;
}

export interface TransferListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: TransferListItem[];
}

export type TransferAction = 'accept' | 'reject' | 'cancel' | 'pause' | 'resume' | 'retry';

// Transfer service functions
export const transferService = {
  /**
   * Get all transfers for current user
   * 
   * REPLACES: Mock transfers array in TransferHistory.tsx
   * 
   * @param role - Filter by 'sender' or 'receiver'
   * @param status - Filter by transfer status
   */
  async getTransfers(role?: 'sender' | 'receiver', status?: TransferStatus): Promise<TransferListItem[]> {
    try {
      const params = new URLSearchParams();
      if (role) params.append('role', role);
      if (status) params.append('status', status);
      
      const response = await api.get<TransferListResponse>(`/transfers/?${params.toString()}`);
      return response.data.results;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Create a new transfer
   * 
   * REPLACES: Mock transfer creation in SenderDashboard.tsx
   * 
   * @example
   * // With existing file
   * const transfer = await transferService.createTransfer({
   *   receiver_id: 2,
   *   file_id: 1
   * });
   * 
   * // With inline file data
   * const transfer = await transferService.createTransfer({
   *   receiver_id: 2,
   *   file_data: {
   *     original_name: 'document.pdf',
   *     size: 1048576,
   *     mime_type: 'application/pdf'
   *   }
   * });
   */
  async createTransfer(data: CreateTransferData): Promise<Transfer> {
    try {
      if (!data.file_id) {
        throw new Error('Transfer cannot be created without a valid fileId.');
      }

      if (!data.file_name?.trim()) {
        throw new Error('file_name missing');
      }

      if (!data.aes_key?.trim()) {
        throw new Error('aes_key missing');
      }

      if (!data.iv?.trim()) {
        throw new Error('IV missing');
      }

      const response = await api.post<Transfer>('/transfers/', data);
      return response.data;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Get transfer details by ID
   */
  async getTransferById(id: number): Promise<Transfer> {
    try {
      const response = await api.get<Transfer>(`/transfers/${id}/`);
      return response.data;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Get transfer by UUID
   */
  async getTransferByUUID(uuid: string): Promise<Transfer> {
    try {
      const response = await api.get<Transfer>(`/transfers/uuid/${uuid}/`);
      return response.data;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Resolve fileId from transfer UUID.
   * Required when history entries do not yet include fileId.
   */
  async resolveFileIdFromTransferUUID(transferUuid: string): Promise<number> {
    if (!transferUuid) {
      throw new Error('Cannot resolve fileId: transferUuid is missing.');
    }

    const transfer = await this.getTransferByUUID(transferUuid);
    const fileId = transfer.file?.id;

    if (!fileId) {
      throw new Error(`Cannot resolve fileId from transfer ${transferUuid}.`);
    }

    return fileId;
  },

  /**
   * Resolve required metadata for frontend decryption download flow.
   * Returns fileId + original file name + IV if backend includes it.
   */
  async resolveDownloadContext(params: { transferId?: number; transferUuid?: string }): Promise<TransferDownloadContext> {
    const { transferId, transferUuid } = params;

    let transfer: Transfer;
    if (transferId && Number.isFinite(transferId) && transferId > 0) {
      transfer = await this.getTransferById(transferId);
    } else if (transferUuid) {
      transfer = await this.getTransferByUUID(transferUuid);
    } else {
      throw new Error('Cannot resolve download context: transferId or transferUuid is required.');
    }

    const fileId = transfer.file?.id;
    const fileName = transfer.file_name ?? transfer.file?.original_name;
    const mimeType = transfer.file?.mime_type ?? 'application/pdf';
    const aesKey = transfer.aes_key ?? transfer.encrypted_aes_key ?? null;
    const iv = transfer.iv ?? transfer.file_iv ?? null;

    if (!fileId) {
      throw new Error('Cannot resolve download context: fileId is missing in transfer.');
    }

    if (!fileName) {
      throw new Error('Cannot resolve download context: file name is missing in transfer.');
    }

    if (!iv?.trim()) {
      throw new Error('Cannot resolve download context: IV is missing in transfer.');
    }

    if (!aesKey?.trim()) {
      throw new Error('Cannot resolve download context: AES key is missing in transfer.');
    }

    return {
      fileId,
      fileName,
      aesKey,
      iv,
      mimeType,
    };
  },

  /**
   * Update transfer (progress, status, etc.)
   */
  async updateTransfer(id: number, data: Partial<Transfer>): Promise<Transfer> {
    try {
      const response = await api.patch<Transfer>(`/transfers/${id}/`, data);
      return response.data;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Perform action on transfer
   * 
   * REPLACES: Mock accept/reject in ReceiverDashboard.tsx
   * 
   * @example
   * // Accept incoming transfer
   * await transferService.performAction(transferId, 'accept');
   * 
   * // Reject incoming transfer
   * await transferService.performAction(transferId, 'reject');
   */
  async performAction(id: number, action: TransferAction): Promise<{ message: string; transfer: Transfer }> {
    try {
      const response = await api.post<{ message: string; transfer: Transfer }>(
        `/transfers/${id}/action/`,
        { action }
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Get transfers sent by current user
   * 
   * REPLACES: Mock sent transfers in SenderDashboard.tsx
   */
  async getSentTransfers(): Promise<TransferListItem[]> {
    try {
      const response = await api.get<TransferListResponse>('/transfers/sent/');
      return response.data.results;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Get transfers received by current user
   * 
   * REPLACES: Mock received transfers in ReceiverDashboard.tsx
   */
  async getReceivedTransfers(): Promise<TransferListItem[]> {
    try {
      const response = await api.get<TransferListResponse>('/transfers/received/');
      return response.data.results;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Get pending incoming transfers
   * 
   * REPLACES: Mock incoming requests in ReceiverDashboard.tsx
   */
  async getPendingTransfers(): Promise<TransferListItem[]> {
    try {
      const response = await api.get<TransferListResponse>('/transfers/pending/');
      return response.data.results;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Get active (in-progress) transfers
   */
  async getActiveTransfers(): Promise<Transfer[]> {
    try {
      const response = await api.get<{ results: Transfer[] }>('/transfers/active/');
      return response.data.results;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Get transfer logs
   * 
   * REPLACES: Mock security logs in SecurityLog.tsx
   */
  async getTransferLogs(transferId: number): Promise<TransferLog[]> {
    try {
      const response = await api.get<{ results: TransferLog[] }>(`/transfers/${transferId}/logs/`);
      return response.data.results;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },

  /**
   * Get transfer statistics
   */
  async getStats(): Promise<TransferStats> {
    try {
      const response = await api.get<TransferStats>('/transfers/stats/');
      return response.data;
    } catch (error) {
      throw handleApiError(error as any);
    }
  },
};

/**
 * Helper function to convert API Transfer to frontend TransferRecord format
 * 
 * Use this to replace mock TransferRecord in TransferHistory.tsx:
 * 
 * // Before (mock):
 * const mockTransfers: TransferRecord[] = [...];
 * 
 * // After (real API):
 * const transfers = await transferService.getTransfers();
 * const transferRecords = transfers.map(transferToRecord);
 */
export const transferToRecord = (transfer: TransferListItem | Transfer): {
  id: string;
  transferUuid?: string;
  fileId?: number;
  fileUuid?: string;
  fileName: string;
  fileSize: string;
  sender: string;
  receiver: string;
  status: 'completed' | 'failed' | 'pending' | 'in-progress';
  timestamp: Date;
} => {
  // Map API status to frontend status
  const statusMap: Record<TransferStatus, 'completed' | 'failed' | 'pending' | 'in-progress'> = {
    pending: 'pending',
    accepted: 'in-progress',
    rejected: 'failed',
    connecting: 'in-progress',
    key_exchange: 'in-progress',
    transferring: 'in-progress',
    paused: 'in-progress',
    completed: 'completed',
    failed: 'failed',
    cancelled: 'failed',
  };

  const isFullTransfer = 'sender' in transfer && typeof transfer.sender === 'object';
  
  return {
    id: transfer.id.toString(),
    transferUuid: transfer.uuid,
    fileId: isFullTransfer ? (transfer as Transfer).file.id : undefined,
    fileUuid: isFullTransfer ? (transfer as Transfer).file.uuid : undefined,
    fileName: isFullTransfer ? (transfer as Transfer).file.original_name : (transfer as TransferListItem).file_name,
    fileSize: isFullTransfer ? (transfer as Transfer).file.size_formatted : (transfer as TransferListItem).file_size_formatted,
    sender: isFullTransfer ? (transfer as Transfer).sender.username : (transfer as TransferListItem).sender_username,
    receiver: isFullTransfer ? (transfer as Transfer).receiver.username : (transfer as TransferListItem).receiver_username,
    status: statusMap[transfer.status] || 'pending',
    timestamp: new Date(transfer.created_at),
  };
};

/**
 * Helper to convert pending transfer to IncomingRequest format
 * 
 * REPLACES: Mock incomingRequest in ReceiverDashboard.tsx
 */
export const transferToIncomingRequest = (transfer: TransferListItem): {
  id: string;
  sender: string;
  fileName: string;
  fileSize: string;
} => ({
  id: transfer.id.toString(),
  sender: transfer.sender_username,
  fileName: transfer.file_name,
  fileSize: transfer.file_size_formatted,
});

export default transferService;
