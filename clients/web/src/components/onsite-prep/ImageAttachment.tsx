'use client'

import { useRef } from 'react'

interface ImageAttachmentProps {
  images: File[]
  onImagesChange: (images: File[]) => void
  maxImages?: number
}

export function ImageAttachment({ images, onImagesChange, maxImages = 5 }: ImageAttachmentProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleAdd = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    const remaining = maxImages - images.length
    const toAdd = files.slice(0, remaining)
    onImagesChange([...images, ...toAdd])
    // Reset input
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleRemove = (index: number) => {
    onImagesChange(images.filter((_, i) => i !== index))
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div className="text-[10px] uppercase tracking-widest text-gray-500">
          Whiteboard Images ({images.length}/{maxImages})
        </div>
        {images.length < maxImages && (
          <button
            onClick={handleAdd}
            className="text-xs text-coral hover:text-coral/80"
          >
            + Attach Image
          </button>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        className="hidden"
        onChange={handleFileChange}
      />

      {images.length > 0 && (
        <div className="grid grid-cols-3 gap-2">
          {images.map((file, i) => (
            <div key={i} className="relative group">
              <img
                src={URL.createObjectURL(file)}
                alt={file.name}
                className="w-full h-20 object-cover rounded-lg border border-gray-200"
              />
              <button
                onClick={() => handleRemove(i)}
                className="absolute top-1 right-1 w-5 h-5 bg-red-500 text-white rounded-full text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
              >
                x
              </button>
              <div className="text-[9px] text-gray-400 truncate mt-0.5">{file.name}</div>
            </div>
          ))}
        </div>
      )}

      {images.length === 0 && (
        <div
          onClick={handleAdd}
          className="border-2 border-dashed border-gray-200 rounded-lg p-4 text-center cursor-pointer hover:border-gray-300 transition-colors"
        >
          <div className="text-xs text-gray-400">
            Attach whiteboard photos (optional)
          </div>
          <div className="text-[10px] text-gray-300 mt-1">
            JPEG, PNG, WebP &bull; Max {maxImages} images
          </div>
        </div>
      )}
    </div>
  )
}
