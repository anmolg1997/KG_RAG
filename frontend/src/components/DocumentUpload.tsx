import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { 
  CloudArrowUpIcon, 
  DocumentIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { uploadAPI, graphAPI } from '../services/api';
import { useAppStore } from '../store';

interface UploadStatus {
  filename: string;
  status: 'uploading' | 'processing' | 'success' | 'error';
  message: string;
  documentId?: string;
  entities?: number;
}

export default function DocumentUpload() {
  const { setGraphStats } = useAppStore();
  const [isDragging, setIsDragging] = useState(false);
  const [uploads, setUploads] = useState<UploadStatus[]>([]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const processFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploads((prev) => [
        ...prev,
        {
          filename: file.name,
          status: 'error',
          message: 'Only PDF files are supported',
        },
      ]);
      return;
    }

    // Add to uploads list
    const uploadIndex = uploads.length;
    setUploads((prev) => [
      ...prev,
      {
        filename: file.name,
        status: 'uploading',
        message: 'Uploading...',
      },
    ]);

    try {
      // Update status to processing
      setUploads((prev) =>
        prev.map((u, i) =>
          i === uploadIndex ? { ...u, status: 'processing', message: 'Processing document...' } : u
        )
      );

      const response = await uploadAPI.uploadDocument(file);

      setUploads((prev) =>
        prev.map((u, i) =>
          i === uploadIndex
            ? {
                ...u,
                status: response.success ? 'success' : 'error',
                message: response.message,
                documentId: response.document_id,
              }
            : u
        )
      );

      // Refresh graph stats
      if (response.success) {
        const stats = await graphAPI.getStats();
        setGraphStats(stats);
      }
    } catch (error) {
      console.error('Upload error:', error);
      setUploads((prev) =>
        prev.map((u, i) =>
          i === uploadIndex
            ? {
                ...u,
                status: 'error',
                message: error instanceof Error ? error.message : 'Upload failed',
              }
            : u
        )
      );
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    files.forEach(processFile);
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    files.forEach(processFile);
    e.target.value = ''; // Reset input
  };

  const clearUploads = () => {
    setUploads([]);
  };

  return (
    <div className="h-full overflow-y-auto p-4 lg:p-6">
      <div className="max-w-3xl mx-auto">
        {/* Drop zone */}
        <motion.div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          animate={{
            scale: isDragging ? 1.02 : 1,
            borderColor: isDragging ? 'rgb(56, 178, 172)' : 'rgb(72, 101, 129)',
          }}
          className={`
            glass rounded-2xl p-12 text-center border-2 border-dashed transition-colors
            ${isDragging ? 'bg-electric-500/10' : ''}
          `}
        >
          <input
            type="file"
            accept=".pdf"
            multiple
            onChange={handleFileSelect}
            className="hidden"
            id="file-upload"
          />
          
          <label htmlFor="file-upload" className="cursor-pointer">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-electric-400/20 to-electric-600/20 flex items-center justify-center mx-auto mb-6">
              <CloudArrowUpIcon className="w-8 h-8 text-electric-400" />
            </div>
            
            <h3 className="text-xl font-semibold text-midnight-100 mb-2">
              Upload PDF Documents
            </h3>
            <p className="text-midnight-400 mb-6">
              Drag and drop your contract PDFs here, or click to browse
            </p>
            
            <span className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-electric-500 text-midnight-950 font-medium hover:bg-electric-400 transition-colors">
              <DocumentIcon className="w-5 h-5" />
              Select Files
            </span>
          </label>
        </motion.div>

        {/* Upload list */}
        {uploads.length > 0 && (
          <div className="mt-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Uploads</h3>
              <button
                onClick={clearUploads}
                className="text-sm text-midnight-400 hover:text-midnight-200 transition-colors"
              >
                Clear all
              </button>
            </div>
            
            <div className="space-y-3">
              {uploads.map((upload, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="glass rounded-xl p-4 flex items-center gap-4"
                >
                  {/* Status icon */}
                  <div className={`
                    w-10 h-10 rounded-lg flex items-center justify-center
                    ${upload.status === 'success' ? 'bg-green-500/20' : ''}
                    ${upload.status === 'error' ? 'bg-red-500/20' : ''}
                    ${upload.status === 'uploading' || upload.status === 'processing' ? 'bg-electric-500/20' : ''}
                  `}>
                    {upload.status === 'success' && <CheckCircleIcon className="w-6 h-6 text-green-400" />}
                    {upload.status === 'error' && <XCircleIcon className="w-6 h-6 text-red-400" />}
                    {(upload.status === 'uploading' || upload.status === 'processing') && (
                      <ArrowPathIcon className="w-6 h-6 text-electric-400 animate-spin" />
                    )}
                  </div>
                  
                  {/* Details */}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-midnight-100 truncate">
                      {upload.filename}
                    </p>
                    <p className={`text-sm ${
                      upload.status === 'success' ? 'text-green-400' :
                      upload.status === 'error' ? 'text-red-400' :
                      'text-midnight-400'
                    }`}>
                      {upload.message}
                    </p>
                  </div>
                  
                  {/* Document ID */}
                  {upload.documentId && (
                    <div className="text-xs text-midnight-500 font-mono">
                      {upload.documentId.slice(0, 16)}...
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Instructions */}
        <div className="mt-8 glass rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-4">How it works</h3>
          <ol className="space-y-4">
            {[
              { step: 1, title: 'Upload', desc: 'Upload your PDF contract documents' },
              { step: 2, title: 'Extract', desc: 'AI extracts entities, clauses, and relationships' },
              { step: 3, title: 'Store', desc: 'Information is stored in the knowledge graph' },
              { step: 4, title: 'Query', desc: 'Ask questions about your contracts' },
            ].map((item) => (
              <li key={item.step} className="flex items-start gap-4">
                <div className="w-8 h-8 rounded-lg bg-electric-500/20 flex items-center justify-center flex-shrink-0">
                  <span className="text-sm font-bold text-electric-400">{item.step}</span>
                </div>
                <div>
                  <p className="font-medium text-midnight-100">{item.title}</p>
                  <p className="text-sm text-midnight-400">{item.desc}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}
