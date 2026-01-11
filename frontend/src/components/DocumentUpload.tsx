import { useState, useCallback, useRef, useEffect } from 'react';
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
  relationships?: number;
  chunks?: number;
  pages?: number;
  schema?: string;
}

export default function DocumentUpload() {
  const { setGraphStats } = useAppStore();
  const [isDragging, setIsDragging] = useState(false);
  const [uploads, setUploads] = useState<UploadStatus[]>([]);
  const uploadCountRef = useRef(0);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    // Important: Set dropEffect to indicate drop is allowed
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = 'copy';
    }
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Only set dragging false if we're leaving the drop zone itself
    // (not entering a child element)
    if (e.currentTarget === e.target) {
      setIsDragging(false);
    }
  }, []);

  const handleDragEnter = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = 'copy';
    }
    setIsDragging(true);
  }, []);

  const processFile = useCallback(async (file: File) => {
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

    // Use ref to track upload index (avoids stale closure issues)
    const uploadIndex = uploadCountRef.current;
    uploadCountRef.current += 1;

    // Add to uploads list
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
                entities: response.entities_extracted,
                relationships: response.relationships_extracted,
                chunks: response.chunks_created,
                pages: response.pages_parsed,
                schema: response.schema_used,
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
  }, [setGraphStats]);

  // Handle paste events (Ctrl+V / Cmd+V)
  const handlePaste = useCallback((e: ClipboardEvent) => {
    const clipboardData = e.clipboardData;
    if (!clipboardData) return;

    // Collect files from clipboard
    const files: File[] = [];

    // Try clipboardData.items first
    if (clipboardData.items && clipboardData.items.length > 0) {
      const items = Array.from(clipboardData.items);
      for (const item of items) {
        if (item.kind === 'file') {
          const file = item.getAsFile();
          if (file) {
            files.push(file);
          }
        }
      }
    }

    // Fallback to clipboardData.files
    if (files.length === 0 && clipboardData.files && clipboardData.files.length > 0) {
      files.push(...Array.from(clipboardData.files));
    }

    // If we got PDF files, process them
    const pdfFiles = files.filter(f => f.name.toLowerCase().endsWith('.pdf') || f.type === 'application/pdf');
    
    if (pdfFiles.length > 0) {
      e.preventDefault(); // Prevent default paste behavior
      pdfFiles.forEach(processFile);
    }
  }, [processFile]);

  // Add paste event listener
  useEffect(() => {
    document.addEventListener('paste', handlePaste);
    return () => {
      document.removeEventListener('paste', handlePaste);
    };
  }, [handlePaste]);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const dataTransfer = e.dataTransfer;
    if (!dataTransfer) {
      return;
    }

    // Collect actual file objects
    const files: File[] = [];
    
    // Try dataTransfer.items first (more reliable across browsers)
    if (dataTransfer.items && dataTransfer.items.length > 0) {
      const items = Array.from(dataTransfer.items);
      for (const item of items) {
        if (item.kind === 'file') {
          const file = item.getAsFile();
          if (file) {
            files.push(file);
          }
        }
      }
    }
    
    // Fallback to dataTransfer.files
    if (files.length === 0 && dataTransfer.files && dataTransfer.files.length > 0) {
      files.push(...Array.from(dataTransfer.files));
    }

    // If we got files, process them
    if (files.length > 0) {
      files.forEach(processFile);
      return;
    }

    // No file objects found - analyze what we received instead
    const types = Array.from(dataTransfer.types || []);
    const hasStringData = types.length > 0;
    const hasUriList = types.includes('text/uri-list');
    const hasPlainText = types.includes('text/plain');
    
    // Build informative error message
    let errorMessage = 'Unable to access file contents.';
    
    if (hasUriList || hasPlainText) {
      // Source provided paths/URIs instead of file access
      errorMessage = 'The source provided file references instead of file access. Please drag directly from your system file manager (Finder on Mac, Explorer on Windows).';
    } else if (hasStringData) {
      errorMessage = `Received unsupported data format. Please drag PDF files from your system file manager.`;
    } else {
      errorMessage = 'No files detected. Please drag PDF files from your system file manager, or use the "Select Files" button.';
    }

    setUploads((prev) => [
      ...prev,
      {
        filename: 'Drop failed',
        status: 'error',
        message: errorMessage,
      },
    ]);
  }, [processFile]);

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
        {/* Hidden file input */}
        <input
          type="file"
          accept=".pdf"
          multiple
          onChange={handleFileSelect}
          className="hidden"
          id="file-upload"
        />
        
        {/* Drop zone */}
        <motion.div
          onDragEnter={handleDragEnter}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          animate={{
            scale: isDragging ? 1.02 : 1,
            borderColor: isDragging ? 'rgb(56, 178, 172)' : 'rgb(72, 101, 129)',
          }}
          className={`
            glass rounded-2xl p-12 text-center border-2 border-dashed transition-colors cursor-pointer
            ${isDragging ? 'bg-electric-500/10' : ''}
          `}
          onClick={() => document.getElementById('file-upload')?.click()}
        >
          {/* Pointer events none on children during drag to prevent interference */}
          <div className={isDragging ? 'pointer-events-none' : ''}>
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-electric-400/20 to-electric-600/20 flex items-center justify-center mx-auto mb-6">
              <CloudArrowUpIcon className="w-8 h-8 text-electric-400" />
            </div>
            
            <h3 className="text-xl font-semibold text-midnight-100 mb-2">
              Upload PDF Documents
            </h3>
            <p className="text-midnight-400 mb-6">
              {isDragging ? 'Drop your files here!' : 'Drag from Finder/Explorer, paste (⌘V), or click to browse'}
            </p>
            
            <span className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-electric-500 text-midnight-950 font-medium hover:bg-electric-400 transition-colors">
              <DocumentIcon className="w-5 h-5" />
              Select Files
            </span>
          </div>
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
                    {/* Extraction metrics */}
                    {upload.status === 'success' && (
                      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-midnight-400">
                        {upload.pages !== undefined && (
                          <span>📄 {upload.pages} pages</span>
                        )}
                        {upload.chunks !== undefined && (
                          <span>📦 {upload.chunks} chunks</span>
                        )}
                        {upload.entities !== undefined && (
                          <span className="text-electric-400">🔷 {upload.entities} entities</span>
                        )}
                        {upload.relationships !== undefined && (
                          <span className="text-purple-400">↔️ {upload.relationships} relations</span>
                        )}
                      </div>
                    )}
                  </div>
                  
                  {/* Schema badge */}
                  {upload.schema && (
                    <div className="text-xs bg-midnight-800 px-2 py-1 rounded text-midnight-300">
                      {upload.schema}
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
              { step: 1, title: 'Upload', desc: 'Upload your PDF documents' },
              { step: 2, title: 'Extract', desc: 'AI extracts entities and relationships based on the active schema' },
              { step: 3, title: 'Store', desc: 'Information is stored in the knowledge graph' },
              { step: 4, title: 'Query', desc: 'Ask questions about your documents' },
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
