import React, { forwardRef } from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', ...props }, ref) => {
    return (
      <div className="form-group flex flex-col gap-1 w-full">
        {label && <label className="text-sm font-medium text-[var(--text-secondary)]">{label}</label>}
        <input 
          ref={ref}
          className={`input-glass ${error ? 'border-red-500' : ''} ${className}`} 
          {...props} 
        />
        {error && <span className="text-xs text-red-500">{error}</span>}
      </div>
    );
  }
);

Input.displayName = 'Input';
