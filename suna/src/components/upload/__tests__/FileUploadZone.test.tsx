/**
 * File Upload Zone Component Tests
 *
 * Tests for the drag-and-drop file upload component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { FileUploadZone, FileList } from '../FileUploadZone';

// Mock react-dropzone
jest.mock('react-dropzone', () => ({
  useDropzone: () => ({
    getRootProps: () => ({ 'data-testid': 'dropzone' }),
    getInputProps: () => ({ 'data-testid': 'file-input' }),
    isDragActive: false,
  }),
}));

// Mock fetch API
global.fetch = jest.fn();

describe('FileUploadZone', () => {
  const mockOnFilesUploaded = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    (fetch as jest.Mock).mockClear();
  });

  const defaultProps = {
    onFilesUploaded: mockOnFilesUploaded,
    maxFiles: 10,
    maxSize: 50 * 1024 * 1024, // 50MB
    disabled: false,
    className: '',
  };

  it('renders upload zone correctly', () => {
    render(<FileUploadZone {...defaultProps} />);

    expect(screen.getByText('Drag & drop files here')).toBeInTheDocument();
    expect(screen.getByText('or click to browse')).toBeInTheDocument();
    expect(screen.getByText('Supported: .md, .pdf, .csv, .json, .txt, .png, .jpg')).toBeInTheDocument();
  });

  it('displays file size limit correctly', () => {
    render(<FileUploadZone {...defaultProps} />);

    expect(screen.getByText('Maximum size: 50 MB per file')).toBeInTheDocument();
  });

  it('shows disabled state when disabled prop is true', () => {
    render(<FileUploadZone {...defaultProps} disabled={true} />);

    const dropzone = screen.getByTestId('dropzone');
    expect(dropzone).toHaveClass('opacity-50');
    expect(dropzone).toHaveClass('cursor-not-allowed');
  });

  it('handles successful file upload', async () => {
    const mockFiles = [
      {
        id: 'file1',
        file: new File(['test content'], 'test.md', { type: 'text/markdown' }),
        status: 'success' as const,
        progress: 100,
        result: {
          chunks_count: 5,
          processing_time: 1.5,
          doc_id: 'doc123',
        },
      },
    ];

    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        results: [
          {
            status: 'success',
            chunks_count: 5,
            processing_time: 1.5,
            doc_id: 'doc123',
          },
        ],
      }),
    });

    render(<FileUploadZone {...defaultProps} />);

    // Simulate file drop
    const dropzone = screen.getByTestId('dropzone');
    const file = new File(['test content'], 'test.md', { type: 'text/markdown' });

    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [file],
      },
    });

    // Wait for upload processing
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        '/api/upload/files',
        expect.objectContaining({
          method: 'POST',
          body: expect.any(FormData),
        })
      );
    });

    // Check if callback was called
    await waitFor(() => {
      expect(mockOnFilesUploaded).toHaveBeenCalled();
    });
  });

  it('handles upload error gracefully', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      statusText: 'Upload failed',
    });

    render(<FileUploadZone {...defaultProps} />);

    const dropzone = screen.getByTestId('dropzone');
    const file = new File(['test content'], 'test.md', { type: 'text/markdown' });

    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [file],
      },
    });

    await waitFor(() => {
      expect(fetch).toHaveBeenCalled();
    });

    // Check for error handling (should not crash)
    expect(screen.getByText('Drag & drop files here')).toBeInTheDocument();
  });

  it('validates file types correctly', () => {
    render(<FileUploadZone {...defaultProps} />);

    const dropzone = screen.getByTestId('dropzone');
    const invalidFile = new File(['test content'], 'test.exe', { type: 'application/x-executable' });

    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [invalidFile],
      },
    });

    // Should show error for unsupported file type
    expect(screen.getByText(/File type '\.exe' not supported/)).toBeInTheDocument();
  });

  it('validates file size correctly', () => {
    render(<FileUploadZone {...defaultProps} />);

    const dropzone = screen.getByTestId('dropzone');
    const largeFile = new File(['x'.repeat(60 * 1024 * 1024)], 'large.md', { type: 'text/markdown' }); // 60MB

    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [largeFile],
      },
    });

    // Should show error for file size exceeding limit
    expect(screen.getByText(/File size.*exceeds limit/)).toBeInTheDocument();
  });
});

describe('FileList', () => {
  const mockOnRemoveFile = jest.fn();
  const mockOnClearFiles = jest.fn();
  const mockOnUploadFiles = jest.fn();

  const mockFiles = [
    {
      id: 'file1',
      file: new File(['content'], 'test.md'),
      status: 'pending' as const,
      progress: 0,
    },
    {
      id: 'file2',
      file: new File(['content'], 'test.pdf'),
      status: 'uploading' as const,
      progress: 50,
    },
    {
      id: 'file3',
      file: new File(['content'], 'test.json'),
      status: 'success' as const,
      progress: 100,
      result: {
        chunks_count: 3,
        processing_time: 1.2,
        doc_id: 'doc123',
      },
    },
    {
      id: 'file4',
      file: new File(['content'], 'test.csv'),
      status: 'error' as const,
      progress: 0,
      error: 'Processing failed',
    },
  ];

  it('renders file list correctly', () => {
    render(
      <FileList
        files={mockFiles}
        onRemoveFile={mockOnRemoveFile}
        onClearFiles={mockOnClearFiles}
        onUploadFiles={mockOnUploadFiles}
      />
    );

    expect(screen.getByText('Uploaded Files (4)')).toBeInTheDocument();
    expect(screen.getByText('test.md')).toBeInTheDocument();
    expect(screen.getByText('test.pdf')).toBeInTheDocument();
    expect(screen.getByText('test.json')).toBeInTheDocument();
    expect(screen.getByText('test.csv')).toBeInTheDocument();
  });

  it('displays correct status icons', () => {
    render(
      <FileList
        files={mockFiles}
        onRemoveFile={mockOnRemoveFile}
        onClearFiles={mockOnClearFiles}
        onUploadFiles={mockOnUploadFiles}
      />
    );

    // Should have different status indicators
    const statusIcons = screen.getAllByTestId(/status-icon/);
    expect(statusIcons).toHaveLength(4);
  });

  it('shows progress bar for uploading files', () => {
    render(
      <FileList
        files={mockFiles}
        onRemoveFile={mockOnRemoveFile}
        onClearFiles={mockOnClearFiles}
        onUploadFiles={mockOnUploadFiles}
      />
    );

    // Should show progress bar for uploading file
    const progressBar = screen.getByTestId('progress-file2');
    expect(progressBar).toBeInTheDocument();
  });

  it('shows success information for completed files', () => {
    render(
      <FileList
        files={mockFiles}
        onRemoveFile={mockOnRemoveFile}
        onClearFiles={mockOnClearFiles}
        onUploadFiles={mockOnUploadFiles}
      />
    );

    expect(screen.getByText('Successfully uploaded and indexed')).toBeInTheDocument();
    expect(screen.getByText('3 chunks')).toBeInTheDocument();
    expect(screen.getByText('Processed in 1.2s')).toBeInTheDocument();
  });

  it('shows error message for failed files', () => {
    render(
      <FileList
        files={mockFiles}
        onRemoveFile={mockOnRemoveFile}
        onClearFiles={mockOnClearFiles}
        onUploadFiles={mockOnUploadFiles}
      />
    );

    expect(screen.getByText('Processing failed')).toBeInTheDocument();
  });

  it('handles file removal', () => {
    render(
      <FileList
        files={mockFiles}
        onRemoveFile={mockOnRemoveFile}
        onClearFiles={mockOnClearFiles}
        onUploadFiles={mockOnUploadFiles}
      />
    );

    const removeButtons = screen.getAllByTitle('Remove file');
    fireEvent.click(removeButtons[0]);

    expect(mockOnRemoveFile).toHaveBeenCalledWith('file1');
  });

  it('handles clear all files', () => {
    render(
      <FileList
        files={mockFiles}
        onRemoveFile={mockOnRemoveFile}
        onClearFiles={mockOnClearFiles}
        onUploadFiles={mockOnUploadFiles}
      />
    );

    const clearButton = screen.getByText('Clear All');
    fireEvent.click(clearButton);

    expect(mockOnClearFiles).toHaveBeenCalled();
  });

  it('shows appropriate upload button text', () => {
    const allPendingFiles = mockFiles.map(f => ({ ...f, status: 'pending' as const }));

    render(
      <FileList
        files={allPendingFiles}
        onRemoveFile={mockOnRemoveFile}
        onClearFiles={mockOnClearFiles}
        onUploadFiles={mockOnUploadFiles}
      />
    );

    const uploadButton = screen.getByText('Upload Files');
    expect(uploadButton).toBeInTheDocument();
    expect(uploadButton).not.toBeDisabled();
  });

  it('disables upload button when all files are processed', () => {
    const allCompletedFiles = mockFiles.map(f => ({ ...f, status: 'success' as const }));

    render(
      <FileList
        files={allCompletedFiles}
        onRemoveFile={mockOnRemoveFile}
        onClearFiles={mockOnClearFiles}
        onUploadFiles={mockOnUploadFiles}
      />
    );

    const uploadButton = screen.getByText('Upload Complete');
    expect(uploadButton).toBeInTheDocument();
    expect(uploadButton).toBeDisabled();
  });
});

describe('File Upload Integration', () => {
  it('handles complete upload workflow', async () => {
    const mockOnFilesUploaded = jest.fn();

    // Mock successful upload response
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        results: [
          {
            status: 'success',
            chunks_count: 5,
            processing_time: 1.5,
            doc_id: 'doc123',
          },
        ],
      }),
    });

    render(<FileUploadZone onFilesUploaded={mockOnFilesUploaded} />);

    const dropzone = screen.getByTestId('dropzone');
    const file = new File(['# Test Document'], 'test.md', { type: 'text/markdown' });

    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [file],
      },
    });

    // Wait for upload to complete
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        '/api/upload/files',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    // Check callback was called with results
    await waitFor(() => {
      expect(mockOnFilesUploaded).toHaveBeenCalledWith(
        expect.arrayContaining([
          expect.objectContaining({
            status: 'success',
            chunks_count: 5,
            processing_time: 1.5,
            doc_id: 'doc123',
          }),
        ])
      );
    });
  });
});