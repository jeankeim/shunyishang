'use client';

import React, { useState, useRef, useCallback } from 'react';
import { Upload, X, Image as ImageIcon } from 'lucide-react';
import { getAuthToken } from '@/lib/api';

interface ImageUploaderProps {
  onImageUploaded: (imageUrl: string) => void;
  accept?: string;
  maxSize?: number; // bytes
  className?: string;
}

export function ImageUploader({
  onImageUploaded,
  accept = 'image/*',
  maxSize = 5 * 1024 * 1024, // 5MB
  className = '',
}: ImageUploaderProps) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    // 检查文件类型
    if (!file.type.startsWith('image/')) {
      return '请上传图片文件（JPG/PNG 等）';
    }

    // 检查文件大小
    if (file.size > maxSize) {
      return `图片大小不能超过 ${Math.round(maxSize / 1024 / 1024)}MB`;
    }

    return null;
  };

  const handleFile = useCallback(async (file: File) => {
    setError(null);
    
    // 验证文件
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    // 显示预览
    const reader = new FileReader();
    reader.onload = (e) => {
      setPreviewUrl(e.target?.result as string);
    };
    reader.readAsDataURL(file);

    // 检查认证状态
    const token = getAuthToken();
    if (!token) {
      setError('请先登录后再上传图片');
      setPreviewUrl(null);
      return;
    }

    // 上传到服务器
    setIsUploading(true);
    
    try {
      const formData = new FormData();
      formData.append('file', file);

      const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${API_BASE}/api/v1/wardrobe/upload-image`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '上传失败');
      }

      const data = await response.json();
      onImageUploaded(data.image_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : '上传失败，请重试');
      setPreviewUrl(null);
    } finally {
      setIsUploading(false);
    }
  }, [onImageUploaded, maxSize]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFile(file);
    }
  }, [handleFile]);

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFile(file);
    }
  };

  const handleRemove = () => {
    setPreviewUrl(null);
    onImageUploaded('');
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className={`space-y-2 ${className}`}>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        衣物图片
      </label>
      
      {!previewUrl ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={handleClick}
          className={`
            relative border-2 border-dashed rounded-lg p-8 
            text-center cursor-pointer transition-all duration-200
            ${isDragging 
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/10' 
              : 'border-gray-300 dark:border-gray-600 hover:border-blue-400 dark:hover:border-blue-500'
            }
          `}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={accept}
            onChange={handleFileChange}
            className="hidden"
            disabled={isUploading}
          />
          
          <div className="space-y-4">
            {isUploading ? (
              <div className="flex flex-col items-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
                <p className="mt-4 text-sm text-gray-600 dark:text-gray-400">正在上传...</p>
              </div>
            ) : (
              <>
                <div className="flex justify-center">
                  <Upload className="h-12 w-12 text-gray-400" />
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  <p>
                    <span className="font-medium text-blue-600 dark:text-blue-400">
                      点击上传
                    </span>{' '}
                    或拖拽图片到此处
                  </p>
                  <p className="mt-1 text-xs">
                    支持 JPG、PNG 格式，最大 5MB
                  </p>
                </div>
              </>
            )}
          </div>
        </div>
      ) : (
        <div className="relative rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700">
          <ImageIcon className="absolute top-2 right-2 h-6 w-6 text-gray-400" />
          <img
            src={previewUrl}
            alt="预览"
            className="w-full h-48 object-cover"
          />
          <button
            type="button"
            onClick={handleRemove}
            className="absolute top-2 left-2 p-1.5 bg-red-500 hover:bg-red-600 text-white rounded-full transition-colors"
            title="删除图片"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}
    </div>
  );
}
