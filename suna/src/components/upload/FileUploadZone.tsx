"use client"

import React, { useCallback, useState, useRef } from "react"
import { useDropzone } from "react-dropzone"
import { Upload, X, FileText, CheckCircle, AlertCircle, Loader2 } from "lucide-react"

// Types for file upload
interface FileUploadItem {
  id: string
  file: File
  status: "pending" | "uploading" | "success" | "error"
  progress: number
  error?: string
  result?: {
    chunks_count?: number
    processing_time?: number
    doc_id?: string
  }
}

interface FileUploadZoneProps {
  onFilesUploaded?: (results: FileUploadItem[]) => void
  maxFiles?: number
  maxSize?: number
  disabled?: boolean
  className?: string
}

// Supported file types
const SUPPORTED_FORMATS = [
  "text/markdown",
  "text/plain",
  "application/pdf",
  "text/csv",
  "application/json",
  "image/png",
  "image/jpeg",
  "image/jpg",
]

const ACCEPTED_TYPES = {
  "text/markdown": [".md", ".markdown"],
  "text/plain": [".txt"],
  "application/pdf": [".pdf"],
  "text/csv": [".csv"],
  "application/json": [".json"],
  "image/png": [".png"],
  "image/jpeg": [".jpg", ".jpeg"],
}

// File size limit (50MB)
const MAX_FILE_SIZE = 50 * 1024 * 1024

// Get file icon based on type
const getFileIcon = (filename: string) => {
  const extension = filename.split('.').pop()?.toLowerCase()

  switch (extension) {
    case "pdf":
      return "📄"
    case "md":
    case "markdown":
      return "📝"
    case "txt":
      return "📄"
    case "csv":
      return "📊"
    case "json":
      return "🔧"
    case "png":
    case "jpg":
    case "jpeg":
      return "🖼️"
    default:
      return "📎"
  }
}

