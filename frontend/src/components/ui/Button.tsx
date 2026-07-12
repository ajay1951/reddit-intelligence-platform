import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({ 
  children, 
  variant = 'primary', 
  isLoading = false, 
  className = '', 
  disabled, 
  ...props 
}) => {
  const baseClasses = "btn";
  const variantClasses = variant === 'primary' ? 'btn-primary' : `btn-${variant}`;
  
  return (
    <button 
      className={`${baseClasses} ${variantClasses} ${className}`} 
      disabled={isLoading || disabled} 
      {...props}
    >
      {isLoading ? (
        <span className="flex items-center gap-2">
          <span className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin"></span>
          Processing...
        </span>
      ) : children}
    </button>
  );
};
