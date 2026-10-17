import React, { useState, useEffect, useRef } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, Trash2, Play, RefreshCw, FolderOpen } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';

interface UploadedFileRecord {
  id: string;
  filename: string;
  size_bytes: number;
  content_type: string;
  uploaded_at: string;
  processed: boolean;
  details?: Record<string, any>;
}

interface FileUploadZoneProps {
  apiBaseUrl?: string;
  allowedExtensions?: string[];
  acceptedFormatsText?: string;
  onFileProcessed?: (result: any) => void;
}

export const FileUploadZone: React.FC<FileUploadZoneProps> = ({
  apiBaseUrl = '/api/v1',
  allowedExtensions = ['.json', '.yaml', '.yml', '.txt', '.md'],
  acceptedFormatsText = 'JSON, YAML, TXT, Markdown',
  onFileProcessed,
}) => {
  const [files, setFiles] = useState<UploadedFileRecord[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchFiles = async () => {
    try {
      const res = await fetch(`${apiBaseUrl}/files`);
      if (res.ok) {
        const data = await res.json();
        setFiles(data);
      }
    } catch {
      // Offline fallback
    }
  };

  useEffect(() => {
    fetchFiles();
  }, [apiBaseUrl]);

  const handleUpload = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    const file = fileList[0];
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();

    if (!allowedExtensions.includes(ext)) {
      setStatusMessage({
        type: 'error',
        text: `File type ${ext} not supported. Allowed formats: ${acceptedFormatsText}`,
      });
      return;
    }

    setIsUploading(true);
    setStatusMessage(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${apiBaseUrl}/files/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Upload failed');
      }

      await res.json();
      setStatusMessage({
        type: 'success',
        text: `Uploaded "${file.name}" (${(file.size / 1024).toFixed(1)} KB) successfully.`,
      });
      await fetchFiles();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'File upload failed' });
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleProcess = async (fileId: string) => {
    setProcessingId(fileId);
    setStatusMessage(null);
    try {
      const res = await fetch(`${apiBaseUrl}/files/${fileId}/process`, {
        method: 'POST',
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Processing failed');
      }
      const data = await res.json();
      setStatusMessage({
        type: 'success',
        text: data.message || `File ${data.filename} processed successfully.`,
      });
      if (onFileProcessed) {
        onFileProcessed(data);
      }
      await fetchFiles();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Processing failed' });
    } finally {
      setProcessingId(null);
    }
  };

  const handleDelete = async (fileId: string) => {
    try {
      const res = await fetch(`${apiBaseUrl}/files/${fileId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setFiles((prev) => prev.filter((f) => f.id !== fileId));
        setStatusMessage({ type: 'success', text: 'File removed successfully.' });
      }
    } catch {
      setStatusMessage({ type: 'error', text: 'Failed to delete file.' });
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="space-y-4">
      {/* Upload Drop Zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          handleUpload(e.dataTransfer.files);
        }}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
          isDragging
            ? 'border-primary bg-primary/10 shadow-lg'
            : 'border-border bg-card/50 hover:bg-muted/40 hover:border-primary/50'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept={allowedExtensions.join(',')}
          onChange={(e) => handleUpload(e.target.files)}
        />
        <div className="flex flex-col items-center justify-center gap-2">
          <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
            {isUploading ? (
              <RefreshCw className="w-6 h-6 animate-spin" />
            ) : (
              <Upload className="w-6 h-6" />
            )}
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">
              {isUploading ? 'Uploading file...' : 'Drop files here or click to browse'}
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Accepted formats: {acceptedFormatsText} (up to 50MB)
            </p>
          </div>
          <div className="flex flex-wrap gap-1.5 mt-2 justify-center">
            {allowedExtensions.map((ext) => (
              <Badge key={ext} variant="default" className="text-[10px] uppercase font-mono">
                {ext.replace('.', '')}
              </Badge>
            ))}
          </div>
        </div>
      </div>

      {/* Status banner */}
      {statusMessage && (
        <div
          className={`rounded-lg p-3 text-xs flex items-center gap-2 border ${
            statusMessage.type === 'success'
              ? 'bg-emerald-950/20 text-emerald-400 border-emerald-800/40'
              : 'bg-rose-950/20 text-rose-400 border-rose-800/40'
          }`}
        >
          {statusMessage.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 shrink-0" />
          )}
          <span>{statusMessage.text}</span>
        </div>
      )}

      {/* Uploaded File Registry */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FolderOpen className="w-4 h-4 text-primary" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-foreground">
              Uploaded Datasets & Files ({files.length})
            </h4>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={fetchFiles}
            className="h-7 text-xs gap-1 text-muted-foreground hover:text-foreground"
          >
            <RefreshCw className="w-3 h-3" /> Refresh
          </Button>
        </div>

        {files.length === 0 ? (
          <div className="p-6 text-center text-xs text-muted-foreground">
            No custom files uploaded yet. Drag and drop a file above to load into the active pipeline.
          </div>
        ) : (
          <div className="divide-y divide-border">
            {files.map((file) => (
              <div
                key={file.id}
                className="p-3.5 flex flex-wrap items-center justify-between gap-3 text-xs hover:bg-muted/30 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-[200px]">
                  <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center text-primary shrink-0">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="font-semibold text-foreground truncate max-w-xs">{file.filename}</div>
                    <div className="text-[11px] text-muted-foreground font-mono">
                      {formatSize(file.size_bytes)} • {new Date(file.uploaded_at).toLocaleTimeString()}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Badge variant={file.processed ? 'success' : 'default'} className="text-[10px]">
                    {file.processed ? 'PROCESSED' : 'READY'}
                  </Badge>
                  <Button
                    size="sm"
                    disabled={processingId === file.id}
                    onClick={() => handleProcess(file.id)}
                    className="h-7 text-xs gap-1.5"
                  >
                    {processingId === file.id ? (
                      <RefreshCw className="w-3 h-3 animate-spin" />
                    ) : (
                      <Play className="w-3 h-3" />
                    )}
                    {processingId === file.id ? 'Processing...' : 'Load to Engine'}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDelete(file.id)}
                    className="h-7 w-7 p-0 text-muted-foreground hover:text-rose-400"
                    title="Delete file"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