// Format file size for display
const formatFileSize = (bytes: number) => {
  if (bytes === 0) return "0 Bytes"

  const k = 1024
  const sizes = ["Bytes", "KB", "MB", "GB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
}

export const FileUploadZone: React.FC<FileUploadZoneProps> = ({
  onFilesUploaded,
  maxFiles = 10,
  maxSize = MAX_FILE_SIZE,
  disabled = false,
  className = "",
}) => {
  const [files, setFiles] = useState<FileUploadItem[]>([])
  const [isDragActive, setIsDragActive] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Validate single file
  const validateFile = (file: File): { isValid: boolean; error?: string } => {
    // Check file size
    if (file.size > maxSize) {
      return {
        isValid: false,
        error: `File size (${formatFileSize(file.size)}) exceeds limit (${formatFileSize(maxSize)})`,
      }
    }

    // Check file type
    const extension = file.name.split('.').pop()?.toLowerCase()
    const isSupported = Object.values(ACCEPTED_TYPES).some(
      types => types.includes(`.${extension}`)
    )

    if (!isSupported) {
      return {
        isValid: false,
        error: `File type '.${extension}' not supported. Supported formats: .md, .pdf, .csv, .json, .txt, .png, .jpg`,
      }
    }

    return { isValid: true }
  }

  // Handle file selection
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (disabled) return

      // Validate files
      const validFiles: FileUploadItem[] = []
      const maxAllowedFiles = maxFiles - files.length

      for (let i = 0; i < Math.min(acceptedFiles.length, maxAllowedFiles); i++) {
        const file = acceptedFiles[i]
        const validation = validateFile(file)

        if (validation.isValid) {
          validFiles.push({
            id: `${Date.now()}-${Math.random()}`,
            file,
            status: "pending",
            progress: 0,
          })
        } else {
          // Add invalid file with error
          validFiles.push({
            id: `${Date.now()}-${Math.random()}`,
            file,
            status: "error",
            progress: 0,
            error: validation.error,
          })
        }
      }

      if (files.length + validFiles.length > maxFiles) {
        // Add warning about file limit
        const excessFiles = acceptedFiles.slice(maxAllowedFiles)
        console.warn(`Only ${maxFiles} files allowed. ${excessFiles.length} files were ignored.`)
      }

      setFiles(prevFiles => [...prevFiles, ...validFiles])
    },
    [disabled, maxFiles, maxSize, files.length]
  )

  const dropzone = useDropzone({
    onDrop,
    accept: Object.keys(ACCEPTED_TYPES).reduce((acc, key) => {
      acc[key] = ACCEPTED_TYPES[key]
      return acc
    }, {} as Record<string, string[]>),
    maxSize,
    maxFiles: maxFiles - files.length,
    disabled,
    noClick: files.length > 0, // Disable click when we have files
    noKeyboard: true,
    onDragEnter: () => setIsDragActive(true),
    onDragLeave: () => setIsDragActive(false),
  })

  // Remove file from list
  const removeFile = (fileId: string) => {
    setFiles(prevFiles => prevFiles.filter(f => f.id !== fileId))

    // Cancel upload if in progress
    const fileToRemove = files.find(f => f.id === fileId)
    if (fileToRemove?.status === "uploading" && abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
  }

  // Clear all files
  const clearFiles = () => {
    // Cancel any ongoing uploads
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }

    setFiles([])
    setUploadProgress(0)
  }

  // Upload files
  const uploadFiles = async () => {
    const filesToUpload = files.filter(f => f.status === "pending")

    if (filesToUpload.length === 0) {
      return
    }

    setUploadProgress(0)

    try {
      const formData = new FormData()

      // Add files to form data
      filesToUpload.forEach(fileItem => {
        formData.append("files", fileItem.file)
      })

      // Create abort controller
      abortControllerRef.current = new AbortController()

      // Update file statuses to uploading
      setFiles(prevFiles =>
        prevFiles.map(file =>
          filesToUpload.some(f => f.id === file.id)
            ? { ...file, status: "uploading" as const, progress: 0 }
            : file
        )
      )

      // Make upload request
      const response = await fetch("/api/upload/files", {
        method: "POST",
        headers: {
          // Add authentication header if available
          "Authorization": localStorage.getItem("auth_token") || "",
        },
        body: formData,
        signal: abortControllerRef.current.signal,
      })

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`)
      }

      const result = await response.json()

      // Update file statuses with results
      setFiles(prevFiles =>
        prevFiles.map((file, index) => {
          const uploadResult = result.results[index]

          if (file.status === "uploading") {
            return {
              ...file,
              status: uploadResult.status === "success" ? "success" : "error",
              progress: 100,
              error: uploadResult.error_message,
              result: uploadResult.status === "success" ? {
                chunks_count: uploadResult.chunks_count,
                processing_time: uploadResult.processing_time,
                doc_id: uploadResult.doc_id,
              } : undefined,
            }
          }
          return file
        })
      )

      // Update progress
      setUploadProgress(100)

      // Call callback if provided
      if (onFilesUploaded) {
        const results = filesToUpload.map(fileItem => {
          const updatedFile = files.find(f => f.id === fileItem.id)
          return updatedFile || fileItem
        })
        onFilesUploaded(results)
      }

    } catch (error) {
      console.error("Upload failed:", error)

      // Update file statuses to error
      setFiles(prevFiles =>
        prevFiles.map(file =>
          file.status === "uploading"
            ? { ...file, status: "error" as const, progress: 0, error: "Upload failed" }
            : file
        )
      )

      setUploadProgress(0)
    } finally {
      abortControllerRef.current = null
    }
  }

  // Calculate overall progress
  const calculateOverallProgress = () => {
    if (files.length === 0) return 0

    const totalProgress = files.reduce((sum, file) => sum + file.progress, 0)
    return totalProgress / files.length
  }

  const overallProgress = calculateOverallProgress()

  return (
    <div className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors duration-200 ${isDragActive ? "border-blue-500 bg-blue-50" : "border-gray-300"} ${className} ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}>
      <div className="flex flex-col items-center justify-center space-y-4">
        {/* Upload Icon */}
        <div className={`p-4 rounded-full ${isDragActive ? "bg-blue-500 text-white" : "bg-gray-100 text-gray-500"} transition-colors duration-200`}>
          <Upload className="h-8 w-8" />
        </div>

        {/* Drag and Drop Text */}
        <div>
          <p className="text-lg font-medium text-gray-900">
            {isDragActive ? "Drop files here" : "Drag & drop files here"}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            or click to browse
          </p>
        </div>

        {/* File Type Info */}
        <div className="text-xs text-gray-400">
          <p>Supported: .md, .pdf, .csv, .json, .txt, .png, .jpg</p>
          <p>Maximum size: {formatFileSize(maxSize)} per file</p>
        </div>
      </div>

      {/* Hidden file input for click-to-browse */}
      <input
        {...dropzone.getInputProps()}
        className="hidden"
      />
    </div>
  )
}

// File List Component
export const FileList: React.FC<{
  files: FileUploadItem[]
  onRemoveFile: (fileId: string) => void
  onClearFiles: () => void
  onUploadFiles: () => void
  className?: string
}> = ({ files, onRemoveFile, onClearFiles, onUploadFiles, className = "" }) => {
  const getStatusIcon = (status: FileUploadItem["status"]) => {
    switch (status) {
      case "success":
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case "error":
        return <AlertCircle className="h-5 w-5 text-red-500" />
      case "uploading":
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
      default:
        return <FileText className="h-5 w-5 text-gray-400" />
    }
  }

  const getStatusColor = (status: FileUploadItem["status"]) => {
    switch (status) {
      case "success":
        return "border-green-200 bg-green-50"
      case "error":
        return "border-red-200 bg-red-50"
      case "uploading":
        return "border-blue-200 bg-blue-50"
      default:
        return "border-gray-200 bg-gray-50"
    }
  }

  if (files.length === 0) {
    return null
  }

  return (
    <div className={`space-y-2 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">
          Uploaded Files ({files.length})
        </h3>
        <button
          onClick={onClearFiles}
          className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-md transition-colors"
        >
          Clear All
        </button>
      </div>

      {/* File List */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {files.map((file) => (
          <div
            key={file.id}
            className={`flex items-center justify-between p-3 rounded-lg border-2 transition-colors ${getStatusColor(file.status)}`}
          >
            {/* File Info */}
            <div className="flex items-center space-x-3 flex-1">
              {/* Icon */}
              <div className="text-2xl">
                {getFileIcon(file.file.name)}
              </div>

              {/* Details */}
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">
                  {file.file.name}
                </p>
                <div className="flex items-center space-x-2 text-sm text-gray-500">
                  <span>{formatFileSize(file.file.size)}</span>
                  {file.result?.chunks_count && (
                    <span>• {file.result.chunks_count} chunks</span>
                  )}
                </div>
              </div>
            </div>

            {/* Status and Controls */}
            <div className="flex items-center space-x-2">
              {/* Status Icon */}
              {getStatusIcon(file.status)}

              {/* Progress Bar */}
              {file.status === "uploading" && (
                <div className="w-24">
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-2 bg-blue-500 transition-all duration-300 ease-out"
                      style={{ width: `${file.progress}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Remove Button */}
              <button
                onClick={() => onRemoveFile(file.id)}
                className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-full transition-colors"
                title="Remove file"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Error Message */}
          {file.status === "error" && file.error && (
            <div className="mt-2 text-sm text-red-600">
              {file.error}
            </div>
          )}

          {/* Success Info */}
          {file.status === "success" && file.result && (
            <div className="mt-2 text-xs text-green-600">
              <p>✅ Successfully uploaded and indexed</p>
              {file.result.processing_time && (
                <p>Processed in {file.result.processing_time.toFixed(2)}s</p>
              )}
            </div>
          )}
        </div>
      ))}
      </div>

      {/* Upload Button */}
      <div className="flex justify-center">
        <button
          onClick={onUploadFiles}
          disabled={files.every(f => f.status !== "pending")}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          {files.every(f => f.status !== "pending") ? "Upload Complete" : "Upload Files"}
        </button>
      </div>
    </div>
  )
}