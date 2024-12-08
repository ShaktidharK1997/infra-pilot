// src/components/ui/alert.jsx
import React from 'react';

const Alert = ({ children, variant = 'default', className = '', ...props }) => {
  const baseStyles = 'p-4 rounded-lg border mb-4';
  const variantStyles = {
    default: 'bg-gray-100 border-gray-200 text-gray-800',
    destructive: 'bg-red-100 border-red-200 text-red-800',
  };

  return (
    <div 
      role="alert"
      className={`${baseStyles} ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

const AlertDescription = ({ children, className = '', ...props }) => {
  return (
    <div className={`text-sm ${className}`} {...props}>
      {children}
    </div>
  );
};

export { Alert, AlertDescription };