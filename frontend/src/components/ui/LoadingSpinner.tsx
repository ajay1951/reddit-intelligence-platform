import React from 'react';

interface LoadingSpinnerProps {
  text?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ text = "Loading..." }) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 gap-4">
      <div className="w-10 h-10 border-4 border-[#3b82f6]/20 border-t-[#3b82f6] rounded-full animate-spin"></div>
      <p className="text-[#a1a1aa] font-medium">{text}</p>
    </div>
  );
};
